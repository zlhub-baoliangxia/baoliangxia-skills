#!/usr/bin/env python3
"""Validate or submit one viral image/video replication request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import GatewayError, api_headers, base_url, fail, print_json, request_json, unwrap_data
from _viral import validate_key, validate_request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-file", required=True, help="UTF-8 JSON request body")
    parser.add_argument("--idempotency-key", required=True, help="Saved key for this logical request")
    parser.add_argument("--base-url")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print request without network or API key")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = Path(args.request_file).expanduser().resolve()
    try:
        body = validate_request(json.loads(path.read_text(encoding="utf-8")))
        key = validate_key(args.idempotency_key)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise GatewayError(str(exc)) from exc
    url = base_url(args.base_url) + "/api/v1/viral-replications"
    if args.dry_run:
        print_json({"method": "POST", "url": url, "idempotencyKey": key, "body": body, "dryRun": True})
        return
    response = unwrap_data(request_json("POST", url, body=body, headers=api_headers(key)))
    if not isinstance(response, dict) or not isinstance(response.get("id"), str):
        raise GatewayError("Viral replication response did not include a batch task id")
    print_json(response)


if __name__ == "__main__":
    try:
        main()
    except GatewayError as exc:
        fail(str(exc))
