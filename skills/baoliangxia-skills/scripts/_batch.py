"""批量提交与集中轮询；工作线程仅做 HTTP，状态由主线程落盘。"""

from __future__ import annotations

import json
import math
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from _common import (GatewayError, api_headers, base_url, download_outputs,
                     generation_result, output_urls, request_json, unwrap_data)
from _models import MODELS

TERMINAL = {'completed', 'failed', 'stopped'}
SEEDREAM = {'doubao-seedream-4.5', 'doubao-seedream-5.0-lite'}


def task_urls(task):
    return list(dict.fromkeys(url for url in output_urls(task.get('result', {}).get('outputs')) if url))


def validate_options(concurrency, interval, timeout):
    if not 1 <= concurrency <= 20 or not math.isfinite(interval) or not math.isfinite(timeout) or interval < 0 or timeout < 0:
        raise ValueError('并发必须为1–20；轮询间隔和超时必须是有限的非负数')


def request_capacity(job: dict) -> int:
    spec = MODELS[job['model']]
    capacity = spec.max_outputs or 1
    if job['model'] in SEEDREAM:
        capacity = min(capacity, 15 - len(job['payload'].get('inputImages', [])))
    if capacity < 1:
        raise ValueError('参考图数量已达上限，没有生成图片的位置')
    return capacity


def initial_tasks(jobs: list[dict], session: dict | None = None) -> list[dict]:
    tasks = []
    for index, job in enumerate(jobs):
        if MODELS[job['model']].max_outputs:
            tasks.append(new_task(index, job, min(job['count'], request_capacity(job))))
        else:
            tasks.extend(new_task(index, job, 1) for _ in range(job['count']))
    if session and tasks:
        # 会话字段只放在第一个初始任务上；其余任务和补缺任务都不带，追加进它所在的会话。
        tasks[0]['payload'].update(session)
        tasks[0]['carriesSession'] = True
    return tasks


def new_task(index: int, job: dict, count: int) -> dict:
    spec = MODELS[job['model']]
    payload = dict(job['payload'])
    # 数量能力取模型与网关的交集；视频/Pro/Gemini 不带 n。
    payload.pop('n', None)
    if spec.max_outputs:
        payload['n'] = count
    return {'jobIndex': index, 'endpoint': f'/api/v1/{spec.kind}/generations',
            'payload': payload, 'requestedCount': count,
            'idempotencyKey': str(uuid.uuid4()), 'status': 'prepared'}


def save_state(state: dict, directory: Path) -> None:
    temporary = directory / 'batch.json.tmp'
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(directory / 'batch.json')


def parallel(pool, tasks, function):
    futures = {pool.submit(function, task): task for task in tasks}
    for future in as_completed(futures):
        task = futures[future]
        try:
            yield task, future.result(), None
        except (GatewayError, OSError, ValueError) as error:
            yield task, None, error


