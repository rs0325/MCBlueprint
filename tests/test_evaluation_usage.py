import copy
import json
import sys
from pathlib import Path

import pytest
from scripts.aggregate_usage import aggregate, main

ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "evaluation/records/usage-example.json"


def read_example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def find_group(result: dict, mode: str = "single-use") -> dict:
    return next(group for group in result["groups"] if group["productionMode"] == mode)


def test_usage_keeps_failures_in_primary_rate_and_does_not_add_token_breakdowns() -> None:
    result = aggregate(read_example())
    group = find_group(result)

    assert group["attemptCount"] == 2
    assert group["correctionCount"] == 1
    assert group["acceptedArtifactCount"] == 1
    assert group["metrics"]["inputTokens"]["estimated"]["total"] == 1800
    assert group["metrics"]["imageTokens"]["estimated"]["total"] == 200
    assert (
        group["perAcceptedArtifact"]["inputTokens"]["estimatedKnownSubtotalPerAcceptedArtifact"]
        == 1800
    )
    assert group["metrics"]["providerTotalTokens"]["notCollectedCount"] == 2
    assert group["metrics"]["inputTokens"]["notCollectedCount"] == 0
    assert group["acceptedArtifactsOnly"]["attemptIds"] == ["house-try-1", "house-try-2"]


def test_no_accepted_artifact_has_no_per_artifact_rate() -> None:
    record = read_example()
    for row in record["attempts"]:
        row["qualityOutcome"] = "unknown"
    group = find_group(aggregate(record))

    assert group["acceptedArtifactCount"] == 0
    assert group["perAcceptedArtifact"]["inputTokens"]["status"] == "no-accepted-artifacts"
    assert group["perAcceptedArtifact"]["inputTokens"]["measuredKnownSubtotal"]["total"] is None
    assert group["perAcceptedArtifact"]["inputTokens"]["estimatedKnownSubtotal"]["total"] == 1800


def test_missing_measurements_make_normalized_value_partial_not_zero() -> None:
    record = read_example()
    group = find_group(aggregate(record))
    rate = group["perAcceptedArtifact"]["providerTotalTokens"]

    assert rate["status"] == "partial"
    assert rate["measuredKnownSubtotalPerAcceptedArtifact"] is None
    assert rate["notCollectedCount"] == 2


def test_modes_keep_library_preparation_cost_separate() -> None:
    record = read_example()
    library = copy.deepcopy(record["attempts"][0])
    library.update(
        attemptId="library-setup",
        comparisonGroupId="house-comparison",
        artifactId=None,
        result="success",
        correctsAttemptId=None,
        productionMode="library-preparation",
        qualityOutcome="unknown",
    )
    record["attempts"].append(library)
    reused = copy.deepcopy(record["attempts"][1])
    reused.update(
        attemptId="reused-house",
        comparisonGroupId="house-reuse-comparison",
        artifactId="reused-final",
        correctsAttemptId=None,
        productionMode="reused-production",
    )
    record["attempts"].append(reused)
    result = aggregate(record)

    assert {group["productionMode"] for group in result["groups"]} == {
        "single-use",
        "reused-production",
        "library-preparation",
    }
    assert find_group(result, "library-preparation")["acceptedArtifactCount"] == 0
    assert find_group(result, "reused-production")["acceptedArtifacts"] == ["reused-final"]


def test_cost_currency_and_estimate_are_not_collapsed() -> None:
    group = find_group(aggregate(read_example()))
    cost = group["metrics"]["cost"]["byCurrency"]["USD"]

    assert cost["estimated"] == {"total": 0.035, "count": 2}
    assert group["metrics"]["elapsedSeconds"]["measured"]["total"] == 105


def test_unknown_cost_currency_marks_the_whole_group_incomplete() -> None:
    record = read_example()
    missing = copy.deepcopy(record["attempts"][0])
    missing.update(
        attemptId="unpriced-attempt",
        artifactId=None,
        artifactRef=None,
        result="interrupted",
        correctsAttemptId=None,
        qualityOutcome="unknown",
        qualityEvidence="中断し、費用を取得できなかった",
    )
    missing["metrics"]["cost"].update(
        value=None,
        unit="currency",
        currency=None,
        status="not-collected",
        reason="費用と通貨を取得できなかった",
    )
    record["attempts"].append(missing)
    cost = find_group(aggregate(record))["metrics"]["cost"]
    rate = find_group(aggregate(record))["perAcceptedArtifact"]["cost"]

    assert cost["byCurrency"]["USD"]["complete"] is True
    assert cost["unknownCurrency"]["notCollectedCount"] == 1
    assert cost["notCollectedCount"] == 1
    assert cost["complete"] is False
    assert rate["status"] == "partial"
    assert rate["notCollectedCount"] == 1


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            lambda row: row["metrics"]["inputTokens"].update(
                value=0, status="not-collected", reason="未取得"
            ),
            "未取得/対象外",
        ),
        (lambda row: row["metrics"]["imageTokens"].update(includedIn="outputTokens"), "includedIn"),
        (lambda row: row.update(correctsAttemptId="missing"), "記録内にありません"),
        (
            lambda row: row["metrics"]["cost"].update(currency=None, unit="currency"),
            "currency",
        ),
        (
            lambda row: row["metrics"]["cost"].update(currency=["USD"], unit=["USD"]),
            "currency",
        ),
        (lambda row: row["metrics"]["inputTokens"].update(unit="character"), "unit"),
        (lambda row: row.update(artifactRef=None), "artifactRefが必要です"),
    ],
)
def test_invalid_usage_record_is_rejected(change, message: str) -> None:
    record = read_example()
    change(record["attempts"][0])

    with pytest.raises(ValueError, match=message):
        aggregate(record)


def test_identical_input_produces_identical_aggregate() -> None:
    record = read_example()

    assert aggregate(record) == aggregate(copy.deepcopy(record))


def test_cli_returns_2_for_non_string_cost_currency(tmp_path, monkeypatch, capsys) -> None:
    record = read_example()
    record["attempts"][0]["metrics"]["cost"].update(currency=["USD"], unit=["USD"])
    path = tmp_path / "invalid-usage.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["aggregate_usage.py", str(path)])

    assert main() == 2
    assert "metrics.cost.currency" in capsys.readouterr().err
