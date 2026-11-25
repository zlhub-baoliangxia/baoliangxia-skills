# Vidu Q3 reference models

Use this reference for `viduq3-ad` and `viduq3-mix`.

## Script

```bash
python3 {baseDir}/scripts/create_model_generation.py "USER_PROMPT" \
  --model viduq3-mix [options]
```

## 参数拼装

Omitted `--aspect-ratio` becomes `16:9`. Omitted `--resolution` becomes `1080p` for both `viduq3-ad` and `viduq3-mix`, matching the documented size default. Explicit flags win.

| Intent | Flag | Rule |
|---|---|---|
| Duration | `--duration N` | `1`–`16` seconds with 0–2 images; `3`–`16` seconds with 3–7 images (primary and reference images combined) |
| Aspect ratio | `--aspect-ratio VALUE` | `9:16`, `16:9`, `3:4`, `4:3`, or `1:1` |
| Resolution | `--resolution VALUE` | Ad: `720p`/`1080p`; Mix: `540p`/`720p`/`1080p` |
| Product/reference images | primary image plus repeated reference-image flags | Combined maximum 7; order is preserved |

```bash
python3 {baseDir}/scripts/create_model_generation.py "保持商品外观，生成电商广告" \
  --model viduq3-ad --duration 8 --resolution 1080p --aspect-ratio 9:16 \
  --reference-image-id upl_product
```

## 不可用能力

These database models do not expose reference-video input through the Gateway route. Provider callback, negative prompt, and raw Vidu task suffixes such as `_reference2video` are unavailable; the server adapter chooses the upstream route.