def execute_batch(jobs: list[dict], output_dir: Path, *, concurrency=5,
                  interval=20, timeout=21600, service_url=None, download=False,
                  session: dict | None = None) -> dict:
    validate_options(concurrency, interval, timeout)
    if not jobs or any(type(job['count']) is not int or job['count'] < 1 for job in jobs) or sum(job['count'] for job in jobs) > 100:
        raise ValueError('批量目标总数必须为1–100')
    for job in jobs:
        request_capacity(job)
        if MODELS[job['model']].unavailable_reason:
            raise ValueError('模型当前不可用')
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if (output_dir / 'batch.json').exists():
        raise ValueError('输出目录已有batch.json，请继续查询原任务，或为新批次选择新目录')
    # 提交前先检查认证，避免无密钥时产生不确定的本地任务。
    api_headers()
    root = base_url(service_url)
    state = {'status': 'running', 'jobs': jobs, 'tasks': initial_tasks(jobs, session),
             'requestedCount': sum(job['count'] for job in jobs), 'completedCount': 0,
             'baseUrl': root, 'stateFile': str(output_dir / 'batch.json')}
    started = time.monotonic()
    deadline = started + timeout
    # 独占创建，避免两个进程同时指定相同目录时覆盖幂等键。
    try:
        with (output_dir / 'batch.json').open('x', encoding='utf-8') as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
    except FileExistsError as error:
        raise ValueError('输出目录已有batch.json，请使用新目录') from error

    def submit(task):
        for attempt in range(3):
            try:
                return generation_result(request_json('POST', root + task['endpoint'],
                                         body=task['payload'], headers=api_headers(task['idempotencyKey'])))
            except GatewayError as error:
                # 只重试明确拒绝受理的429；传输中断等不确定结果交给原键恢复。
                delay = error.retry_after or 60
                if error.status != 429 or attempt == 2 or time.monotonic() + delay >= deadline:
                    raise
                time.sleep(delay)

    def query(task):
        response = unwrap_data(request_json('GET', root + '/api/v1/generations/' + task['generationId'], headers=api_headers()))
        if not isinstance(response, dict):
            raise GatewayError('Generation response must be a JSON object')
        return response

    def record_submission(task, response, error):
        if error:
            rejected = getattr(error, 'status', None) in {400, 401, 402, 403, 404, 422, 429}
            task.update(status='rejected' if rejected else 'submission_unknown', error=str(error))
        else:
            task.update(generationId=response['generationId'], status='pending', submission=response)
        save_state(state, output_dir)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        while True:
            prepared = [t for t in state['tasks'] if t['status'] == 'prepared']
            stage = time.monotonic()
            opening = [t for t in prepared if t.get('carriesSession')]
            rest = [t for t in prepared if not t.get('carriesSession')]
            # 带会话字段的任务先单独提交，有了受理结果再并发其余任务。若同时提交，
            # 其余任务可能先追加进当天旧会话，新会话里只剩第一个任务。
            # 第一个任务未受理时其余任务照常提交，会话以各任务响应里的 session 为准。
            for task, response, error in parallel(pool, opening, submit):
                record_submission(task, response, error)
            # 所有创建请求完成受理后才开始轮询；单个创建失败不取消其它任务。
            for task, response, error in parallel(pool, rest, submit):
                record_submission(task, response, error)
            if prepared:
                print(json.dumps({'phase': 'submit', 'tasks': len(prepared), 'elapsedSeconds': round(time.monotonic() - stage, 3)}), file=sys.stderr)

            active = [t for t in state['tasks'] if t['status'] in {'pending', 'running'}]
            round_start = time.monotonic()
            for task, response, error in parallel(pool, active, query):
                if error:
                    task['queryError'] = str(error)
                    task['retryAfterSeconds'] = getattr(error, 'retry_after', None) or 60
                else:
                    task.pop('queryError', None)
                    task.pop('retryAfterSeconds', None)
                    status = str(response.get('status', '')).lower()
                    if status not in TERMINAL | {'pending', 'running'}:
                        task['queryError'] = 'Unknown generation status; continue querying original ID'
                    else:
                        task.update(status=status, result=response)
                save_state(state, output_dir)

            state['completedCount'] = sum(len(task_urls(t)) for t in state['tasks'] if t['status'] == 'completed')
            # 同一逻辑任务只允许一个数量型请求在途，终态有产出才补缺。
            for index, job in enumerate(jobs):
                group = [t for t in state['tasks'] if t['jobIndex'] == index]
                if not MODELS[job['model']].max_outputs:
                    continue
                if any(t['status'] != 'completed' or not task_urls(t) for t in group):
                    continue
                actual = sum(len(task_urls(t)) for t in group)
                remaining = job['count'] - actual
                if remaining > 0 and time.monotonic() < deadline:
                    state['tasks'].append(new_task(index, job, min(remaining, request_capacity(job))))
            save_state(state, output_dir)
            if any(t['status'] == 'prepared' for t in state['tasks']):
                continue
            pending = [t for t in state['tasks'] if t['status'] in {'pending', 'running'}]
            if not pending or time.monotonic() >= deadline:
                for task in pending:
                    task['timedOut'] = True
                break
            # 默认以100次/分钟估算，给默认120次查询限额留余量；429按服务端建议退避。
            delay = max(interval, len(active) * 60 / 100,
                        max((t.get('retryAfterSeconds', 0) for t in pending), default=0))
            time.sleep(min(max(0, delay - (time.monotonic() - round_start)), max(0, deadline - time.monotonic())))

    for index, job in enumerate(jobs):
        actual = sum(len(task_urls(t)) for t in state['tasks'] if t['jobIndex'] == index and t['status'] == 'completed')
        job.update(completedCount=actual, remainingCount=max(0, job['count'] - actual))
    if any(t.get('timedOut') for t in state['tasks']):
        state['status'] = 'pending'
    elif all(job['remainingCount'] == 0 for job in jobs):
        state['status'] = 'completed'
    else:
        state['status'] = 'partial' if state['completedCount'] else 'incomplete'
    save_state(state, output_dir)
    if download:
        for index, task in enumerate(state['tasks']):
            if task['status'] != 'completed':
                continue
            try:
                task['downloaded'] = download_outputs(task_urls(task), output_dir / f'{index + 1:03d}_{task["generationId"]}')
            except (GatewayError, OSError) as error:
                task['downloadError'] = str(error)
            save_state(state, output_dir)
    state['elapsedSeconds'] = round(time.monotonic() - started, 3)
    print(json.dumps({'phase': 'finished', 'tasks': len(state['tasks']), 'elapsedSeconds': state['elapsedSeconds']}), file=sys.stderr)
    save_state(state, output_dir)
    return state
