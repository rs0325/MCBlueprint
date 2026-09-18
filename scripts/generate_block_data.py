"""Generate bundled block data from Mojang's official data generator.

Usage (either obtain server.jar yourself or let the script download it):

    python scripts/generate_block_data.py --version 1.21.11 --download
    python scripts/generate_block_data.py --version 1.21.11 --server-jar path/to/server.jar

The script runs ``java -DbundlerMainClass=net.minecraft.data.Main -jar server.jar --reports``,
converts ``reports/blocks.json`` into the compact format described in docs/ARCHITECTURE.md
section 10, writes ``src/mcblueprint/data/blocks/<version>.json`` and records the
DataVersion (``world_version`` from the jar's ``version.json``) in
``src/mcblueprint/data/versions.json``. Java 21+ is required only to run this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "src" / "mcblueprint" / "data"
GENERATED_DIR = REPO_ROOT / "generated"
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def download_server_jar(version: str, dest_dir: Path) -> Path:
    """Download the official server jar for ``version`` and verify its SHA-1."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    jar_path = dest_dir / f"server-{version}.jar"
    manifest = _fetch_json(VERSION_MANIFEST_URL)
    entry = next((v for v in manifest["versions"] if v["id"] == version), None)
    if entry is None:
        raise SystemExit(f"Version {version} not found in Mojang version manifest")
    version_meta = _fetch_json(entry["url"])
    server = version_meta["downloads"]["server"]
    if jar_path.exists() and _sha1(jar_path) == server["sha1"]:
        print(f"Using cached {jar_path}")
        return jar_path
    print(f"Downloading {server['url']} ({server['size'] / 1_000_000:.1f} MB)")
    urllib.request.urlretrieve(server["url"], jar_path)
    if _sha1(jar_path) != server["sha1"]:
        jar_path.unlink()
        raise SystemExit("Downloaded server jar failed SHA-1 verification")
    return jar_path


def run_data_generator(server_jar: Path, output_dir: Path) -> Path:
    """Run Mojang's data generator and return the path to reports/blocks.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "java",
        "-DbundlerMainClass=net.minecraft.data.Main",
        "-jar",
        str(server_jar.resolve()),
        "--reports",
        "--output",
        str(output_dir.resolve()),
    ]
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=output_dir, check=True)
    blocks_json = output_dir / "reports" / "blocks.json"
    if not blocks_json.exists():
        raise SystemExit(f"Data generator did not produce {blocks_json}")
    return blocks_json


def read_data_version(server_jar: Path) -> int:
    with zipfile.ZipFile(server_jar) as jar:
        with jar.open("version.json") as fh:
            return int(json.load(fh)["world_version"])


def convert_blocks(blocks_json: Path) -> dict[str, dict[str, object]]:
    """Convert Mojang's blocks.json into ``{id: {properties, default}}``."""
    raw = json.loads(blocks_json.read_text(encoding="utf-8"))
    result: dict[str, dict[str, object]] = {}
    for block_id, info in sorted(raw.items()):
        properties = {name: list(values) for name, values in info.get("properties", {}).items()}
        default = next(
            (state.get("properties", {}) for state in info["states"] if state.get("default")),
            {},
        )
        result[block_id] = {"properties": properties, "default": dict(default)}
    return result


def write_block_data(version: str, blocks: dict[str, dict[str, object]]) -> Path:
    out_path = DATA_DIR / "blocks" / f"{version}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # One block per line keeps diffs between versions readable.
    lines = [
        f"  {json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}" for k, v in blocks.items()
    ]
    out_path.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8", newline="\n")
    return out_path


def write_versions(version: str, data_version: int) -> Path:
    versions_path = DATA_DIR / "versions.json"
    versions: dict[str, dict[str, int]] = {}
    if versions_path.exists():
        versions = json.loads(versions_path.read_text(encoding="utf-8"))
    versions[version] = {"dataVersion": data_version}
    ordered = dict(sorted(versions.items(), key=lambda kv: _version_key(kv[0])))
    versions_path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8", newline="\n")
    return versions_path


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", required=True, help="Minecraft version, e.g. 1.21.11")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--server-jar", type=Path, help="Path to an existing server.jar")
    source.add_argument(
        "--download", action="store_true", help="Download server.jar from Mojang into generated/"
    )
    args = parser.parse_args(argv)

    work_dir = GENERATED_DIR / args.version
    server_jar = args.server_jar or download_server_jar(args.version, GENERATED_DIR)
    blocks_json = run_data_generator(server_jar, work_dir)
    blocks = convert_blocks(blocks_json)
    data_version = read_data_version(server_jar)

    out_path = write_block_data(args.version, blocks)
    versions_path = write_versions(args.version, data_version)
    print(f"Wrote {out_path} ({len(blocks)} blocks)")
    print(f"Wrote {versions_path} ({args.version}: dataVersion {data_version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
