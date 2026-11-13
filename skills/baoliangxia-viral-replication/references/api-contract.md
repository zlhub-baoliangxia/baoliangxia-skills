# 爆款复刻网关接口合约

与 CanvasMind Agent Gateway 的爆款复刻创建/查询实现对应。实际调用前确认目标部署有该 REST 路由或 MCP Tool；目标返回 404 时停止，不改走普通生成接口。

## REST 与 MCP

| 动作 | REST | MCP |
| --- | --- | --- |
| 创建 | `POST /api/v1/viral-replications`，`Idempotency-Key` 请求头 | `create_viral_replication`，`idempotencyKey` 参数 |
| 查询 | `GET /api/v1/viral-replications/:id`，可带 `cursor` | `get_viral_replication`，`id`、可选 `cursor` |
| 拼接 | `POST /api/v1/viral-replications/:id/merge/:groupIndex` | `merge_viral_replication`，`id`、`groupIndex` |

有效且启用的 Bearer Key 默认可调用全部已开放的 Gateway 能力，无需选择或校验 Scope。图片/视频创建分别使用 `viral_image_replication` / `viral_video_replication` 操作做幂等。同一用户、操作、幂等键和请求体只生成一次父批任务；相同键而请求体不同返回 409。已绑定的同键重放直接返回原任务 ID，不因之后模型配置或素材状态变化而重新提交。10 分钟有效期只约束待完成上传票据；已完成的 `uploadId` 没有独立到期时间，若对象存储已不可用，新请求仍会被拒绝。

## 图片请求

```json
{
  "type": "image",
  "sourceImage": { "uploadId": "upl_source" },
  "productImages": [{ "uploadId": "upl_product" }],
  "requirement": "保留构图，替换成我的产品",
  "count": 2,
  "ratio": "1:1",
  "imageModel": "doubao-seedream-4.5",
  "textModel": "doubao-seed-2.1-pro"
}
```

必填：`type/sourceImage/requirement/count/ratio/imageModel/textModel`。skill 在用户未指定时补 `imageModel=doubao-seedream-4.5`、`textModel=doubao-seed-2.1-pro`；图片复刻暂时只支持文本模型 `doubao-seed-2.1-pro`，用户指定其他文本模型时停止提交，不静默替换。未指定比例时使用 `1:1`。图片比例可选值为 `1:1`、`4:3`、`3:4`、`9:16`、`16:9`。可选：`productImages`、`industry`、`resolution`、`promptOptimization`。`resolution` 未指定时省略，使用模型配置的默认档位。`requirement` 是用户给出的生成要求。默认不传 `promptOptimization`，由服务端按 `requirement` 优化。只有调用方已经确认优化稿、且不要服务端再改写时才传：`{ "originalDescription": "...", "optimizedDescription": "...", "traceId": "..." }`，前两项必填且非空，`traceId` 可选。`count` 为 1～100 的整数。`industry` 只接受 `ecommerce`、`beauty`、`telecom`、`netservice`，没有对应值就省略。图片和文本模型标识必须能从当前公开目录唯一解析；可传 `modelKey` 或准确 `selectionKey`。缺少文本模型会使图片执行器跳过参考图分析，因此请求中必须显式提供；由 skill 补默认值，不是 Gateway 自动默认。

## 视频请求

```json
{
  "type": "video",
  "sourceVideo": { "uploadId": "upl_source" },
  "productImages": [{ "uploadId": "upl_product" }],
  "productDescription": "产品卖点与复刻要求",
  "count": 1,
  "videoModel": "doubao-seedance-2.0",
  "textModel": "doubao-seed-2.1-pro",
  "replicationMode": "partial"
}
```

必填：`type/sourceVideo/productDescription/count/videoModel/textModel`。skill 在用户未指定时补 `videoModel=doubao-seedance-2.0`、`textModel=doubao-seed-2.1-pro`；视频复刻暂时只支持文本模型 `doubao-seed-2.1-pro`，用户指定其他文本模型时停止提交，不静默替换。可选：`productImages`、`referenceAudios`（最多 3 条）、`industry`、`resolution`、`ratio`、`replicationMode`（`partial` 动作复刻 | `full` 高度复刻）。`resolution` 与 `ratio` 同为可选项。`resolution` 未指定时省略，使用模型配置的默认档位。`ratio` 未指定时同样省略：服务端按已上传源片的真实宽高映射到该模型 `ratioOptions`，读不到宽高时用该列表第一项。只接受该模型当前列出的具体比例，不接受 `adaptive`。取值不在列表内时返回 HTTP 400，消息为 `当前模型不支持该比例`，发生在预扣之前，不会创建任务。同一次批任务的所有片段使用同一个比例。未保存比例的老任务行为完全不变。高度复刻（`replicationMode=full`）选了与源片不同的比例时，不转码深度片，直接作为参考视频提交，运镜对齐可能下降。`productDescription` 是融合使用的最终文案，不要再传优化前原文或大纲。`count` 为 1～20 的整数，省略 `replicationMode` 使用 `partial`。`industry` 与图片相同，只接受 `ecommerce`、`beauty`、`telecom`、`netservice`。源片时长和宽高由服务端探测上传文件。`strategies`、`promptOptimization`、`sourceVideoMetadata` 以及任何未知字段都会被拒绝。高度复刻只允许 skill 主文档所列白名单中的 7 个模型；`viduq4-preview`（界面名称 `vidu-q4-preview`）不支持高度复刻。Gateway 每套视频最多派发 40 个片段，超限不会继续派发；已发生的反推消耗仍按真实用量处理。

