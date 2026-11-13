#!/usr/bin/env python3
"""批量创建媒体任务：单输出模型并发，数量型图片按实际结果补缺。"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from _batch import execute_batch, initial_tasks, validate_options
from _common import GatewayError, fail, print_json
from _generation import session_fields
from create_model_generation import build_parser, parse_args, prepare_generation
from _models import catalog_rows

JOB_FIELDS = {'prompt', 'model', 'aspect_ratio', 'resolution', 'duration', 'output_format',
              'input_upload_id', 'image_upload_id', 'reference_image_id', 'reference_video_id', 'audio_upload_id',
              'reference_audio_id', 'options', 'option', 'watermark'}


def prepare_jobs(args):
    if args.n is not None or args.idempotency_key:
        raise ValueError('批量入口使用--count，不使用--n或共享的--idempotency-key；每个请求自动保存独立键')
    if args.jobs_file:
        if args.count != 1 or any(getattr(args, key, None) for key in JOB_FIELDS):
            raise ValueError('--jobs-file不能与公共生成参数混用；请在每项中填写完整参数')
        rows = json.loads(Path(args.jobs_file).read_text(encoding='utf-8-sig'))
        if not isinstance(rows, list) or not rows:
            raise ValueError('--jobs-file必须是非空JSON数组')
    else:
        rows = [{key: getattr(args, key, None) for key in JOB_FIELDS if getattr(args, key, None) is not None}]
        rows[0]['option'] = args.option
        rows[0]['reference_audio_id'] = args.reference_audio_id
        rows[0]['count'] = args.count
    jobs = []
    for row in rows:
        if not isinstance(row, dict) or set(row) - (JOB_FIELDS | {'count'}):
            raise ValueError('任务清单包含不支持的字段')
        count = row.get('count', 1)
        if type(count) is not int or not 1 <= count <= 100:
            raise ValueError('count必须为1–100的整数')
        item = parse_args([])
        for key, value in row.items():
            if key == 'count':
                continue
            if key in {'input_upload_id', 'reference_image_id', 'reference_video_id', 'reference_audio_id', 'option'}:
                if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                    raise ValueError(f'{key}必须是字符串数组')
            elif key == 'options':
                if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, (str, bool)) for k, v in value.items()):
                    raise ValueError('options必须是字符串或布尔值组成的对象')
                item_options = []
                for option_key, option_value in value.items():
                    item_options.append(f'{option_key}={str(option_value).lower() if isinstance(option_value, bool) else option_value}')
                item.option = item_options
            elif key == 'watermark':
                if type(value) is bool:
                    item.watermark = str(value).lower()
                elif isinstance(value, str) and value in {'true', 'false'}:
                    item.watermark = value
                else:
                    raise ValueError('watermark必须为布尔值')
            elif key == 'duration':
                if value is not None and type(value) is not int:
                    raise ValueError('duration必须为整数')
            elif value is not None and not isinstance(value, str):
                raise ValueError(f'{key}必须是字符串')
            if key not in {'options', 'watermark'}:
                setattr(item, key, value)
        _spec, payload = prepare_generation(item)
        jobs.append({'model': item.model, 'count': count, 'payload': payload})
    if sum(job['count'] for job in jobs) > 100:
        raise ValueError('所有任务的目标总数不能超过100')
    return jobs


def main():
    parser = build_parser()
    parser.description = __doc__
    parser.add_argument('--count', type=int, default=1, help='目标总数；脚本按模型能力自动拆分和补缺')
    parser.add_argument('--jobs-file', help='不同提示词/模型：JSON数组，每项含model、prompt、count及可选参数（下划线命名）')
    parser.add_argument('--output-dir', help='新批次目录；默认baoliangxia_results/batch_<UUID>')
    parser.add_argument('--concurrency', type=int, default=5)
    parser.add_argument('--interval', type=float, default=20)
    parser.add_argument('--timeout', type=float, default=21600)
    args = parser.parse_args()
    if args.list_models:
        print_json(catalog_rows())
        return
    validate_options(args.concurrency, args.interval, args.timeout)
    jobs = prepare_jobs(args)
    # 会话参数是批次级的：只写进第一个初始任务，jobs-file 每一项不接受会话字段。
    session = session_fields(args.new_session, args.session_title)
    if args.dry_run:
        note = '先提交初始任务，再集中轮询；数量型图片仅在completed后按实际缺口补交'
        if session:
            note += '；第一个任务带会话字段并单独先提交，受理后其余任务再并发'
        print_json({'jobs': jobs, 'initialTasks': initial_tasks(jobs, session), 'concurrency': args.concurrency,
                    'note': note})
        return
    directory = Path(args.output_dir or f'baoliangxia_results/batch_{uuid.uuid4()}')
    result = execute_batch(jobs, directory, concurrency=args.concurrency, interval=args.interval,
                           timeout=args.timeout, service_url=args.base_url, download=True, session=session)
    print_json(result)
    if result['status'] != 'completed' or any(t.get('downloadError') for t in result['tasks']):
        raise SystemExit(2)


if __name__ == '__main__':
    try:
        main()
    except (GatewayError, ValueError, OSError) as error:
        fail(str(error))
