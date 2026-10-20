"""既存 fixture の全生成後、一括/分割出力だけを別プロセスで比較する。"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from hashlib import sha256
from pathlib import Path

from mcblueprint.exporters import EXPORTERS
from mcblueprint.generator import generate
from mcblueprint.loader import load_blueprint
from mcblueprint.model.vec import Vec3
from mcblueprint.region_export import export_regions


def worker(args: argparse.Namespace) -> dict:
    blueprint = load_blueprint(args.fixture)
    volume = generate(blueprint)
    input_hash = sha256(args.fixture.read_bytes()).hexdigest()
    # #96 の output 段階と同じく、生成済み volume の保持量は測定開始前に確保する。
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        destination = Path(tmp) / "result"
        if args.memory:
            tracemalloc.start()
        started = time.perf_counter()
        if args.mode == "single":
            exporter = EXPORTERS[args.format]()
            exporter.export(volume, blueprint, destination.with_suffix(exporter.extension))
        else:
            export_regions(volume, blueprint, destination, region_size=Vec3(*args.region_size),
                           input_sha256=input_hash, format=args.format)
        elapsed = time.perf_counter() - started
        peak = None
        if args.memory:
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        return {"seconds": elapsed, "pythonPeakBytes": peak}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--region-size", nargs=3, type=int, default=[32, 16, 32])
    parser.add_argument("--format", choices=sorted(EXPORTERS), default="schem")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["single", "regions"])
    parser.add_argument("--memory", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.mode:
        print(json.dumps(worker(args)))
        return
    results = {}
    for mode in ("single", "regions"):
        command = [sys.executable, __file__, str(args.fixture), "--format", args.format,
                   "--region-size", *map(str, args.region_size), "--output", str(args.output),
                   "--mode", mode]
        samples = [json.loads(subprocess.check_output(command, text=True))["seconds"]
                   for _ in range(args.repetitions)]
        memory = json.loads(subprocess.check_output([*command, "--memory"], text=True))
        results[mode] = {
            "secondsMedian": statistics.median(samples), "samplesSeconds": samples,
            "pythonPeakBytes": memory["pythonPeakBytes"],
        }
    record = {
        "python": sys.version, "platform": platform.platform(), "fixture": str(args.fixture),
        "fixtureSha256": sha256(args.fixture.read_bytes()).hexdigest(),
        "format": args.format, "regionSize": args.region_size,
        "method": "各試行は別プロセス。全生成後の出力段階のみ、時間中央値と"
                  "別試行のtracemalloc peak。"
                  "完成volume保持量・生成時間・プロセス全体RSSは含まない。",
        "results": results,
    }
    args.output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
