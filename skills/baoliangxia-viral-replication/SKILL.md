---
name: baoliangxia-viral-replication
description: Use when the user asks to复刻爆款图片或视频、替换产品素材并生成同款内容 through 爆量匣/baoliangxia Agent Gateway. Covers image replication, partial/full video replication, uploaded source media, task progress and result download; ordinary image/video generation belongs to baoliangxia-skills.
---

# 爆量匣爆款复刻

使用独立的爆款复刻接口或 MCP Tool，按用户提供的源片/源图和产品要求生成复刻结果。保留用户原始要求；只有用户要求优化时才改写。视频任务必须走复刻批任务的反推 → 融合 → 装箱 → 出视频，图片任务走图片复刻链路；不要用普通生图/生视频接口替代。

## 接口状态

截至 2026-10-28，`/api/v1/viral-replications` 和 `create_viral_replication` / `get_viral_replication` 是已提交的设计，服务端尚未实现。当前 skill 可用于离线构造与校验请求（`--dry-run`），不能宣称已经能完成真实复刻。只有目标部署已提供这些接口、用户拥有对应 Key 且端到端验证通过后，才执行真实提交和轮询。若目标返回 404，说明接口尚未部署；告知用户并停止，不改走普通生成接口。

## 首次使用

需要 Python 3 和环境变量 `BAOLIANGXIA_AGENT_GATEWAY_API_KEY`。若用户还没有 Key：到 [爆量匣](https://baoliangxia.com/) 注册或登录 → 左下角头像 → API/CLI → 创建 API Key（默认可调用全部已开放能力）。Key 只从环境变量读取，不写入命令、项目文件、日志或回复。默认服务地址是 `https://baoliangxia.com/`；仅在用户给出其他部署时使用 `BAOLIANGXIA_AGENT_GATEWAY_BASE_URL` 或 `--base-url`。

## 选择路径

| 用户意图 | 接口 | 输入 |
| --- | --- | --- |
| 复刻一张爆款图并替换产品 | `type=image` | 源图、要求、数量、比例、图片模型、文本模型；产品图可选 |
| 按爆款视频复刻产品广告 | `type=video`, `replicationMode=partial` | 源视频、产品描述、套数、视频模型、文本模型；产品图/参考音频可选且受模型限制 |
| 完全复刻视频 | `type=video`, `replicationMode=full` | 同视频输入；只有服务端当前能力、模型、凭证与配额都合格时可提交 |

源素材一律先运行 `scripts/upload_file.py FILE`，取得 `uploadId`。任务创建体只能引用 `{ "uploadId": "..." }`，不能传本地路径、外部 URL、Base64 或 Data URL。复刻模型使用页面可选的准确标识；图片和视频都必须显式提供 `textModel`，不知道模型标识或该模型是否支持复刻时先查目标部署的模型目录/页面配置，不凭普通生成模型表猜测。图片 `count` 为 1～100，视频 `count` 为 1～20；视频每套最多派发 40 个片段，超过时任务会停止继续派发，已发生的上游分析消耗仍按真实用量处理。不要自动拆成多个复刻请求。视频源片是分析素材，不作为最终每段视频的参考视频直接透传。

请求字段、REST/MCP 名称、状态和输出语义见 [接口合约](references/api-contract.md)。

## REST 操作

1. 用上传脚本上传源图/源视频和所需产品图、参考音频，保留每个 `uploadId`。
2. 按接口合约写一个 UTF-8 JSON 请求文件。图片与视频字段严格分开。一次逻辑提交先生成并保存一条 8～128 位幂等键；网络结果不确定时用**原文件和原键**重试。请求内容变化须换新键。
3. 先运行 `scripts/create_viral_replication.py --request-file REQUEST.json --idempotency-key KEY --dry-run` 检查字段和接口目标。目标服务已上线时，去掉 `--dry-run` 提交；返回 `id` 是批任务 ID。
4. 运行 `scripts/query_viral_replication.py BATCH_ID --wait --output-dir OUTPUT_DIR`，`completed|partial|failed|stopped` 为终态。`partial` 需要呈现已成功产物和失败数量。脚本默认每 20 秒查询一次，最多等待 6 小时；这是客户端等待时间，不是服务端任务失败时限。等待超时只报告当前 ID 和状态，不自动补发、换键或创建替代任务。
5. 只在返回结果中有真实积分字段时说明实际消耗；不依据套数、时长、配置价或预扣估算最终消耗。下载 URL 有时效，查询时刷新。对用户呈现文件绝对路径和实际状态，不展示原始 JSON、幂等键、内部批任务细节，除非用户明确要求。

```bash
python {baseDir}/scripts/upload_file.py /path/to/source.mp4
python {baseDir}/scripts/create_viral_replication.py --request-file /path/to/request.json --idempotency-key 8127bf6d-43d0-4c62-9744-27cf48f6d248 --dry-run
python {baseDir}/scripts/query_viral_replication.py BATCH_ID --wait --output-dir /path/to/baoliangxia_results/BATCH_ID
```

Windows 可用 `python` 或 `py -3`。脚本均支持 `--help`。请求文件只保存素材 ID 和用户要求，不存 Key；提交后保留该文件与幂等键以便不确定请求重放。不要把含真实素材或用户内容的请求文件提交到 Git。

## MCP 操作

目标 MCP 服务已上线时，先用 `create_upload_ticket` / `complete_upload` 上传本地素材，再调用 `create_viral_replication`，参数等于 REST 请求体加 `idempotencyKey`。之后用 `get_viral_replication({"batchTaskId":"..."})` 轮询。MCP 和 REST 的 Key、素材归属、幂等、模型与计费规则相同。若 Tool 不在 `tools/list` 中，视为尚未部署并停止。

## 结果呈现

按“复刻状态、已完成张数或成片套数、失败/部分成功数量、文件、可调整方向”的顺序简洁回复。视频片段数和成片套数分别写；不能把片段完成视为成片完成。`partial` 时逐项列出可用文件。没有产物时不写“已生成”。若完全复刻未开放，说明服务端拒绝原因，不静默降级为部分复刻。建议调整只作为下一次请求的选项，用户确认前不重新生成。