当前公开目录的视频模型分辨率：`doubao-seedance-2.5` 为 `480p/720p/1080p`；`MiniMax-H3` 为 `768P/2K`；`wan3.0-video` 与 `wan3.0-video-prime` 为 `480P/720P/1080P`；`doubao-seedance-2.0` 为 `480p/720p/1080p`；`doubao-seedance-2.0-fast` 与 `doubao-seedance-2.0-mini` 为 `480p/720p`；`viduq4-preview` 为 `540p/720p/1080p/2K/4K`；`vidu-short_drama_ads_fast` 为 `720p`。对应比例（不含 `adaptive`）：`doubao-seedance-2.5`、`doubao-seedance-2.0`、`doubao-seedance-2.0-fast` 与 `doubao-seedance-2.0-mini` 为 `9:16/16:9/3:4/4:3/1:1`；`MiniMax-H3` 为 `9:16/16:9/4:3/3:4/1:1/21:9`；`wan3.0-video` 与 `wan3.0-video-prime` 为 `9:16/16:9/4:3/3:4/1:1`；`viduq4-preview` 为 `16:9/9:16/1:1/3:4/4:3`；`vidu-short_drama_ads_fast` 为 `16:9/9:16/3:4/4:3`。目录没有 `ratioOptions` 时回退 `16:9/9:16/4:3/3:4/1:1`。目录配置会变化，提交前以目标部署返回的模型目录为准，且不得传 `adaptive`。

## 响应与状态

创建成功为 HTTP 202：`{ "id":"<batchTaskId>", "object":"viral_replication", "type":"image|video", "status":"pending", "createdAt":"<ISO>", "requestId":"req_xxx" }`。重放返回原 ID，REST 另带 `Idempotency-Replayed: true`。

查询响应包含 `id/object/type/status/createdAt/updatedAt/progress/outputs/error`。状态 `pending|running|completed|partial|failed|stopped`，后四项为终态。`progress` 图片给 `targetCount/completedCount/failedCount`；视频另给 `setsTotal/setsCompleted` 与 `segmentsTotal/segmentsCompleted/segmentsFailed`。`setsCompleted` 只计已转存并持久化的合并成片；片段完成但尚未合并时不增加。`outputs` 只含已转存到对象存储的媒体，带临时下载 `url`。视频输出应标明成片或片段及 `groupIndex`；图片带槽位序号。最多 100 项，更多时返回 `nextCursor`，用 `?cursor=...` 读取后续页。不存在、跨用户或非 Gateway 复刻任务统一 404。

拼接接口只允许当前用户通过 Agent Gateway 创建的视频复刻任务。只有目标套全部片段进入终态（成功、失败或停止）后才允许拼接；有产物的成功片段按 `segIndex` 升序合成，失败片段会被跳过。接口同步等待并持久化结果，返回 `id/groupIndex/status/cached`；成功后再次查询批任务以取得临时下载 URL 和 `role=merged`。请求超时后先查询原任务确认是否已保存成片；仍无结果时可以本地用 FFmpeg 拼接下载的片段。重复调用已成功拼接的套会返回缓存状态，不会重新生成片段。

错误体沿用 Gateway：`{ "error": { "code": "...", "message": "...", "requestId": "req_xxx", "retryable": false } }`。遇到 429 按 `retryAfterSeconds` 等待；网络不确定时只重放原幂等键和原请求。404 新路由或缺少新 MCP Tool 表示部署未就绪，停止。

30 秒是服务端幂等 claim 的短租约，不是生成时限。图片沿用现有 2 小时传输空闲窗口，超时后的状态按既有图片执行/恢复规则处理；视频沿用 6 小时单轮轮询窗口，窗口到期仍未确认上游终态时保留可恢复状态。图片单批并发取模型能力与服务端配置的较小值，最高 10；视频按批次限制上游提交速率，当前默认每秒 5 次，提交速率不是同时在途数上限。本期没有每用户、每 Key 或全局在途任务硬上限。脚本 `query_viral_replication.py --wait` 默认等待 6 小时，超时后任务仍可凭原 ID 查询。
