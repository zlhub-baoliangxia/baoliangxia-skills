# 批量生成与恢复

同一提示词和参数，5个视频先并发创建，再统一等待并下载：

```bash
python3 {baseDir}/scripts/create_batch_generations.py "USER_PROMPT" \
  --model doubao-seedance-2.0 --count 5 --output-dir /absolute/path/new_batch
```

图片同样使用 `--count`。Seedream4.5/Lite 每次上限 `15-参考图数`，Image 2 async 每次上限10，均在完成后按实际张数补缺；Pro、Image 2.5 async 和其他单输出模型不传n，拆成单图任务并发。批量参数默认等待6小时，覆盖视频合法窗口；可以用 `--timeout` 自定义本地等待时限，但超时不等于服务端终态。

不同提示词、不同模型放入一个UTF-8 JSON文件；字段沿用脚本参数的下划线命名。公共 `--model` / prompt 不能与 `--jobs-file` 混用；其他生成参数也应写在每一项内。可用 `reference_audio_id` 字符串数组、`options` 对象和布尔 `watermark` 字段；旧单音频入口 `audio_upload_id` 仍可使用，但不能与 `reference_audio_id` 同时设置。

```json
[
  {"model":"doubao-seedance-2.0","prompt":"第一个镜头的用户原文","count":1,"duration":5},
  {"model":"doubao-seedance-2.0","prompt":"第二个镜头的用户原文","count":1,"duration":5},
  {"model":"doubao-seedream-4.5","prompt":"用户海报原文","count":5,"input_upload_id":["upl_product"],"watermark":true},
  {"model":"wan3.0-video","prompt":"参考音频节奏的镜头","count":1,"reference_audio_id":["upl_a","upl_b"],"options":{"audio":false}}
]
```

```bash
python3 {baseDir}/scripts/create_batch_generations.py \
  --jobs-file /absolute/path/jobs.json --output-dir /absolute/path/new_batch
```

所有任务先校验后提交，数量总和1–100。默认5个HTTP连接，`--concurrency 1..20` 可调整；所有初始任务提交阶段结束后集中查询，绝不等待一个视频完成才提交下一个。`--dry-run` 展示首轮请求，不读取密钥、建目录或联网。后续补图请求取决于实际输出，无法预先确定。不同提示词之间的补图各自独立。

## 生成页会话

用户明确要求「新开一个对话」「这批单独放一组」时，在命令行加 `--new-session`，要命名再加 `--session-title "标题"`（最多50字）。这两个参数是批次级的，`--jobs-file` 的每一项里不能写；和 `--jobs-file` 一起用时写在命令行上。

- 只有第一个初始任务带 `newSession` / `sessionTitle`。它先单独提交，有了受理结果后其余初始任务再并发提交，因此追加进它新建的会话。若同时提交，其余任务可能先落进当天的旧会话。
- 其余初始任务和所有补图任务都不带会话字段。
- 第一个任务被拒或结果不确定时，其余任务照常提交，落到当天最新的会话；实际落在哪个会话以各任务 `submission.session.title` 为准。
- `--dry-run` 的 `initialTasks` 里只有第一项带会话字段；`batch.json` 里该项标 `carriesSession: true`，恢复时按原 payload 和原键重放即可，不要给其他任务补加会话字段。
- 没要求时不加这两个参数，结果按天自动归到当天最新的 API 会话。

Gateway允许图片n，但模型组包可映射、锁定或删除字段。Pro和Image 2.5 async 没有多输出能力；Seedream需要Gateway同时将组图模式设为auto。使用旧服务端时可能每轮只返回一张，执行器仍按实际张数补齐。不得绕过网关传厂商原始组图字段。

输出目录内 `batch.json` 保存每次请求、独立幂等键、任务ID、终态、实际输出及下载路径，不含API Key。这个文件在POST前落盘，结果逐步更新。已存在该文件的目录不能作为新批次使用，避免覆盖恢复依据。退出码0表示全部生成和下载成功；2表示部分完成、仍在运行、未完成或下载失败。

恢复时先读batch.json：

- 有generationId：用 `query_generation.py ID --wait --timeout 21600 --output-dir ORIGINAL_TASK_DIR` 查询原任务并下载。对多个未完成ID同时运行查询命令，统一收集结果，不再提交生成。
- submission_unknown / prepared且没有ID：可能已受理，不能当成失败缺额。使用保存的endpoint、payload和idempotencyKey重放完全相同的请求，再查询返回的ID。可以用标准库HTTP helper重放，API Key继续从环境变量读取；不要手写带Key的命令。
- rejected：没有确认成功受理，先处理限流/参数/余额错误，再用同一请求和原键重试。
- completed但downloadError：只查询并重新下载，不重新生成。
- failed / stopped / completed零输出：保留已成功文件和失败原因，停止自动补交；重试新的付费生成前按用户意图处理。

示例：先请求n=5，完成实际返回2张，下一次只请求n=3；如果原任务仍running、查询超时或无法确认受理，就不新建补图任务。每次completed至少增加一个有效输出才继续，最多目标总数轮，不会无限空跑。

最终展示所有成功文件；部分完成时明确“已完成X/Y，剩余Z”以及原因。仅使用Gateway明确返回的费用，不推测积分或算力点。
