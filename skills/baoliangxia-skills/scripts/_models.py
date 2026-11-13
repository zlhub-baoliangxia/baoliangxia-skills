#!/usr/bin/env python3
"""Static baoliangxia media-model catalog used by the skill scripts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    kind: str
    reference: str
    ratios: tuple[str, ...] = ()
    resolutions: tuple[str, ...] = ()
    duration_min: int | None = None
    duration_max: int | None = None
    duration_values: tuple[int, ...] = ()
    duration_required: bool = False
    allow_adaptive_duration: bool = False
    max_outputs: int | None = None
    output_formats: tuple[str, ...] = ()
    max_input_images: int | None = None
    max_reference_images: int | None = None
    max_reference_videos: int | None = None
    max_reference_audios: int | None = None
    gateway_options: dict[str, tuple[str, ...] | None] | None = None
    gateway_option_defaults: dict[str, str | bool] | None = None
    allow_audio: bool = False
    unavailable_reason: str | None = None
    # Applied only when the caller omits the flag. A value stated in the model
    # document wins. Otherwise the ratio is 16:9, and the resolution is the
    # supported tier nearest 720p, spelled exactly as that model requires.
    default_ratio: str | None = None
    default_resolution: str | None = None
    # Used instead of default_ratio when an image or video is attached.
    default_ratio_with_media: str | None = None
    # Some image-driven routes cannot accept a ratio. Leave it unset then.
    omit_default_ratio_with_media: bool = False


IMAGE_RATIOS = ("9:16", "16:9", "3:4", "4:3", "1:1", "21:9", "3:2", "2:3")
IMAGE_2_RATIOS = IMAGE_RATIOS + ("5:4", "4:5", "9:21", "2:1", "1:2", "1:3", "3:1")
VIDEO_RATIOS = ("9:16", "16:9", "3:4", "4:3", "1:1")
WAN_RATIOS = ("adaptive", "9:16", "16:9", "4:3", "3:4", "1:1")


MODELS: dict[str, ModelSpec] = {
    "doubao-seedream-4.5": ModelSpec(
        "images", "references/models/doubao-seedream-4.5.md",
        ratios=IMAGE_RATIOS, resolutions=("2K", "4K"), max_outputs=15, max_input_images=14,
        default_ratio="1:1", default_resolution="2K",
        gateway_options={"watermark": None}, gateway_option_defaults={"watermark": False},
    ),
    "doubao-seedream-5.0-lite": ModelSpec(
        "images", "references/models/doubao-seedream-5.0-lite.md",
        ratios=IMAGE_RATIOS, resolutions=("2K", "3K", "4K"), max_outputs=15,
        output_formats=("png", "jpeg"), max_input_images=14,
        default_ratio="1:1", default_resolution="2K",
        gateway_options={"watermark": None}, gateway_option_defaults={"watermark": False},
    ),
    "doubao-seedream-5.0-pro": ModelSpec(
        "images", "references/models/doubao-seedream-5.0-pro.md",
        ratios=IMAGE_RATIOS, resolutions=("1K", "2K"), output_formats=("png", "jpeg"),
        max_input_images=10, default_ratio="1:1", default_resolution="2K",
        gateway_options={"watermark": None}, gateway_option_defaults={"watermark": False},
    ),
    "zl-pep-image-2-async": ModelSpec(
        "images", "references/models/zl-pep-image-2.md",
        ratios=IMAGE_2_RATIOS, resolutions=("1K", "2K", "4K"), max_outputs=10,
        max_input_images=3, default_ratio="16:9", default_resolution="1K",
        gateway_options={"quality": ("auto", "low", "medium", "high"), "background": ("auto", "opaque")},
        gateway_option_defaults={"quality": "auto", "background": "auto"},
    ),
    "zl-pep-image-2.5-flare-async": ModelSpec(
        "images", "references/models/zl-pep-image-2.md",
        ratios=IMAGE_2_RATIOS, resolutions=("1K", "2K", "4K"),
        max_input_images=3, default_ratio="16:9", default_resolution="1K",
        gateway_options={"quality": ("auto", "low", "medium", "high"), "background": ("auto", "opaque")},
        gateway_option_defaults={"quality": "auto", "background": "auto"},
    ),
    "zl-pep-image-2.5-sunburst-async": ModelSpec(
        "images", "references/models/zl-pep-image-2.md",
        ratios=IMAGE_2_RATIOS, resolutions=("1K", "2K", "4K"),
        max_input_images=3, default_ratio="16:9", default_resolution="1K",
        gateway_options={"quality": ("auto", "low", "medium", "high"), "background": ("auto", "opaque")},
        gateway_option_defaults={"quality": "auto", "background": "auto"},
    ),
    "zl-ooe-3.1-flash-image-t": ModelSpec(
        "images", "references/models/zl-ooe-3.1-flash-image.md",
        ratios=("1:1", "3:4", "4:3", "16:9", "9:16", "21:9", "3:2", "2:3", "5:4", "4:5"),
        max_input_images=3, default_ratio="16:9",
        gateway_options={"imageSize": ("1K", "2K", "4K")}, gateway_option_defaults={"imageSize": "2K"},
    ),
    "doubao-seedance-2.0": ModelSpec(
        "videos", "references/models/doubao-seedance-2.0.md",
        ratios=VIDEO_RATIOS, resolutions=("480p", "720p", "1080p"), duration_min=1,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=1,
        gateway_options={"generate_audio": None, "watermark": None},
        gateway_option_defaults={"generate_audio": True, "watermark": False},
        default_ratio="16:9", default_resolution="720p",
    ),
    "doubao-seedance-2.0-fast": ModelSpec(
        "videos", "references/models/doubao-seedance-2.0.md",
        ratios=VIDEO_RATIOS, resolutions=("480p", "720p"), duration_min=1,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=1,
        gateway_options={"generate_audio": None, "watermark": None},
        gateway_option_defaults={"generate_audio": True, "watermark": False},
        default_ratio="16:9", default_resolution="720p",
    ),
    "doubao-seedance-2.0-mini": ModelSpec(
        "videos", "references/models/doubao-seedance-2.0.md",
        ratios=VIDEO_RATIOS, resolutions=("480p", "720p"), duration_min=1,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=1,
        gateway_options={"generate_audio": None, "watermark": None},
        gateway_option_defaults={"generate_audio": True, "watermark": False},
        default_ratio="16:9", default_resolution="720p",
    ),
    "doubao-seedance-2.5": ModelSpec(
        "videos", "references/models/doubao-seedance-2.5.md",
        ratios=VIDEO_RATIOS + ("adaptive",), resolutions=("480p", "720p", "1080p"),
        duration_min=4, duration_max=30, allow_adaptive_duration=True,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=10,
        gateway_options={"generate_audio": None, "omni_reference_task_type": ("reference", "edit", "extend"), "watermark": None},
        gateway_option_defaults={"generate_audio": True, "watermark": False},
        default_ratio="adaptive", default_resolution="720p",
    ),
    "happyhorse-1.1": ModelSpec(
        "videos", "references/models/happyhorse-1.1.md",
        ratios=("9:16", "16:9", "1:1"), resolutions=("720P", "1080P"),
        duration_min=1, max_reference_images=20, max_reference_videos=20,
        default_ratio="16:9", default_resolution="720P", omit_default_ratio_with_media=True,
    ),
    "jielan-video": ModelSpec(
        "videos", "references/models/jielan-video.md",
        ratios=VIDEO_RATIOS, resolutions=("720p", "1080p", "2k", "4k"), duration_min=1,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=1,
        gateway_options={"generate_audio": None, "watermark": None},
        gateway_option_defaults={"generate_audio": True, "watermark": False},
        default_ratio="16:9", default_resolution="720p",
    ),
    "jielan-video-lite": ModelSpec(
        "videos", "references/models/jielan-video.md",
        ratios=VIDEO_RATIOS, resolutions=("720p", "1080p"), duration_min=1,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=1,
        gateway_options={"generate_audio": None, "watermark": None},
        gateway_option_defaults={"generate_audio": True, "watermark": False},
        default_ratio="16:9", default_resolution="720p",
    ),
    "jielan-video-mini": ModelSpec(
        "videos", "references/models/jielan-video.md",
        ratios=VIDEO_RATIOS, resolutions=("720p", "1080p"), duration_min=1,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=1,
        gateway_options={"generate_audio": None, "watermark": None},
        gateway_option_defaults={"generate_audio": True, "watermark": False},
        default_ratio="16:9", default_resolution="720p",
    ),
    "kling-v3-omni": ModelSpec(
        "videos", "references/models/kling-v3-omni.md",
        ratios=("9:16", "16:9", "1:1"), duration_min=3, duration_max=15,
        max_reference_images=7, max_reference_videos=7, default_ratio="16:9",
        gateway_options={"mode": ("std", "pro", "4k"), "sound": ("on", "off"), "watermark": None},
        gateway_option_defaults={"mode": "pro", "sound": "off", "watermark": False},
    ),
    "MiniMax-H3": ModelSpec(
        "videos", "references/models/minimax-h3.md",
        ratios=("adaptive", "9:16", "16:9", "4:3", "3:4", "1:1", "21:9"),
        resolutions=("768P", "2K"), duration_min=4, duration_max=15, duration_required=True,
        max_reference_images=30, max_reference_videos=10, allow_audio=True,
        max_reference_audios=3,
        gateway_options={"watermark": None}, gateway_option_defaults={"watermark": False},
        default_ratio="16:9", default_resolution="768P", default_ratio_with_media="adaptive",
    ),
    "video-sr": ModelSpec(
        "videos", "references/models/video-sr.md", resolutions=("720p", "1080p", "2k", "4k"),
        max_reference_videos=1, default_resolution="720p",
        unavailable_reason=(
            "video-sr 仅用于视频提升画质，不能用于普通视频生成；请改用 scripts/create_video_super_resolution.py"
        ),
    ),
    "vidu": ModelSpec(
        "videos", "references/models/vidu-solutions.md", max_reference_videos=1,
    ),
    "vidu-short_drama_ads_fast": ModelSpec(
        "videos", "references/models/vidu-short-ads.md",
        ratios=("16:9", "9:16", "3:4", "4:3"), resolutions=("720p",),
        duration_values=tuple(range(4, 16)) + (20, 25, 30), max_reference_images=20,
        max_reference_videos=1, default_ratio="16:9", default_resolution="720p",
    ),
    "viduq2-pro": ModelSpec(
        "videos", "references/models/vidu-solutions.md",
        resolutions=("540p", "720p", "1080p"), max_reference_images=1,
        default_resolution="720p",
    ),
    "viduq2-turbo": ModelSpec(
        "videos", "references/models/vidu-solutions.md",
        resolutions=("540p", "720p", "1080p"), max_reference_images=1,
        default_resolution="720p",
    ),
    "viduq3-ad": ModelSpec(
        "videos", "references/models/vidu-q3.md", ratios=VIDEO_RATIOS,
        resolutions=("720p", "1080p"), duration_min=1, duration_max=16,
        max_reference_images=7, default_ratio="16:9", default_resolution="1080p",
    ),
    "viduq3-mix": ModelSpec(
        "videos", "references/models/vidu-q3.md", ratios=VIDEO_RATIOS,
        resolutions=("540p", "720p", "1080p"), duration_min=1, duration_max=16,
        max_reference_images=7, default_ratio="16:9", default_resolution="1080p",
    ),
    "wan3.0-video": ModelSpec(
        "videos", "references/models/wan3.0-video.md", ratios=WAN_RATIOS,
        resolutions=("480P", "720P", "1080P"), duration_min=2, duration_max=30,
        allow_adaptive_duration=True, max_reference_images=10, max_reference_videos=5,
        allow_audio=True, default_ratio="adaptive", default_resolution="1080P",
        max_reference_audios=5, gateway_options={"audio": None, "watermark": None},
        gateway_option_defaults={"audio": True, "watermark": False},
    ),
    "wan3.0-video-prime": ModelSpec(
        "videos", "references/models/wan3.0-video.md", ratios=WAN_RATIOS,
        resolutions=("480P", "720P", "1080P"), duration_min=2, duration_max=30,
        allow_adaptive_duration=True, max_reference_images=10, max_reference_videos=5,
        allow_audio=True, default_ratio="adaptive", default_resolution="1080P",
        max_reference_audios=5, gateway_options={"audio": None, "watermark": None},
        gateway_option_defaults={"audio": True, "watermark": False},
    ),
}


def catalog_rows() -> list[dict[str, object]]:
    return [
        {
            "model": model,
            "kind": spec.kind,
            "reference": spec.reference,
            "available": spec.unavailable_reason is None,
            "availabilityNote": spec.unavailable_reason,
            "defaultAspectRatio": spec.default_ratio,
            "defaultResolution": spec.default_resolution,
            "supportsOutputCount": spec.max_outputs is not None,
            "maxOutputsPerRequest": spec.max_outputs or 1,
            "supportsReferenceAudio": spec.max_reference_audios is not None,
            "maxReferenceAudios": spec.max_reference_audios or 0,
            "gatewayOptions": {
                key: {"type": "boolean" if choices is None else "enum",
                      "choices": list(choices or ()),
                      "default": (spec.gateway_option_defaults or {}).get(key)}
                for key, choices in (spec.gateway_options or {}).items()
            },
            "batchStrategy": "count_then_top_up" if spec.max_outputs else "parallel_single",
        }
        for model, spec in MODELS.items()
    ]
