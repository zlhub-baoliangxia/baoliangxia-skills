#!/usr/bin/env python3
"""Upload a local image, video, or audio file and return its uploadId."""

import argparse
from pathlib import Path

from _common import (
    GatewayError,
    api_headers,
    base_url,
    fail,
    guess_kind,
    guess_mime_type,
    print_json,
    request_json,
    send_upload,
    unwrap_data,
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--mime-type")
    parser.add_argument("--kind", choices=["image", "video", "audio"])
    parser.add_argument("--base-url", default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        raise GatewayError(f"File not found: {path}")
    mime_type = args.mime_type or guess_mime_type(path)
    kind = args.kind or guess_kind(mime_type)
    root = base_url(args.base_url)
    ticket = unwrap_data(
        request_json(
            "POST",
            root + "/api/v1/uploads/ticket",
            body={
                "filename": path.name,
                "mimeType": mime_type,
                "size": path.stat().st_size,
                "kind": kind,
            },
            headers=api_headers(),
        )
    )
    if not isinstance(ticket, dict):
        raise GatewayError("Upload ticket response must be a JSON object")
    upload_id = ticket.get("uploadId")
    upload_url = ticket.get("host") or ticket.get("uploadUrl") or ticket.get("url")
    if not upload_id or not upload_url:
        raise GatewayError("Upload ticket did not include uploadId and host/uploadUrl")
    send_upload(
        upload_url,
        str(ticket.get("method") or "POST"),
        ticket.get("fields") or {},
        path,
        mime_type,
    )
    completed = unwrap_data(
        request_json(
            "POST",
            root + f"/api/v1/uploads/{upload_id}/complete",
            headers=api_headers(),
        )
    )
    result = dict(completed) if isinstance(completed, dict) else {}
    result.setdefault("uploadId", upload_id)
    result.setdefault("status", "completed")
    print_json(result)


if __name__ == "__main__":
    try:
        main()
    except GatewayError as exc:
        fail(str(exc))
