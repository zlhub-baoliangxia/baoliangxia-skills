---
name: baoliangxia-viral-replication
description: Use when the user asks to复刻爆款图片或视频、动作复刻、高度复刻、替换产品素材并生成同款内容 through 爆量匣/baoliangxia Agent Gateway. Covers image replication, 动作复刻（replicationMode=partial）and 高度复刻（replicationMode=full）, uploaded source media, task progress and result download; ordinary image/video generation belongs to baoliangxia-skills.
---

# 爆量匣爆款复刻

使用独立的爆款复刻接口或 MCP Tool，按用户提供的源片/源图和产品要求生成复刻结果。保留用户原文；只有用户要求优化时才改写，改写结果直接写入对应文案字段。视频任务必须走复刻批任务的反推 → 融合 → 装箱 → 出视频，图片任务走图片复刻链路；不要用普通生图/生视频接口替代。

## 接口状态

创建、查询和视频拼接接口已在 CanvasMind 项目实现。实际调用前仍需确认目标部署提供对应 REST 路由或 MCP Tool，并且用户拥有对应 Key。若拼接路由与 Tool 都返回 404，说明目标部署尚未提供服务端拼接；按用户意愿使用本地 FFmpeg，或告知用户，不改走普通生成接口。

## 首次使用

需要 Python 3 和环境变量 `BAOLIANGXIA_AGENT_GATEWAY_API_KEY`。若用户还没有 Key：到 [爆量匣](https://baoliangxia.com/) 注册或登录 → 左下角头像 → API/CLI → 创建 API Key（默认可调用全部已开放能力）。Key 只从环境变量读取，不写入命令、项目文件、日志或回复。默认服务地址是 `https://baoliangxia.com/`；仅在用户给出其他部署时使用 `BAOLIANGXIA_AGENT_GATEWAY_BASE_URL` 或 `--base-url`。

## 选择路径

| 用户意图 | 接口 | 输入 |
| --- | --- | --- |
| 复刻一张爆款图并替换产品 | `type=image` | 源图、`requirement`、数量、比例、图片模型、文本模型；产品图可选 |
| 动作复刻视频 | `type=video`，省略 `replicationMode` 或 `partial` | 源视频、`productDescription`、套数、视频模型、文本模型；产品图/参考音频可选且受模型限制 |
| 高度复刻视频 | `type=video`，`replicationMode=full` | 与动作复刻相同的字段；模型必须在下方白名单内，否则服务端拒绝 |

视频文案只放在 `productDescription`。这是融合使用的最终文字：用户没要求改写时原样写入；用户要求优化时，先得到确认后的文案再写入。不要另传优化前原文、大纲或 `promptOptimization`。

不要传 `strategies`、`sourceVideoMetadata`，也不要传时长、宽高。源片时长和尺寸由服务端探测上传文件。这些字段以及任何未知字段都会被拒绝。

高度复刻只对这些视频模型提交：`doubao-seedance-2.0`、`doubao-seedance-2.0-fast`、`doubao-seedance-2.0-mini`、`doubao-seedance-2.5`、`MiniMax-H3`、`wan3.0-video`、`vidu-short-ads`。`vidu-q4-preview`（API modelKey：`viduq4-preview`）不支持高度复刻；可灵、HappyHorse、Vidu Q3，以及剧集带货里除 `vidu-short-ads` 以外的标识，也不能做高度复刻。用户指定了不支持的模型时说明原因，不改成动作复刻，也不换模型，除非用户确认。

### 默认模型与可选项

用户未指定模型时，在创建请求体前补入下列默认值。Gateway 的请求校验要求模型字段存在，不会替调用方填默认值：

- 图片复刻与视频复刻的文本模型：`doubao-seed-2.1-pro`。
- 图片模型：`doubao-seedream-4.5`。
- 视频模型：`doubao-seedance-2.0`。

当前图片和视频复刻的文本模型仅支持 `doubao-seed-2.1-pro`。用户指定其他文本模型时，说明暂不支持并停止提交；不要静默替换成默认模型。

模型值使用下表“API modelKey”中的准确标识。若目标模型目录中同一裸 modelKey 有多个匹配项，使用该条目的 `selectionKey` 唯一指定；不要把界面展示名直接当成 API modelKey。

当前模型目录中可用于图片复刻的模型：

| 界面名称 | API `imageModel` 值 |
| --- | --- |
| `doubao-seedream-4.5`（默认） | `doubao-seedream-4.5` |
| `doubao-seedream-5.0-lite` | `doubao-seedream-5.0-lite` |
| `doubao-seedream-5.0-pro` | `doubao-seedream-5.0-pro` |
| `zl-ooe-3.1-flash-image` | `zl-ooe-3.1-flash-image-t` |
| `zl-pep-image-2` | `zl-pep-image-2-async` |
| `zl-pep-image-2.5-sunburst-async` | `zl-pep-image-2.5-sunburst-async` |
| `zl-pep-image-2.5-flare-async` | `zl-pep-image-2.5-flare-async` |

图片画面比例统一可选 `1:1`、`4:3`、`3:4`、`9:16`、`16:9`，不按图片模型区分。API 要求 `ratio`；用户未指定时使用界面默认 `1:1`。图片 `resolution` 可省略，让所选模型配置采用自己的默认档位。

当前模型目录中可用于视频复刻的模型及分辨率：

| 界面名称 | API `videoModel` 值 | 可选 `resolution` |
| --- | --- | --- |
| `doubao-seedance-2.5` | `doubao-seedance-2.5` | `480p`、`720p`、`1080p` |
| `MiniMax-H3` | `MiniMax-H3` | `768P`、`2K` |
| `wan3.0-video` | `wan3.0-video` | `480P`、`720P`、`1080P` |
| `wan3.0-video-prime` | `wan3.0-video-prime` | `480P`、`720P`、`1080P` |
| `doubao-seedance-2.0`（默认） | `doubao-seedance-2.0` | `480p`、`720p`、`1080p` |
| `doubao-seedance-2.0-fast` | `doubao-seedance-2.0-fast` | `480p`、`720p` |
| `doubao-seedance-2.0-mini` | `doubao-seedance-2.0-mini` | `480p`、`720p` |
| `vidu-q4-preview` | `viduq4-preview` | `540p`、`720p`、`1080p`、`2K`、`4K` |
| `vidu-short-ads` | `vidu-short_drama_ads_fast` | `720p` |

视频 `resolution` 未指定时省略，由所选模型配置应用自己的默认档位。可选模型与分辨率来自当前爆款复刻模型目录；目录可能随部署配置变化，提交前以目标部署的模型目录为准。

图片文案放在 `requirement`。默认不要传 `promptOptimization`，服务端会按该要求自己优化。只有用户已经确认一份优化稿、并且明确不要服务端再改写时，才附带 `promptOptimization`：`optimizedDescription` 用确认稿，`originalDescription` 用优化前原文，`traceId` 仅在已有那次优化记录时填写。

`industry` 可选，只使用 `ecommerce`、`beauty`、`telecom`、`netservice`。没有对应行业就省略。

源素材一律先运行 `scripts/upload_file.py FILE`，取得 `uploadId`。任务创建体只能引用 `{ "uploadId": "..." }`，不能传本地路径、外部 URL、Base64 或 Data URL。图片和视频都必须提供 `textModel`；用户未指定时补默认值。需要确认 modelKey、selectionKey 或复刻可用性时查目标部署模型目录，不凭普通生图/生视频模型目录猜测。图片 `count` 为 1～100，视频 `count` 为 1～20；视频每套最多派发 40 个片段，超过时任务会停止继续派发，已发生的上游分析消耗仍按真实用量处理。不要自动拆成多个复刻请求。视频源片是分析素材，不作为最终每段视频的参考视频直接透传。

请求字段、REST/MCP 名称、状态和输出语义见 [接口合约](references/api-contract.md)。

## REST 操作

1. 用上传脚本上传源图/源视频和所需产品图、参考音频，保留每个 `uploadId`。
2. 按接口合约写一个 UTF-8 JSON 请求文件。图片与视频字段严格分开。一次逻辑提交先生成并保存一条 8～128 位幂等键；网络结果不确定时用**原文件和原键**重试。请求内容变化须换新键。
3. 先运行 `scripts/create_viral_replication.py --request-file REQUEST.json --idempotency-key KEY --dry-run` 检查字段和接口目标。目标服务已上线时，去掉 `--dry-run` 提交；返回 `id` 是批任务 ID。
4. 运行 `scripts/query_viral_replication.py BATCH_ID --wait --output-dir OUTPUT_DIR`，`completed|partial|failed|stopped` 是片段任务的终态；`completed` **不代表拼接完成**。脚本默认每 20 秒查询一次，最多等待 6 小时；这是客户端等待时间，不是服务端任务失败时限。等待超时只报告当前 ID 和状态，不自动补发、换键或创建替代任务。
5. 视频任务到终态后，按 `groupIndex` 汇总片段，并确认目标套的片段都已进入终态，再逐套调用 `scripts/merge_viral_replication.py BATCH_ID --group-index N`。服务端拼接调用会等待，成功返回后重新查询原批任务，直到 `outputs` 中出现对应 `role=merged`。若服务端返回片段尚未结束，继续查询原批任务后再调用；不要创建新的复刻任务。
6. 如果用户不想等待服务端拼接，或拼接超时/失败后查询仍拿不到 `role=merged`，可用已下载的片段在本地用 FFmpeg 按 `segIndex` 升序拼接。`query_viral_replication.py --output-dir` 输出里的 `outputs` 保留每项的 `role/groupIndex/segIndex`，`downloaded` 列表按有下载 URL 的输出顺序对应；只挑目标套的 `role=segment` 文件。先检查该套片段是否齐全；若有失败片段，只能生成部分成片并向用户说明缺段。不要把片段列表当作最终成片。
7. 只在返回结果中有真实积分字段时说明实际消耗；不依据套数、时长、配置价或预扣估算最终消耗。下载 URL 有时效，查询时刷新。对用户呈现文件绝对路径和实际状态，不展示原始 JSON、幂等键、内部批任务细节，除非用户明确要求。

本地 FFmpeg concat demuxer 示例（输入清单按 `segIndex` 排序，路径改为本地绝对路径）：

```text
file 'D:/path/to/segment-01.mp4'
file 'D:/path/to/segment-02.mp4'
```

```bash
ffmpeg -f concat -safe 0 -i merge-list.txt -c copy merged.mp4
```

若片段编码参数不兼容导致 stream copy 失败，可转码后拼接：

```bash
ffmpeg -f concat -safe 0 -i merge-list.txt -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k -movflags +faststart merged.mp4
```

```bash
python {baseDir}/scripts/upload_file.py /path/to/source.mp4
python {baseDir}/scripts/create_viral_replication.py --request-file /path/to/request.json --idempotency-key 8127bf6d-43d0-4c62-9744-27cf48f6d248 --dry-run
python {baseDir}/scripts/query_viral_replication.py BATCH_ID --wait --output-dir /path/to/baoliangxia_results/BATCH_ID
python {baseDir}/scripts/merge_viral_replication.py BATCH_ID --group-index N
```

Windows 可用 `python` 或 `py -3`。脚本均支持 `--help`。请求文件只保存素材 ID 和用户要求，不存 Key；提交后保留该文件与幂等键以便不确定请求重放。不要把含真实素材或用户内容的请求文件提交到 Git。

## MCP 操作

目标 MCP 服务已上线时，先用 `create_upload_ticket` / `complete_upload` 上传本地素材，再调用 `create_viral_replication`，参数等于 REST 请求体加 `idempotencyKey`。之后用 `get_viral_replication({"id":"..."})` 轮询，`id` 是创建接口返回的批任务 id；视频任务到终态后，对每个片段组调用 `merge_viral_replication({"id":"...","groupIndex":N})`，该调用会等待服务端拼接；成功后再次调用 `get_viral_replication` 取得 `role=merged` 的结果。结果超过一页时把 `nextCursor` 作为 `cursor` 继续查。若用户不想等或服务端没返回成片，按 REST 操作第 6 步本地 FFmpeg 拼接。MCP 和 REST 的 Key、素材归属、幂等、模型与计费规则相同。若所需 Tool 不在 `tools/list` 中，按 REST 尝试；REST 也不可用时说明目标部署尚未提供拼接能力。

## 结果呈现

按“复刻状态、已完成张数或成片套数、失败/部分成功数量、文件、可调整方向”的顺序简洁回复。视频片段数和成片套数分别写；不能把片段完成视为成片完成。`partial` 时逐项列出可用文件。没有产物时不写“已生成”。若高度复刻未开放，说明服务端拒绝原因，不静默降级为动作复刻。建议调整只作为下一次请求的选项，用户确认前不重新生成。
