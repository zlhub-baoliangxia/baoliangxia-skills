#!/usr/bin/env python3
"""Create a video generation through the baoliangxia REST API."""

import argparse
import json
import uuid

from _common import GatewayError, api_headers, base_url, fail, generation_result, print_json, request_json, upload_ref
from _models import MODELS
from create_model_generation import validate_video_duration


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="Prompt text; forwarded unchanged")
    parser.add_argument("--model", default="doubao-seedance-2.0")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--resolution", default="1080p")
    parser.add_argument("--image-upload-id")
    parser.add_argument("--reference-image-id", action="append", default=[])
    parser.add_argument("--reference-video-id", action="append", default=[])
    parser.add_argument("--audio-upload-id")
    parser.add_argument("--metadata-json", help="Additional metadata as a JSON object")
    parser.add_argument("--idempotency-key", default=None)
    parser.add_argument("--base-url", default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    spec = MODELS.get(args.model)
    if spec is not None:
        validate_video_duration(args, spec)
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "duration": args.duration,
        "aspectRatio": args.aspect_ratio,
        "resolution": args.resolution,
    }
    if args.image_upload_id:
        payload["imageUrl"] = upload_ref(args.image_upload_id)
    if args.reference_image_id:
        payload["referenceImages"] = [upload_ref(value) for value in args.reference_image_id]
    if args.reference_video_id:
        payload["referenceVideos"] = [upload_ref(value) for value in args.reference_video_id]
    if args.audio_upload_id:
        payload["audio"] = upload_ref(args.audio_upload_id)
    if args.metadata_json:
        metadata = json.loads(args.metadata_json)
        if not isinstance(metadata, dict):
            raise ValueError("--metadata-json must contain a JSON object")
        payload["metadata"] = metadata
    idempotency_key = args.idempotency_key or str(uuid.uuid4())
    response = request_json(
        "POST",
        base_url(args.base_url) + "/api/v1/videos/generations",
        body=payload,
        headers=api_headers(idempotency_key),
    )
    result = generation_result(response)
    result["idempotencyKey"] = idempotency_key
    print_json(result)


if __name__ == "__main__":
    try:
        main()
    except (GatewayError, ValueError, json.JSONDecodeError) as exc:
        fail(str(exc))

