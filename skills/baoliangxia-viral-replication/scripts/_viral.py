"""Local validation for the planned viral-replication Gateway request."""

from __future__ import annotations

from typing import Any


COMMON = {"type", "productImages", "industry", "textModel", "resolution", "count"}
INDUSTRIES = {"ecommerce", "beauty", "telecom", "netservice"}
IMAGE = COMMON | {"sourceImage", "requirement", "ratio", "imageModel", "promptOptimization"}
VIDEO = COMMON | {
    "sourceVideo", "referenceAudios", "productDescription", "videoModel", "replicationMode",
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
    for key in ("industry", "textModel", "resolution"):
        if key in body:
            _nonempty(body, key)
    if "industry" in body and body["industry"] not in INDUSTRIES:
        raise ValueError("industry must be ecommerce, beauty, telecom, or netservice")
    if kind == "image" and "promptOptimization" in body:
        value = body["promptOptimization"]
        required = {"originalDescription", "optimizedDescription"}
        allowed = required | {"traceId"}
        if not isinstance(value, dict) or not required.issubset(value) or set(value) - allowed:
            raise ValueError("promptOptimization has missing or unsupported fields")
        if any(not isinstance(item, str) or not item.strip() for item in value.values()):
            raise ValueError("promptOptimization fields must be non-empty strings")
    return body


def validate_key(value: str) -> str:
    if not 8 <= len(value) <= 128 or any(ord(char) < 0x20 or ord(char) > 0x7e for char in value):
        raise ValueError("idempotency key must contain 8-128 printable ASCII characters")
    return value
