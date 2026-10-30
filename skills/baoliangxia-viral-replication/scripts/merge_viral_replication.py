#!/usr/bin/env python3
"""Request a server-side merge for one completed viral video set."""

from __future__ import annotations

import argparse
from urllib.parse import quote

from _common import GatewayError, api_headers, base_url, fail, print_json, request_json, unwrap_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_task_id", help="Batch task id returned by create_viral_replication")
    parser.add_argument("--group-index", type=int, required=True, help="Set groupIndex from segment outputs")
    parser.add_argument("--base-url")
    parser.add_argument("--timeout", type=float, default=600, help="Merge request timeout in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batch_task_id = args.batch_task_id.strip()
    if not batch_task_id or "/" in batch_task_id:
        raise GatewayError("invalid batch task id")
    if args.group_index < 0:
        raise GatewayError("--group-index must be a non-negative integer")
    if args.timeout <= 0:
        raise GatewayError("--timeout must be positive")

    url = (
        base_url(args.base_url)
        + "/api/v1/viral-replications/"
        + quote(batch_task_id, safe="")
        + f"/merge/{args.group_index}"
    )
    response = unwrap_data(request_json("POST", url, headers=api_headers(), timeout=args.timeout))
    if not isinstance(response, dict) or response.get("id") != batch_task_id:
        raise GatewayError("Viral replication merge response did not match the requested task")
    print_json(response)


if __name__ == "__main__":
    try:
        main()
    except GatewayError as exc:
        fail(str(exc))
