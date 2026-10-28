"""Local validation for the planned viral-replication Gateway request."""

from __future__ import annotations

import math
from typing import Any


COMMON = {"type", "productImages", "industry", "textModel", "resolution", "promptOptimization", "count"}
IMAGE = COMMON | {"sourceImage", "requirement", "ratio", "imageModel"}
VIDEO = COMMON | {
    "sourceVideo", "referenceAudios", "productDescription", "videoModel",
    "replicationMode", "strategies", "sourceVideoMetadata",
}


def _nonempty(body: dict[str, Any], key: str) -> None:
    if not isinstance(body.get(key), str) or not body[key].strip():
        raise ValueError(f"{key} must be a non-empty string")


def _ref(value: Any, key: str) -> None:
    if not isinstance(value, dict) or set(value) != {"uploadId"}:
        raise ValueError(f"{key} must be {{'uploadId': '...'}}")
    if not isinstance(value["uploadId"], str) or not value["uploadId"].strip():
        raise ValueError(f"{key}.uploadId must be a non-empty string")


def _refs(body: dict[str, Any], key: str, maximum: int | None = None) -> None:
    if key not in body:
        return
    items = body[key]
    if not isinstance(items, list) or (maximum is not None and len(items) > maximum):
        raise ValueError(f"{key} must be a list of at most {maximum} item(s)" if maximum is not None else f"{key} must be a list")
    for index, item in enumerate(items):
        _ref(item, f"{key}[{index}]")


def validate_request(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ValueError("request file must contain a JSON object")
    kind = body.get("type")
    if not isinstance(kind, str) or kind not in {"image", "video"}:
        raise ValueError("type must be image or video")
    unknown = set(body) - (IMAGE if kind == "image" else VIDEO)
    if unknown:
        raise ValueError(f"unsupported field(s): {', '.join(sorted(unknown))}")
    count = body.get("count")
    maximum = 100 if kind == "image" else 20
    if type(count) is not int or count < 1 or count > maximum:
        raise ValueError(f"count must be an integer from 1 to {maximum}")
    _refs(body, "productImages")
    if kind == "image":
        _ref(body.get("sourceImage"), "sourceImage")
        for key in ("requirement", "ratio", "imageModel", "textModel"):
            _nonempty(body, key)
    else:
        _ref(body.get("sourceVideo"), "sourceVideo")
        for key in ("productDescription", "videoModel", "textModel"):
            _nonempty(body, key)
        _refs(body, "referenceAudios", 3)
        if body.get("replicationMode", "partial") not in {"partial", "full"}:
            raise ValueError("replicationMode must be partial or full")
        if "strategies" in body:
            strategies = body["strategies"]
            names = {"hotOpening", "ownPattern", "industryFission"}
            if not isinstance(strategies, dict) or set(strategies) - names or any(type(value) is not bool for value in strategies.values()):
                raise ValueError("strategies must contain only hotOpening/ownPattern/industryFission booleans")
        if "sourceVideoMetadata" in body:
            meta = body["sourceVideoMetadata"]
            names = {"durationSeconds", "width", "height"}
            if not isinstance(meta, dict) or not meta or set(meta) - names or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in meta.values()):
                raise ValueError("sourceVideoMetadata values must be positive numbers")
    for key in ("industry", "textModel", "resolution"):
        if key in body:
            _nonempty(body, key)
    if "promptOptimization" in body:
        value = body["promptOptimization"]
        required = {"originalDescription", "optimizedDescription"} if kind == "image" else {"originalDescription", "outline"}
        allowed = required | ({"traceId"} if kind == "image" else {"outlineTraceId"})
        if not isinstance(value, dict) or not required.issubset(value) or set(value) - allowed:
            raise ValueError("promptOptimization has missing or unsupported fields")
        if any(not isinstance(item, str) or not item.strip() for item in value.values()):
            raise ValueError("promptOptimization fields must be non-empty strings")
    return body


def validate_key(value: str) -> str:
    if not 8 <= len(value) <= 128 or any(ord(char) < 0x20 or ord(char) > 0x7e for char in value):
        raise ValueError("idempotency key must contain 8-128 printable ASCII characters")
    return value
