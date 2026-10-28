#!/usr/bin/env python3
"""Query or wait for a viral replication batch, then download available outputs."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from urllib.parse import quote, urlencode

from _common import GatewayError, api_headers, base_url, download_outputs, fail, output_urls, print_json, request_json, unwrap_data


TERMINAL = {"completed", "partial", "failed", "stopped"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_task_id")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--interval", type=float, default=20)
    parser.add_argument("--timeout", type=float, default=21600)
    parser.add_argument("--output-dir")
    parser.add_argument("--base-url")
    return parser.parse_args()


def fetch_page(url: str, cursor: str | None = None) -> dict:
    target = url if cursor is None else url + "?" + urlencode({"cursor": cursor})
    response = unwrap_data(request_json("GET", target, headers=api_headers()))
    if not isinstance(response, dict):
        raise GatewayError("Viral replication query response must be a JSON object")
    return response


def collect_outputs(url: str, first: dict) -> list[dict]:
    outputs = first.get("outputs") or []
    if not isinstance(outputs, list):
        raise GatewayError("outputs must be a list")
    result = list(outputs)
    seen = set()
    cursor = first.get("nextCursor")
    while cursor:
        if not isinstance(cursor, str) or cursor in seen:
            raise GatewayError("invalid or repeated output cursor")
        seen.add(cursor)
        page = fetch_page(url, cursor)
        items = page.get("outputs") or []
        if not isinstance(items, list):
            raise GatewayError("outputs must be a list")
        result.extend(items)
        cursor = page.get("nextCursor")
    return result


def main() -> None:
    args = parse_args()
    if not args.batch_task_id.strip() or "/" in args.batch_task_id:
        raise GatewayError("invalid batch task id")
    if args.interval <= 0 or args.timeout < 0:
        raise GatewayError("--interval must be positive and --timeout non-negative")
    url = base_url(args.base_url) + "/api/v1/viral-replications/" + quote(args.batch_task_id, safe="")
    deadline = time.monotonic() + args.timeout
    while True:
        response = fetch_page(url)
        status = str(response.get("status", "")).lower()
        if status not in {"pending", "running", *TERMINAL}:
            raise GatewayError(f"unknown viral replication status: {status or '<empty>'}")
        if not args.wait or status in TERMINAL:
            break
        if time.monotonic() >= deadline:
            response = {**response, "timedOut": True}
            break
        time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
    result = dict(response)
    if status in TERMINAL and args.output_dir:
        outputs = collect_outputs(url, result)
        result["outputs"] = outputs
        result.pop("nextCursor", None)
        urls = output_urls(outputs)
        result["downloaded"] = download_outputs(urls, Path(args.output_dir).expanduser().resolve()) if urls else []
    print_json(result)


if __name__ == "__main__":
    try:
        main()
    except GatewayError as exc:
        fail(str(exc))
