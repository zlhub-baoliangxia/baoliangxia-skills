# `video-sr`

`video-sr` 只用于视频提升画质，不是普通视频生成模型。它走独立接口 `POST /api/v1/videos/super-resolutions`；不能用于文生视频、图生视频或参考视频生成。

## Script

```bash
python3 {baseDir}/scripts/create_video_super_resolution.py \
  --generation-id GENERATION_ID --target-resolution 1080p
```

也可以重复 `--upload-id` 或 `--file`。合计 1～10 条。`--plan-key` 缺省 `general`。目标档位只接受 `720p`、`1080p`、`2k`、`4k`，且必须高于源视频；脚本不探测文件。查询用 `scripts/query_generation.py`。

2 条及以上时，退出码与 `create_batch_generations.py` 一致：0 表示全部完成且全部下载到本地；2 表示部分完成、仍在处理、未完成或有下载失败。屏幕输出的每条任务带 `error` / `queryError` / `downloadError`（有才出现），并给出 `remainingCount`。

## 参数拼装

| Intent | Flag | Rule |
|---|---|---|
| 已完成的视频生成记录 | `--generation-id ID` | 与上传、本地文件按条二选一 |
| 已完成上传 | `--upload-id ID` | 上传流程得到的视频 uploadId |
| 本地视频 | `--file PATH` | 先走既有上传，再提交 uploadId |
| 目标清晰度 | `--target-resolution VALUE` | 必填：`720p` / `1080p` / `2k` / `4k` |
| 画质方案 | `--plan-key VALUE` | 缺省 `general` |
| 新会话 | `--new-session` / `--session-title` | 多条时只放在第一条 |

## 不可用能力

`scripts/create_model_generation.py` 会拒绝 `video-sr`，这是预期行为：`video-sr` 仅用于提升已有视频的清晰度。不要把它用于普通视频生成，也不要用 `referenceVideos` 代替超分来源。
