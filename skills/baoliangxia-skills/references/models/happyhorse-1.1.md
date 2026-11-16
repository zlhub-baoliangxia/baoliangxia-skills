# `happyhorse-1.1`

baoliangxia routes this database model to the appropriate HappyHorse 1.1 text/image/reference-video mode based on supplied media.

## Script

```bash
python3 {baseDir}/scripts/create_model_generation.py "USER_PROMPT" \
  --model happyhorse-1.1 [options]
```

## 参数拼装

Omitted `--resolution` becomes uppercase `720P`. Omitted `--aspect-ratio` becomes `16:9` only for text-only requests. When an image or video is attached, the script leaves ratio unset so the upstream route can infer it. Explicit flags win.

| Intent | Flag | Rule |
|---|---|---|
| Output seconds | `--duration N` | Integer `1`–`15` |
| Aspect ratio | `--aspect-ratio VALUE` | `9:16`, `16:9`, or `1:1`; omit for image-driven modes when the upstream route determines it |
| Resolution | `--resolution VALUE` | Exact uppercase `720P` or `1080P` |
| Primary image | `--image-upload-id ID` | Selects image-driven routing |
| Reference images | repeat `--reference-image-id ID` | Selects reference-image routing |
| Reference videos | repeat `--reference-video-id ID` | Selects video routing |

```bash
python3 {baseDir}/scripts/create_model_generation.py "让人物自然转身" \
  --model happyhorse-1.1 --resolution 720P --image-upload-id upl_first
```

## 不可用能力

The Gateway does not expose the upstream variant name directly, audio settings, output-audio controls, or variant-specific edit parameters. Do not replace `happyhorse-1.1` with `happyhorse-1.1-t2v`/`i2v`/`r2v` in the baoliangxia request.

