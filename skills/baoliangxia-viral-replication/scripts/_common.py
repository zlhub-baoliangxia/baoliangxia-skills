#!/usr/bin/env python3
"""Shared HTTP helpers for the baoliangxia Agent Gateway scripts."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Iterable


DEFAULT_BASE_URL = "https://baoliangxia.com/"
API_KEY_ENV = "BAOLIANGXIA_AGENT_GATEWAY_API_KEY"
BASE_URL_ENV = "BAOLIANGXIA_AGENT_GATEWAY_BASE_URL"
# 旧版变量名，仅作兼容回退，避免已配置旧变量的用户升级后失效
LEGACY_API_KEY_ENV = "CANVASMIND_AGENT_GATEWAY_API_KEY"
LEGACY_BASE_URL_ENV = "CANVASMIND_AGENT_GATEWAY_BASE_URL"


class GatewayError(RuntimeError):
    def __init__(self, message: str, *, status=None, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def base_url(value: str | None) -> str:
    return (value or os.environ.get(BASE_URL_ENV) or os.environ.get(LEGACY_BASE_URL_ENV) or DEFAULT_BASE_URL).rstrip("/")


def api_key() -> str:
    value = (os.environ.get(API_KEY_ENV) or os.environ.get(LEGACY_API_KEY_ENV) or "").strip()
    if not value:
        raise GatewayError(f"Missing environment variable: {API_KEY_ENV}")
    return value


def api_headers(idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Accept": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def request_json(
    method: str,
    url: str,
    *,
    body: Any | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 60,
) -> Any:
    request_headers = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json; charset=utf-8")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        detail = raw.decode("utf-8", errors="replace")
        retry_after = exc.headers.get('Retry-After')
        try:
            parsed = json.loads(detail)
            detail = json.dumps(parsed, ensure_ascii=False)
            if isinstance(parsed, dict) and isinstance(parsed.get('error'), dict):
                retry_after = retry_after or parsed['error'].get('retryAfterSeconds')
        except json.JSONDecodeError:
            pass
        try:
            retry_after = max(1, float(retry_after)) if retry_after is not None else None
        except (TypeError, ValueError):
            retry_after = None
        raise GatewayError(f"HTTP {exc.code} from {url}: {detail}", status=exc.code, retry_after=retry_after) from exc
    except urllib.error.URLError as exc:
        raise GatewayError(f"Request failed for {url}: {exc.reason}") from exc

    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GatewayError(f"Invalid JSON response from {url}") from exc


def unwrap_data(value: Any) -> Any:
    if isinstance(value, dict) and isinstance(value.get("data"), dict):
        return value["data"]
    return value


def generation_result(value: Any) -> dict[str, Any]:
    value = unwrap_data(value)
    if not isinstance(value, dict):
        raise GatewayError("Generation response must be a JSON object")
    generation_id = value.get("generationId") or value.get("id")
    if not generation_id:
        raise GatewayError("Generation response did not include id or generationId")
    result = dict(value)
    result["generationId"] = generation_id
    return result


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def fail(message: str) -> None:
    print(json.dumps({"error": str(message)}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(1)


def upload_ref(upload_id: str) -> dict[str, str]:
    return {"uploadId": upload_id}


def encode_multipart(fields: dict[str, Any], file_path: Path, mime_type: str) -> tuple[bytes, str]:
    boundary = f"----baoliangxia-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode("ascii"),
            (
                f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8"),
            file_path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )
    return b"".join(chunks), boundary


def send_upload(
    url: str,
    method: str,
    fields: dict[str, Any],
    file_path: Path,
    mime_type: str,
    timeout: float = 300,
) -> None:
    method = method.upper()
    if method == "POST" or fields:
        body, boundary = encode_multipart(fields, file_path, mime_type)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    else:
        body = file_path.read_bytes()
        headers = {"Content-Type": mime_type}
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GatewayError(f"Upload failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GatewayError(f"Upload failed: {exc.reason}") from exc


def guess_kind(mime_type: str) -> str:
    kind = mime_type.split("/", 1)[0]
    if kind not in {"image", "video", "audio"}:
        raise GatewayError(f"Unsupported media type: {mime_type}")
    return kind


def guess_mime_type(path: Path) -> str:
    mime_type, _encoding = mimetypes.guess_type(path.name)
    if not mime_type:
        raise GatewayError("Could not infer MIME type; pass --mime-type")
    return mime_type


def output_urls(outputs: Any) -> list[str]:
    urls: list[str] = []
    items: Iterable[Any]
    if isinstance(outputs, list):
        items = outputs
    elif outputs is None:
        items = []
    else:
        items = [outputs]
    for item in items:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            url = item.get("url") or item.get("downloadUrl")
            if isinstance(url, str):
                urls.append(url)
    return urls


def download_outputs(urls: Iterable[str], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    for index, url in enumerate(urls, 1):
        request = urllib.request.Request(url, headers={"User-Agent": "baoliangxia-skill/1"})
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                data = response.read()
                content_type = response.headers.get_content_type()
        except urllib.error.URLError as exc:
            raise GatewayError(f"Could not download {url}: {exc.reason}") from exc
        suffix = Path(urllib.parse.urlparse(url).path).suffix
        if not suffix:
            suffix = mimetypes.guess_extension(content_type) or ".bin"
        destination = output_dir / f"{index:02d}{suffix}"
        destination.write_bytes(data)
        downloaded.append(str(destination.resolve()))
    return downloaded
