"""validate の検証結果を、判定を変えずに絞り込んで表示する。"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from math import isfinite, isnan
from typing import Any

from mcblueprint.errors import ValidationError
from mcblueprint.support import SupportWarning


def _json_value(value: Any) -> Any:
    if isinstance(value, float) and not isfinite(value):
        return "NaN" if isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def validation_report(
    source: str,
    errors: Sequence[ValidationError],
    warnings: Sequence[SupportWarning],
    *,
    strict: bool,
    kinds: Sequence[str],
    paths: Sequence[str],
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """全結果から終了コードを決め、表示対象だけを絞ったJSON互換の辞書を返す。

    パスはJSONパスの要素境界で前方一致する。支持警告のパスは不明のため
    None とする。limit=0 は上限なし。id は絞り込み前の1始まりの順番。
    """
    entries = [
        {
            "kind": error.kind,
            "severity": "error",
            "path": error.path,
            "message": error.message,
            "opType": error.op_type,
            "value": _json_value(error.value),
            "position": None,
        }
        for error in errors
    ] + [
        {
            "kind": "support",
            "severity": "warning",
            "path": None,
            "message": warning.message,
            "opType": None,
            "value": str(warning.block),
            "position": warning.position.to_list(),
        }
        for warning in warnings
    ]
    for index, entry in enumerate(entries, 1):
        entry["id"] = index
    matched = [
        entry
        for entry in entries
        if (not kinds or entry["kind"] in kinds)
        and (
            not paths
            or (
                entry["path"] is not None
                and any(
                    entry["path"] == path
                    or entry["path"].startswith((path + ".", path + "["))
                    for path in paths
                )
            )
        )
    ]
    shown = matched[offset : offset + limit] if limit else matched[offset:]
    groups: dict[tuple[str, str, str, str | None], dict[str, Any]] = {}
    for entry in matched:
        key = (entry["kind"], entry["severity"], entry["message"], entry["opType"])
        if key not in groups:
            groups[key] = {
                "kind": entry["kind"],
                "severity": entry["severity"],
                "message": entry["message"],
                "opType": entry["opType"],
                "count": 0,
                "firstId": entry["id"],
                "firstPath": entry["path"],
            }
        groups[key]["count"] += 1
    shown_keys = {
        (entry["kind"], entry["severity"], entry["message"], entry["opType"])
        for entry in shown
    }
    group_rows = [group for key, group in groups.items() if key in shown_keys]
    exit_code = int(bool(errors or (strict and warnings)))
    return {
        "source": source,
        "valid": exit_code == 0,
        "exitCode": exit_code,
        "strict": strict,
        "counts": {
            "total": len(entries),
            "errors": len(errors),
            "warnings": len(warnings),
            "byKind": dict(Counter(entry["kind"] for entry in entries)),
            "matched": len(matched),
            "shown": len(shown),
            "filteredOut": len(entries) - len(matched),
            "omitted": len(matched) - len(shown),
            "groups": len(groups),
            "groupsOmitted": len(groups) - len(group_rows),
        },
        "groups": group_rows,
        "diagnostics": shown,
        "retrieval": {
            "kinds": list(kinds),
            "paths": list(paths),
            "limit": limit,
            "offset": offset,
            "nextOffset": offset + len(shown) if offset + len(shown) < len(matched) else None,
            "hint": "同じ入力・条件で --offset N を指定。全詳細は --limit 0、"
            "全種類・パスは --kind / --path を外して再検証する。",
        },
    }
