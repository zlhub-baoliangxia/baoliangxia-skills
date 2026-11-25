# Jielan video family

The upstream document names this family `zl-video`, `zl-video-lite`, and `zl-video-mini`. baoliangxia requests must use `jielan-video`, `jielan-video-lite`, or `jielan-video-mini` respectively.

## Script

```bash
python3 {baseDir}/scripts/create_model_generation.py "USER_PROMPT" \
  --model jielan-video [options]
```

## 参数拼装

Omitted `--aspect-ratio` becomes `16:9`. Omitted `--resolution` becomes `720p` for `jielan-video`, `jielan-video-lite`, and `jielan-video-mini`. Explicit flags win.

| Intent | Flag | Rule |
|---|---|---|
| Output seconds | `--duration N` | `jielan-video`: integer `4`–`15` (inclusive). Lite/mini: existing catalog says `1`–`15`, but this range is not independently verified; confirm the deployment limit before submitting durations below 4 seconds |
| Aspect ratio | `--aspect-ratio VALUE` | `9:16`, `16:9`, `3:4`, `4:3`, `1:1` |
| Resolution | `--resolution VALUE` | Standard: `720p`/`1080p`/`2k`/`4k`; lite/mini: `720p`/`1080p` |
| Primary image | `--image-upload-id ID` | General driving image |
| Reference images/videos | repeat matching reference flags | Upload first |
| Reference audio | `--reference-audio-id ID` | One upload; legacy `--audio-upload-id` remains supported |
| Generated audio | `--option generate_audio=true|false` | Defaults to `true`; controls generated sound |
| Watermark | `--watermark true|false` | Defaults to `false` |

```bash
python3 {baseDir}/scripts/create_model_generation.py "生成竖屏商品视频" \
  --model jielan-video-mini --duration 5 --resolution 1080p --aspect-ratio 9:16
```

## 不可用能力

The Gateway exposes `generate_audio` and watermark through the listed options. Return-last-frame, seed, and callback controls remain unavailable. Do not send the upstream `zl-video*` names as baoliangxia model identifiers.

