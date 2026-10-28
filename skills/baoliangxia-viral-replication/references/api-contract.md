# 爆款复刻网关接口合约（待部署）

与 CanvasMind `docs/superpowers/specs/2026-10-28-agent-gateway-viral-replication-design.md` 对应。新接口截至 2026-10-28 尚未实现；服务端上线前仅可做本地请求校验。

## REST 与 MCP

| 动作 | REST | MCP |
| --- | --- | --- |
| 创建 | `POST /api/v1/viral-replications`，`Idempotency-Key` 请求头 | `create_viral_replication`，`idempotencyKey` 参数 |
| 查询 | `GET /api/v1/viral-replications/:id`，可带 `cursor` | `get_viral_replication`，`batchTaskId`、可选 `cursor` |

有效且启用的 Bearer Key 默认可调用全部已开放的 Gateway 能力，无需选择或校验 Scope。图片/视频创建分别使用 `viral_image_replication` / `viral_video_replication` 操作做幂等。同一用户、操作、幂等键和请求体只生成一次父批任务；相同键而请求体不同返回 409。

## 图片请求

```json
{
  "type": "image",
  "sourceImage": { "uploadId": "upl_source" },
  "productImages": [{ "uploadId": "upl_product" }],
  "requirement": "保留构图，替换成我的产品",
  "count": 2,
  "ratio": "1:1",
  "imageModel": "doubao-seedream-4.5"
}
```

必填：`type/sourceImage/requirement/count/ratio/imageModel`。可选：`productImages`、`industry`、`resolution`、`textModel`、`promptOptimization`。图片 `promptOptimization` 为 `{ "originalDescription": "...", "optimizedDescription": "...", "traceId": "..." }`，前两项必填，最后一项可选；`requirement` 是用户确认后的最终文本。`count` 为 1～100 的整数。模型标识必须是当前 viral 场景可选的唯一选择项；不传 `textModel` 时由服务端同源配置解析。

## 视频请求

```json
{
  "type": "video",
  "sourceVideo": { "uploadId": "upl_source" },
  "productImages": [{ "uploadId": "upl_product" }],
  "productDescription": "产品卖点与复刻要求",
  "count": 1,
  "videoModel": "doubao-seedance-2.0",
  "replicationMode": "partial"
}
```

必填：`type/sourceVideo/productDescription/count/videoModel`。可选：`productImages`、`referenceAudios`（最多 3 条）、`industry`、`textModel`、`resolution`、`replicationMode`（`partial|full`）、`strategies`（三个布尔值 `hotOpening/ownPattern/industryFission`）、`sourceVideoMetadata`（正数 `durationSeconds/width/height`）、`promptOptimization`。视频 `promptOptimization` 为 `{ "originalDescription": "...", "outline": "...", "outlineTraceId": "..." }`，前两项必填，最后一项可选；`productDescription` 是用户确认后的最终大纲。`count` 为 1～20 的整数。省略 `replicationMode` 使用 `partial`，省略 `textModel` 由服务端同源配置解析。完全复刻的源片时长/尺寸必须由服务端可信探测核对。

## 响应与状态

创建成功为 HTTP 202：`{ "id":"<batchTaskId>", "object":"viral_replication", "type":"image|video", "status":"pending", "createdAt":"<ISO>", "requestId":"req_xxx" }`。重放返回原 ID，REST 另带 `Idempotency-Replayed: true`。

查询响应包含 `id/object/type/status/createdAt/updatedAt/progress/outputs/error`。状态 `pending|running|completed|partial|failed|stopped`，后四项为终态。`progress` 图片给 `targetCount/completedCount/failedCount`；视频另给 `setsTotal/setsCompleted` 与 `segmentsTotal/segmentsCompleted/segmentsFailed`。`outputs` 只含已转存到对象存储的媒体，带临时下载 `url`。视频输出应标明成片或片段及 `groupIndex`；图片带槽位序号。最多 100 项，更多时返回 `nextCursor`，用 `?cursor=...` 读取后续页。不存在、跨用户或非 Gateway 复刻任务统一 404。

错误体沿用 Gateway：`{ "error": { "code": "...", "message": "...", "requestId": "req_xxx", "retryable": false } }`。遇到 429 按 `retryAfterSeconds` 等待；网络不确定时只重放原幂等键和原请求。404 新路由或缺少新 MCP Tool 表示部署未就绪，停止。
