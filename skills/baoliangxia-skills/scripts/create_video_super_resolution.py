#!/usr/bin/env python3
"""对已完成视频或上传视频提升画质。单条直接提交，2～10 条走批量。"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from typing import Any

from _batch import execute_batch
from _common import (
    GatewayError,
    api_headers,
    base_url,
    fail,
    generation_result,
    guess_kind,
    guess_mime_type,
    print_json,
    request_json,
    send_upload,
    unwrap_data,
)
from _generation import add_session_args, add_transport_args, session_fields

ENDPOINT = "/api/v1/videos/super-resolutions"
MAX_ITEMS = 10
RESOLUTIONS = {"720p", "1080p", "2k", "4k"}
DEFAULT_TIMEOUT_SECONDS = 21600


class AppendSource(argparse.Action):
    """按命令行出现顺序收集来源，三种参数各自成条，不合并进同一条。"""

    def __call__(self, parser, namespace, values, option_string=None):
        current = list(getattr(namespace, self.dest) or [])
        kind = {
            "--generation-id": "generation_id",
            "--upload-id": "upload_id",
            "--file": "file",
        }[option_string or ""]
        current.append({"kind": kind, "value": values})
        setattr(namespace, self.dest, current)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation-id", action=AppendSource, dest="sources", help="已完成的视频生成记录 ID，可重复")
    parser.add_argument("--upload-id", action=AppendSource, dest="sources", help="已完成的视频上传 ID，可重复")
    parser.add_argument("--file", action=AppendSource, dest="sources", help="本地视频，先上传再提交，可重复")
    parser.add_argument("--target-resolution", required=True, help="720p、1080p、2k 或 4k")
    parser.add_argument("--plan-key", default="general", help="画质方案，缺省 general")
    parser.add_argument("--output-dir", help="2 条及以上时写入 batch.json 的目录")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    add_session_args(parser)
    add_transport_args(parser)
    parser.set_defaults(sources=[])
    return parser


def normalize_resolution(value: str) -> str:
    token = str(value or "").strip().lower()
    if token not in RESOLUTIONS:
        raise ValueError("targetResolution 必须是 720p、1080p、2k 或 4k")
    return token


def normalize_plan_key(value: str | None) -> str:
    token = str(value or "").strip().lower()
    return token or "general"


def validate_sources(sources: list[dict]) -> list[dict]:
    if not 1 <= len(sources) <= MAX_ITEMS:
        raise ValueError(f"每次提交 1～{MAX_ITEMS} 条视频")
    normalized = []
    for item in sources:
        value = str(item.get("value") or "").strip()
        if not value:
            raise ValueError("来源不能为空")
        normalized.append({"kind": item["kind"], "value": value})
    return normalized


def payload_for_source(source: dict, target_resolution: str, plan_key: str) -> dict[str, Any]:
    """一条请求只带 generationId 或 uploadId。两个都有或都没有时拒绝。"""
    generation_id = str(source.get("generationId") or "").strip()
    upload_id = str(source.get("uploadId") or "").strip()
    if bool(generation_id) == bool(upload_id):
        raise ValueError("generationId 与 uploadId 必须二选一")
    payload: dict[str, Any] = {
        "targetResolution": normalize_resolution(target_resolution),
        "planKey": normalize_plan_key(plan_key),
    }
    if generation_id:
        payload["generationId"] = generation_id
    else:
        payload["uploadId"] = upload_id
    return payload


def upload_local_video(path: str, service_url: str | None) -> str:
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        raise GatewayError(f"File not found: {file_path}")
    mime_type = guess_mime_type(file_path)
    kind = guess_kind(mime_type)
    if kind != "video":
        raise ValueError("提升画质只接受视频文件")
    root = base_url(service_url)
    ticket = unwrap_data(request_json(
        "POST",
        root + "/api/v1/uploads/ticket",
        body={"filename": file_path.name, "mimeType": mime_type, "size": file_path.stat().st_size, "kind": "video"},
        headers=api_headers(),
    ))
    if not isinstance(ticket, dict):
        raise GatewayError("Upload ticket response must be a JSON object")
    upload_id = str(ticket.get("uploadId") or "").strip()
    upload_url = ticket.get("host") or ticket.get("uploadUrl") or ticket.get("url")
    if not upload_id or not upload_url:
        raise GatewayError("Upload ticket did not include uploadId and host/uploadUrl")
    upload_url = str(upload_url)
    if "://" not in upload_url:
        upload_url = f"https://{upload_url.lstrip('/')}"
    send_upload(upload_url, str(ticket.get("method") or "POST"), ticket.get("fields") or {}, file_path, mime_type)
    unwrap_data(request_json("POST", root + f"/api/v1/uploads/{upload_id}/complete", headers=api_headers()))
    return upload_id


def resolve_sources(sources: list[dict], service_url: str | None) -> list[dict]:
    resolved = []
    for item in sources:
        if item["kind"] == "generation_id":
            resolved.append({"generationId": item["value"]})
        elif item["kind"] == "upload_id":
            resolved.append({"uploadId": item["value"]})
        elif item["kind"] == "file":
            resolved.append({"uploadId": upload_local_video(item["value"], service_url)})
        else:
            raise ValueError("不支持的来源")
    return resolved


def build_jobs(sources: list[dict], target_resolution: str, plan_key: str) -> list[dict]:
    jobs = []
    for source in sources:
        jobs.append({
            "model": "video-sr",
            "count": 1,
            "payload": payload_for_source(source, target_resolution, plan_key),
            "endpoint": ENDPOINT,
            "allow_unavailable": True,
        })
    return jobs


def plan_submission(sources: list[dict], target_resolution: str, plan_key: str, session: dict) -> dict:
    """本地校验后给出提交计划。会话字段只在单条上，或多条时交给批量的第一条。"""
    checked = validate_sources(sources)
    resolution = normalize_resolution(target_resolution)
    key = normalize_plan_key(plan_key)
    if len(checked) == 1 and checked[0]["kind"] != "file":
        source = {"generationId": checked[0]["value"]} if checked[0]["kind"] == "generation_id" else {"uploadId": checked[0]["value"]}
        payload = payload_for_source(source, resolution, key)
        payload.update(session)
        return {"mode": "single", "payload": payload, "endpoint": ENDPOINT, "sources": checked}
    return {"mode": "batch" if len(checked) > 1 else "single", "sources": checked, "resolution": resolution, "planKey": key, "session": session, "endpoint": ENDPOINT}


def submit_one(payload: dict, service_url: str | None, idempotency_key: str | None) -> dict:
    key = idempotency_key or str(uuid.uuid4())
    response = request_json(
        "POST",
        base_url(service_url) + ENDPOINT,
        body=payload,
        headers=api_headers(key),
    )
    result = generation_result(response)
    result["idempotencyKey"] = key
    return result


def batch_succeeded(state: dict) -> bool:
    """与 create_batch_generations.py 同口径：全部完成且全部下载成功才算成功，否则退出码 2。"""
    return state.get("status") == "completed" and not any(task.get("downloadError") for task in state.get("tasks", []))


def batch_summary(state: dict) -> dict:
    """批量汇总。失败原因和下载错误也要出现在屏幕输出里，不能只留在 batch.json。"""
    tasks = []
    for task in state.get("tasks", []):
        item = {
            "generationId": task.get("generationId"),
            "status": task.get("status"),
            "session": (task.get("submission") or {}).get("session"),
        }
        for key in ("error", "queryError", "downloadError"):
            if task.get(key):
                item[key] = task[key]
        tasks.append(item)
    return {
        "status": state.get("status"),
        "remainingCount": sum(int(job.get("remainingCount") or 0) for job in state.get("jobs", [])),
        "stateFile": state.get("stateFile"),
        "tasks": tasks,
    }


def main() -> None:
    args = build_parser().parse_args()
    session = session_fields(args.new_session, args.session_title)
    sources = validate_sources(args.sources)
    resolution = normalize_resolution(args.target_resolution)
    plan_key = normalize_plan_key(args.plan_key)
    if len(sources) > 1 and args.idempotency_key:
        raise ValueError("多条任务各自使用独立幂等键，不要传 --idempotency-key")
    if len(sources) > 1 and not args.output_dir:
        raise ValueError("2 条及以上需要 --output-dir")
    resolved = resolve_sources(sources, args.base_url)
    if len(resolved) == 1:
        payload = payload_for_source(resolved[0], resolution, plan_key)
        payload.update(session)
        print_json(submit_one(payload, args.base_url, args.idempotency_key))
        return
    jobs = build_jobs(resolved, resolution, plan_key)
    state = execute_batch(
        jobs,
        Path(args.output_dir),
        concurrency=args.concurrency,
        interval=20,
        timeout=args.timeout,
        service_url=args.base_url,
        download=True,
        session=session,
    )
    print_json(batch_summary(state))
    if not batch_succeeded(state):
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except (GatewayError, ValueError, OSError) as exc:
        fail(str(exc))
