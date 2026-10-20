"""使用量記録を検証し、比較グループごとの集計を出力する。"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

METRICS = (
    "inputTokens",
    "outputTokens",
    "providerTotalTokens",
    "imageTokens",
    "cachedInputTokens",
    "cost",
    "elapsedSeconds",
    "calls",
    "humanEdits",
)
STATUSES = {"measured", "estimated", "not-collected", "not-applicable"}
UNITS = {
    "inputTokens": "token",
    "outputTokens": "token",
    "providerTotalTokens": "token",
    "imageTokens": "token",
    "cachedInputTokens": "token",
    "elapsedSeconds": "second",
    "calls": "call",
    "humanEdits": "edit",
}
INTEGER_METRICS = {
    "inputTokens",
    "outputTokens",
    "providerTotalTokens",
    "imageTokens",
    "cachedInputTokens",
    "calls",
    "humanEdits",
}


def _validate(document: Any) -> list[dict[str, Any]]:
    if (
        not isinstance(document, dict)
        or document.get("schemaVersion") != 1
        or document.get("recordType") != "usage"
    ):
        raise ValueError("schemaVersion=1、recordType=usage のオブジェクトが必要です")
    attempts = document.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError("attempts は配列である必要があります")
    known_ids = {
        row["attemptId"]
        for row in attempts
        if isinstance(row, dict) and isinstance(row.get("attemptId"), str)
    }
    ids: set[str] = set()
    for index, row in enumerate(attempts):
        prefix = f"attempts[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{prefix} はオブジェクトである必要があります")
        required = (
            "attemptId",
            "comparisonGroupId",
            "taskId",
            "artifactId",
            "model",
            "effort",
            "result",
            "correctsAttemptId",
            "productionMode",
            "qualityOutcome",
            "qualityEvidence",
            "recordedAt",
            "source",
            "artifactRef",
            "metrics",
        )
        for key in required:
            if key not in row:
                raise ValueError(f"{prefix}.{key} がありません")
        attempt_id = row["attemptId"]
        if not isinstance(attempt_id, str) or not attempt_id or attempt_id in ids:
            raise ValueError(f"{prefix}.attemptId は重複しない文字列が必要です")
        ids.add(attempt_id)
        if not isinstance(row["comparisonGroupId"], str) or not row["comparisonGroupId"]:
            raise ValueError(f"{prefix}.comparisonGroupId が必要です")
        for key in ("taskId", "model", "effort"):
            if not isinstance(row[key], str) or not row[key]:
                raise ValueError(f"{prefix}.{key} は空でない文字列が必要です")
        if not isinstance(row["result"], str) or row["result"] not in {
            "success",
            "failure",
            "interrupted",
        }:
            raise ValueError(f"{prefix}.result が不正です")
        if not isinstance(row["qualityOutcome"], str) or row["qualityOutcome"] not in {
            "accepted",
            "rejected",
            "unknown",
        }:
            raise ValueError(f"{prefix}.qualityOutcome が不正です")
        if not isinstance(row["qualityEvidence"], str) or not row["qualityEvidence"]:
            raise ValueError(f"{prefix}.qualityEvidence が必要です")
        if not isinstance(row["productionMode"], str) or row["productionMode"] not in {
            "single-use",
            "reused-production",
            "library-preparation",
        }:
            raise ValueError(f"{prefix}.productionMode が不正です")
        if row["artifactId"] is not None and (
            not isinstance(row["artifactId"], str) or not row["artifactId"]
        ):
            raise ValueError(f"{prefix}.artifactId は文字列またはnullが必要です")
        if row["artifactId"] is None and row["qualityOutcome"] == "accepted":
            raise ValueError(f"{prefix}: acceptedにはartifactIdが必要です")
        correction = row["correctsAttemptId"]
        if correction is not None and (
            not isinstance(correction, str) or correction not in known_ids
        ):
            raise ValueError(f"{prefix}.correctsAttemptId が記録内にありません")
        if correction == attempt_id:
            raise ValueError(f"{prefix}.correctsAttemptId が自身を参照しています")
        if (
            not isinstance(row["source"], dict)
            or not row["source"].get("kind")
            or not row["source"].get("reference")
        ):
            raise ValueError(f"{prefix}.source.kind/reference が必要です")
        artifact_ref = row["artifactRef"]
        if artifact_ref is not None and (
            not isinstance(artifact_ref, dict)
            or not artifact_ref.get("kind")
            or not artifact_ref.get("reference")
        ):
            raise ValueError(f"{prefix}.artifactRef は kind/reference またはnullが必要です")
        if row["artifactId"] is not None and artifact_ref is None:
            raise ValueError(f"{prefix}.artifactId にはartifactRefが必要です")
        try:
            timestamp = datetime.fromisoformat(row["recordedAt"].replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError(f"{prefix}.recordedAt はタイムゾーン付きISO 8601が必要です") from error
        if timestamp.utcoffset() is None:
            raise ValueError(f"{prefix}.recordedAt はタイムゾーン付きISO 8601が必要です")
        metrics = row["metrics"]
        if not isinstance(metrics, dict):
            raise ValueError(f"{prefix}.metrics はオブジェクトである必要があります")
        for name in METRICS:
            metric = metrics.get(name)
            if not isinstance(metric, dict) or not isinstance(metric.get("status"), str):
                raise ValueError(f"{prefix}.metrics.{name} は value/status/unit が必要です")
            if "value" not in metric:
                raise ValueError(f"{prefix}.metrics.{name} は value/status/unit が必要です")
            if metric["status"] not in STATUSES:
                raise ValueError(f"{prefix}.metrics.{name}.status が不正です")
            if name == "cost":
                currency = metric.get("currency")
                if currency is not None and (
                    not isinstance(currency, str) or not currency
                ):
                    raise ValueError(f"{prefix}.metrics.cost.currency は文字列が必要です")
                if metric["status"] in {"measured", "estimated"} and currency is None:
                    raise ValueError(f"{prefix}.metrics.cost.currency が必要です")
                expected_unit = currency or "currency"
            else:
                expected_unit = UNITS.get(name)
            if not isinstance(metric.get("unit"), str) or not metric["unit"]:
                raise ValueError(f"{prefix}.metrics.{name}.unit は文字列が必要です")
            if metric["unit"] != expected_unit:
                raise ValueError(f"{prefix}.metrics.{name}.unit が不正です")
            value = metric["value"]
            if metric["status"] in {"not-collected", "not-applicable"}:
                if value is not None or not metric.get("reason"):
                    raise ValueError(
                        f"{prefix}.metrics.{name}: 未取得/対象外にはnullとreasonが必要です"
                    )
            elif (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"{prefix}.metrics.{name}: 実測/推定には0以上の数値が必要です")
            if name in INTEGER_METRICS and metric["status"] in {"measured", "estimated"}:
                if not float(value).is_integer():
                    raise ValueError(f"{prefix}.metrics.{name} は整数である必要があります")
            if (
                name in {"imageTokens", "cachedInputTokens"}
                and metric.get("includedIn") != "inputTokens"
            ):
                raise ValueError(f"{prefix}.metrics.{name}.includedIn は inputTokens が必要です")
    return attempts


def _metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = {status: [] for status in STATUSES}
    for row in rows:
        values[row["status"]].append(row["value"])

    def subtotal(status: str) -> dict[str, Any]:
        entries = values[status]
        return {"total": sum(entries) if entries else None, "count": len(entries)}

    return {
        "measured": subtotal("measured"),
        "estimated": subtotal("estimated"),
        "notCollectedCount": len(values["not-collected"]),
        "notApplicableCount": len(values["not-applicable"]),
        "complete": not values["not-collected"],
    }


def _metric_groups(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    entries = [row["metrics"][name] for row in rows]
    if name == "cost":
        currencies = sorted({entry.get("currency") for entry in entries if entry.get("currency")})
        by_currency = {
            currency: _metric_summary(
                [entry for entry in entries if entry.get("currency") == currency]
            )
            for currency in currencies
        }
        unknown_currency = _metric_summary(
            [entry for entry in entries if not entry.get("currency")]
        )
        not_collected = unknown_currency["notCollectedCount"] + sum(
            summary["notCollectedCount"] for summary in by_currency.values()
        )
        return {
            "byCurrency": by_currency,
            "unknownCurrency": unknown_currency,
            "notCollectedCount": not_collected,
            "complete": not not_collected,
        }
    return _metric_summary(entries)


def _attempt_group(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        row["comparisonGroupId"],
        row["model"],
        row["effort"],
        row["productionMode"],
    )


def aggregate(document: Any) -> dict[str, Any]:
    attempts = _validate(document)
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in attempts:
        groups[_attempt_group(row)].append(row)

    summaries = []
    for key in sorted(groups):
        rows = groups[key]
        artifact_outcomes: dict[str, str] = {}
        for row in sorted(
            rows,
            key=lambda item: datetime.fromisoformat(
                item["recordedAt"].replace("Z", "+00:00")
            ).astimezone(UTC),
        ):
            artifact_id = row["artifactId"]
            if artifact_id is not None and row["qualityOutcome"] != "unknown":
                artifact_outcomes[artifact_id] = row["qualityOutcome"]
        accepted = sorted(
            artifact_id
            for artifact_id, outcome in artifact_outcomes.items()
            if outcome == "accepted"
        )
        metrics = {name: _metric_groups(rows, name) for name in METRICS}
        per_accepted = {}
        for name in METRICS:
            grouped = metrics[name]
            if name == "cost":
                per_accepted[name] = {
                    "status": (
                        "no-accepted-artifacts"
                        if not accepted
                        else "partial"
                        if grouped["notCollectedCount"]
                        else "complete"
                    ),
                    "denominator": len(accepted),
                    "notCollectedCount": grouped["notCollectedCount"],
                    "byCurrency": {
                        currency: _normalized_metric(metric, len(accepted))
                        for currency, metric in grouped["byCurrency"].items()
                    },
                    "unknownCurrency": _normalized_metric(
                        grouped["unknownCurrency"], len(accepted)
                    ),
                }
            else:
                per_accepted[name] = _normalized_metric(grouped, len(accepted))
        quality_unknown = sum(row["qualityOutcome"] == "unknown" for row in rows)
        summaries.append(
            {
                "comparisonGroupId": key[0],
                "model": key[1],
                "effort": key[2],
                "productionMode": key[3],
                "attemptCount": len(rows),
                "attemptIds": [row["attemptId"] for row in rows],
                "correctionCount": sum(row["correctsAttemptId"] is not None for row in rows),
                "acceptedArtifacts": accepted,
                "acceptedArtifactCount": len(accepted),
                "unknownQualityAttemptCount": quality_unknown,
                "metrics": metrics,
                "perAcceptedArtifact": per_accepted,
                "acceptedArtifactsOnly": _accepted_only(rows, accepted),
            }
        )
    return {
        "schemaVersion": 1,
        "recordType": "usage-summary",
        "attemptCount": len(attempts),
        "groups": summaries,
    }


def _normalized_metric(metric: dict[str, Any], denominator: int) -> dict[str, Any]:
    if denominator == 0:
        return {
            "status": "no-accepted-artifacts",
            "measuredKnownSubtotal": metric["measured"],
            "estimatedKnownSubtotal": metric["estimated"],
            "notCollectedCount": metric["notCollectedCount"],
        }
    return {
        "status": "partial" if metric["notCollectedCount"] else "complete",
        "denominator": denominator,
        "measuredKnownSubtotalPerAcceptedArtifact": (
            metric["measured"]["total"] / denominator
            if metric["measured"]["total"] is not None
            else None
        ),
        "estimatedKnownSubtotalPerAcceptedArtifact": (
            metric["estimated"]["total"] / denominator
            if metric["estimated"]["total"] is not None
            else None
        ),
        "notCollectedCount": metric["notCollectedCount"],
    }


def _accepted_only(rows: list[dict[str, Any]], accepted: list[str]) -> dict[str, Any]:
    accepted_rows = [row for row in rows if row["artifactId"] in accepted]
    return {
        "attemptCount": len(accepted_rows),
        "attemptIds": [row["attemptId"] for row in accepted_rows],
        "metrics": {name: _metric_groups(accepted_rows, name) for name in METRICS},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="usage記録JSONのパス")
    args = parser.parse_args()
    try:
        document = json.loads(args.record.read_text(encoding="utf-8"))
        result = aggregate(document)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"使用量記録エラー: {error}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
