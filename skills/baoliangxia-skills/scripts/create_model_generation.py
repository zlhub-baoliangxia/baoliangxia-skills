#!/usr/bin/env python3
"""Create an image or video using an enabled baoliangxia database model identifier."""

from __future__ import annotations

import argparse

from _common import GatewayError, fail, print_json, upload_ref
from _generation import add_session_args, add_transport_args, append_if_present, session_fields, submit, upload_refs
from _models import MODELS, ModelSpec, catalog_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", help="Prompt text; forwarded unchanged")
    parser.add_argument("--model", help="Exact enabled database modelKey")
    parser.add_argument("--list-models", action="store_true", help="Print the bundled model catalog and exit")
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--resolution")
    parser.add_argument("--duration", type=int)
    parser.add_argument("--n", type=int)
    parser.add_argument("--output-format")
    parser.add_argument("--input-upload-id", action="append", default=[])
    parser.add_argument("--image-upload-id")
    parser.add_argument("--reference-image-id", action="append", default=[])
    parser.add_argument("--reference-video-id", action="append", default=[])
    parser.add_argument("--audio-upload-id")
    parser.add_argument("--reference-audio-id", action="append", default=[])
    parser.add_argument("--option", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--watermark", choices=("true", "false"), help="Gateway watermark option")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate arguments and print the endpoint/payload without authentication or network access",
    )
    add_session_args(parser)
    add_transport_args(parser)
    return parser


