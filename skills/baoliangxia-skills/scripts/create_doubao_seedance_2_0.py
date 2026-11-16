#!/usr/bin/env python3
"""Create a doubao-seedance-2.0 video through baoliangxia Agent Gateway."""

import argparse

from _common import GatewayError, fail, upload_ref
from _generation import add_transport_args, append_if_present, submit, upload_refs


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="Prompt text; forwarded unchanged")
    parser.add_argument("--duration", type=int)
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--resolution", choices=("480p", "720p", "1080p", "4K"))
    parser.add_argument("--image-upload-id", help="General guide/cover image; not an explicit first/last-frame role")
    parser.add_argument("--reference-image-id", action="append", default=[])
    parser.add_argument("--reference-video-id", action="append", default=[])
    parser.add_argument("--audio-upload-id", help="Uploaded reference audio, not an output-audio switch")
    add_transport_args(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.duration is not None and not 1 <= args.duration <= 15:
        raise ValueError("--duration must be between 1 and 15")
    payload = {"model": "doubao-seedance-2.0", "prompt": args.prompt}
    append_if_present(payload, "duration", args.duration)
    append_if_present(payload, "aspectRatio", args.aspect_ratio)
    append_if_present(payload, "resolution", args.resolution)
    if args.image_upload_id:
        payload["imageUrl"] = upload_ref(args.image_upload_id)
    append_if_present(payload, "referenceImages", upload_refs(args.reference_image_id))
    append_if_present(payload, "referenceVideos", upload_refs(args.reference_video_id))
    if args.audio_upload_id:
        payload["audio"] = upload_ref(args.audio_upload_id)
    submit("videos", payload, args)


if __name__ == "__main__":
    try:
        main()
    except (GatewayError, ValueError) as exc:
        fail(str(exc))
