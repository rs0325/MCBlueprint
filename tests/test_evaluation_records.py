import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
CASES_PATH = Path("evaluation/cases/fixed-cases.json")
BASELINE_PATH = Path("evaluation/records/baseline.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def read_json(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def file_hash(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_case_definitions_and_references_are_valid() -> None:
    cases_data = read_json(CASES_PATH)
    cases = cases_data["cases"]
    ids = [case["id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert {"single-house", "standalone-tower", "connected-pair", "slope-settlement"} == set(ids)

    for case in cases:
        assert case["task"]
        assert case["requirements"]
        assert case["views"]
        for reference in case["references"]:
            assert (ROOT / reference["path"]).is_file()
            assert SHA256.fullmatch(reference["sha256"])
            assert file_hash(reference["path"]) == reference["sha256"]
            assert reference["license"]

    pair = next(case for case in cases if case["id"] == "connected-pair")
    assert "共有壁" in pair["task"]
    assert "渡り廊下は設けない" in pair["task"]
    assert any("開口" in requirement for requirement in pair["requirements"])
    assert any("連続した切妻屋根" in requirement for requirement in pair["requirements"])


def test_baseline_records_have_consistent_statuses_and_hashes() -> None:
    cases = read_json(CASES_PATH)["cases"]
    cases_by_id = {case["id"]: case for case in cases}
    baseline = read_json(BASELINE_PATH)
    assert baseline["schemaVersion"] == 1
    assert baseline["recordType"] == "baseline"
    assert {run["caseId"] for run in baseline["runs"]} == set(cases_by_id)

    for run in baseline["runs"]:
        case = cases_by_id[run["caseId"]]
        definition = run["caseDefinition"]
        assert definition["path"] == CASES_PATH.as_posix()
        assert definition["sha256"] == file_hash(definition["path"])
        assert run["status"] in {"success", "failure", "unhandled"}
        assert len(run["requirementResults"]) == len(case["requirements"])
        recorded_requirements = {item["requirement"] for item in run["requirementResults"]}
        assert recorded_requirements == set(case["requirements"])
        for item in run["requirementResults"]:
            assert item["status"] in {"pass", "fail", "unknown"}
            if item["status"] == "unknown":
                assert item["reason"]
                assert item["general"] is None
                assert item["experienced"] is None
            else:
                assert item["reason"]

        for category in ("appearance", "interior"):
            score = run["scores"][category]
            assert score["status"] in {"not-evaluated", "evaluated"}
            if score["status"] == "not-evaluated":
                assert score["reason"]
                assert score["general"] is None
                assert score["experienced"] is None
            else:
                assert all(1 <= score[group] <= 5 for group in ("general", "experienced"))

        execution = run["execution"]
        expected_views = set(case["views"])
        artifacts = execution["viewArtifacts"]
        artifact_views = {artifact["view"] for artifact in artifacts}
        assert set(execution["fixedViews"]) == expected_views
        assert artifact_views <= expected_views
        assert set(run["missingViews"]) == expected_views - artifact_views
        for artifact in artifacts:
            assert SHA256.fullmatch(artifact["sha256"])
            assert file_hash(artifact["path"]) == artifact["sha256"]

        if execution["model"] is None:
            assert execution["modelStatus"] in {"not-applicable", "not-run", "unknown"}
            assert execution["modelReason"]
        if execution["seed"] is None:
            assert execution["seedStatus"] == "not-run"
            assert execution["seedReason"]
        if run["input"] is None or run["output"] is None:
            assert run["status"] == "unhandled"
            assert run["notes"]
        for artifact in (run["input"], run["output"]):
            if artifact is not None:
                assert SHA256.fullmatch(artifact["sha256"])
                assert file_hash(artifact["path"]) == artifact["sha256"]
        if run["status"] == "success":
            assert execution["validate"] == "success"
            assert execution["build"] == "success"
            assert run["output"] is not None

    for control in baseline["controls"]:
        assert control["status"] in {"success", "failure", "unhandled"}
        assert SHA256.fullmatch(control["input"]["sha256"])
        assert file_hash("evaluation/controls/unknown-operation.json") == control["input"]["sha256"]
        assert control["execution"]["error"]


def test_evaluation_document_links_resolve() -> None:
    text = (ROOT / "docs/EVALUATION.md").read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    assert links
    for link in links:
        assert (ROOT / "docs" / link).is_file()