def parse_args(argv=None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def require_choice(label: str, value: str | None, choices: tuple[str, ...]) -> None:
    if value is None:
        return
    if not choices:
        raise ValueError(f"{label} is not exposed for this model by Agent Gateway")
    if value not in choices:
        raise ValueError(f"{label} must be one of: {', '.join(choices)}")


def require_count(label: str, values: list[str], maximum: int | None) -> None:
    if values and maximum is None:
        raise ValueError(f"{label} is not exposed for this model by Agent Gateway")
    if maximum is not None and len(values) > maximum:
        raise ValueError(f"{label} accepts at most {maximum} item(s)")


def validate_duration(spec: ModelSpec, value: int | None) -> None:
    if value is None:
        if spec.duration_required:
            raise ValueError("--duration is required for this model")
        return
    if value == -1 and spec.allow_adaptive_duration:
        return
    if spec.duration_values:
        if value not in spec.duration_values:
            choices = ", ".join(str(item) for item in spec.duration_values)
            raise ValueError(f"--duration must be one of: {choices}")
        return
    if spec.duration_min is None and spec.duration_max is None:
        raise ValueError("--duration is not exposed for this model by Agent Gateway")
    if spec.duration_min is not None and value < spec.duration_min:
        raise ValueError(f"--duration must be at least {spec.duration_min}")
    if spec.duration_max is not None and value > spec.duration_max:
        raise ValueError(f"--duration must be at most {spec.duration_max}")


def validate_common(args: argparse.Namespace, spec: ModelSpec) -> None:
    require_choice("--aspect-ratio", args.aspect_ratio, spec.ratios)
    require_choice("--resolution", args.resolution, spec.resolutions)
    validate_duration(spec, args.duration)

    if args.n is not None:
        if spec.max_outputs is None:
            raise ValueError("--n is not exposed for this model by Agent Gateway")
        if not 1 <= args.n <= spec.max_outputs:
            raise ValueError(f"--n must be between 1 and {spec.max_outputs}")

    require_choice("--output-format", args.output_format, spec.output_formats)
    require_count("--input-upload-id", args.input_upload_id, spec.max_input_images)

    video_images = list(args.reference_image_id)
    if args.image_upload_id:
        video_images.insert(0, args.image_upload_id)
    require_count("video image inputs", video_images, spec.max_reference_images)
    require_count("--reference-video-id", args.reference_video_id, spec.max_reference_videos)
    require_count("--reference-audio-id", args.reference_audio_id, spec.max_reference_audios)
    if args.audio_upload_id and args.reference_audio_id:
        raise ValueError("--audio-upload-id and --reference-audio-id cannot be used together")
    if args.audio_upload_id and not spec.allow_audio:
        raise ValueError("--audio-upload-id is not exposed for this model by Agent Gateway")
    if args.reference_audio_id and not spec.allow_audio:
        raise ValueError("--reference-audio-id is not exposed for this model by Agent Gateway")

    options = dict(spec.gateway_option_defaults or {})
    explicit = {}
    for item in args.option:
        if "=" not in item:
            raise ValueError("--option must use KEY=VALUE")
        key, value = item.split("=", 1)
        if key in explicit:
            raise ValueError(f"duplicate --option key: {key}")
        explicit[key] = value
    if args.watermark is not None:
        if "watermark" in explicit:
            raise ValueError("--watermark cannot be combined with --option watermark=...")
        explicit["watermark"] = args.watermark
    allowed = spec.gateway_options or {}
    for key, value in explicit.items():
        if key not in allowed:
            raise ValueError(f"option {key!r} is not exposed for this model by Agent Gateway")
        choices = allowed[key]
        if choices is None:
            if value not in {"true", "false"}:
                raise ValueError(f"option {key} must be true or false")
            options[key] = value == "true"
        else:
            if value not in choices:
                raise ValueError(f"option {key} must be one of: {', '.join(choices)}")
            options[key] = value
    if args.model == "doubao-seedance-2.5":
        has_media = bool(args.image_upload_id or args.reference_image_id or args.reference_video_id or args.reference_audio_id or args.audio_upload_id)
        task_type = options.get("omni_reference_task_type")
        if task_type in {"edit", "extend"} and not args.reference_video_id:
            raise ValueError("omni_reference_task_type=edit/extend requires --reference-video-id")
        if has_media:
            options.setdefault("omni_reference_task_type", "reference")
        else:
            options.pop("omni_reference_task_type", None)
    args.gateway_options = options

    if spec.kind == "images" and (
        args.image_upload_id or args.reference_image_id or args.reference_video_id or args.audio_upload_id
    ):
        raise ValueError("image models accept references through --input-upload-id only")
    if spec.kind == "videos" and args.input_upload_id:
        raise ValueError("video models use --image-upload-id or --reference-image-id, not --input-upload-id")

    if args.model in {"doubao-seedream-4.5", "doubao-seedream-5.0-lite"}:
        output_count = args.n or 1
        if len(args.input_upload_id) + output_count > 15:
            raise ValueError("reference image count + output image count must be at most 15")

    if args.model == "MiniMax-H3" and not video_images and not args.reference_video_id and not args.audio_upload_id and not args.reference_audio_id:
        if not args.aspect_ratio or args.aspect_ratio == "adaptive":
            raise ValueError("MiniMax-H3 text-to-video requires an explicit non-adaptive --aspect-ratio")


def apply_model_defaults(args: argparse.Namespace, spec: ModelSpec) -> None:
    has_media = bool(
        args.image_upload_id
        or args.reference_image_id
        or args.reference_video_id
        or args.input_upload_id
        or args.reference_audio_id
    )
    if not args.aspect_ratio and not (spec.omit_default_ratio_with_media and has_media):
        media_ratio = spec.default_ratio_with_media if has_media else None
        args.aspect_ratio = media_ratio or spec.default_ratio
    if not args.resolution and spec.default_resolution:
        args.resolution = spec.default_resolution


def build_payload(args: argparse.Namespace, spec: ModelSpec) -> dict:
    payload = {"model": args.model, "prompt": args.prompt}
    append_if_present(payload, "aspectRatio", args.aspect_ratio)
    append_if_present(payload, "resolution", args.resolution)

    if spec.kind == "images":
        append_if_present(payload, "n", args.n)
        append_if_present(payload, "outputFormat", args.output_format)
        append_if_present(payload, "inputImages", upload_refs(args.input_upload_id))
        if args.gateway_options:
            payload["options"] = args.gateway_options
        return payload

    append_if_present(payload, "duration", args.duration)
    if args.image_upload_id:
        payload["imageUrl"] = upload_ref(args.image_upload_id)
    append_if_present(payload, "referenceImages", upload_refs(args.reference_image_id))
    append_if_present(payload, "referenceVideos", upload_refs(args.reference_video_id))
    if args.audio_upload_id:
        payload["audio"] = upload_ref(args.audio_upload_id)
    if args.reference_audio_id:
        payload["referenceAudios"] = upload_refs(args.reference_audio_id)
    if args.gateway_options:
        payload["options"] = args.gateway_options
    return payload


def prepare_generation(args: argparse.Namespace) -> tuple[ModelSpec, dict]:
    if not args.model:
        raise ValueError("--model is required")
    spec = MODELS.get(args.model)
    if spec is None:
        raise ValueError("unknown model; run --list-models for exact database identifiers")
    if not args.prompt:
        raise ValueError("prompt is required")
    if spec.unavailable_reason:
        raise ValueError(f"Model {args.model} is not available for ordinary generation: {spec.unavailable_reason}")
    apply_model_defaults(args, spec)
    validate_common(args, spec)
    payload = build_payload(args, spec)
    # 图片分支在 build_payload 里提前返回，会话字段统一在这里补，图片和视频都生效。
    payload.update(session_fields(args.new_session, args.session_title))
    return spec, payload


def main() -> None:
    args = parse_args()
    if args.list_models:
        print_json(catalog_rows())
        return
    spec, payload = prepare_generation(args)
    if args.dry_run:
        print_json({"endpoint": f"/api/v1/{spec.kind}/generations", "payload": payload})
        return
    submit(spec.kind, payload, args)


if __name__ == "__main__":
    try:
        main()
    except (GatewayError, ValueError) as exc:
        fail(str(exc))
