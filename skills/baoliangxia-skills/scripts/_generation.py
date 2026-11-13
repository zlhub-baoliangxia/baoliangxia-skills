#!/usr/bin/env python3
"""Shared submission helpers for model-specific generation scripts."""

from __future__ import annotations

import argparse
import unicodedata
import uuid
from typing import Any

from _common import api_headers, base_url, generation_result, print_json, request_json, upload_ref

SESSION_TITLE_MAX_LENGTH = 50


def add_transport_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--idempotency-key", default=None)
    parser.add_argument("--base-url", default=None)


def add_session_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--new-session", action="store_true",
        help="放进爆量匣生成页新开的会话；仅在用户明确要求新开或单独分组时使用",
    )
    parser.add_argument(
        "--session-title",
        help="本次新建会话时使用的标题（最多50字）；本次没有新建会话时服务端忽略",
    )


def normalize_session_title(value: str | None) -> str | None:
    """与服务端同口径：去掉控制字符、去首尾空白，空串视同未传，超过50字拒绝。"""
    if value is None:
        return None
    normalized = "".join(ch for ch in value if unicodedata.category(ch) != "Cc").strip()
    if not normalized:
        return None
    if len(normalized) > SESSION_TITLE_MAX_LENGTH:
        raise ValueError(f"--session-title must be at most {SESSION_TITLE_MAX_LENGTH} characters")
    return normalized


def session_fields(new_session: bool, session_title: str | None) -> dict[str, Any]:
    """用户没要求时返回空字典，请求体里不出现会话字段。"""
    fields: dict[str, Any] = {}
    if new_session:
        fields["newSession"] = True
    title = normalize_session_title(session_title)
    if title:
        fields["sessionTitle"] = title
    return fields


def append_if_present(payload: dict[str, Any], key: str, value: Any) -> None:
    if value is not None and value != []:
        payload[key] = value


def upload_refs(values: list[str]) -> list[dict[str, str]]:
    return [upload_ref(value) for value in values]


def bounded_int(minimum: int, maximum: int):
    def parse(value: str) -> int:
        parsed = int(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return parsed
    return parse


def wan_duration(value: str) -> int:
    parsed = int(value)
    if parsed != -1 and not 2 <= parsed <= 30:
        raise argparse.ArgumentTypeError("must be -1 or between 2 and 30")
    return parsed


def submit(kind: str, payload: dict[str, Any], args: argparse.Namespace) -> None:
    idempotency_key = args.idempotency_key or str(uuid.uuid4())
    response = request_json(
        "POST",
        base_url(args.base_url) + f"/api/v1/{kind}/generations",
        body=payload,
        headers=api_headers(idempotency_key),
    )
    result = generation_result(response)
    result["idempotencyKey"] = idempotency_key
    print_json(result)
