---
name: baoliangxia-skill
description: 爆量匣 (baoliangxia) AI 生图、生视频技能 - 通过 Agent Gateway 调用 Seedream、Seedance、GPT Image 2、Kling、Wan、MiniMax-H3、Vidu、HappyHorse、即梦视频等模型。覆盖场景：文生图、图生图、参考图生成、文生视频、图生视频、首尾帧、参考视频/音频生成、数字人口播、对口型（lip-sync）、视频超分/提升清晰度、剧集带货短剧广告、本地素材上传、查询生成进度、下载生成结果、配置 API Key。当用户提到爆量匣、baoliangxia，或要求"画一张/生成一张图""做个海报""生成一段视频/广告片""把这张图做成视频""让这个人物说话""提升视频清晰度""查一下生成状态"时都应触发。Use when the user asks to generate, create, draw, edit, modify, upscale, lip-sync, or check any image, video, or media asset through baoliangxia/爆量匣, including local media upload, generation status, downloads, API-key setup, or garbled Chinese REST prompts.
version: 1.0.3
display_name: baoliangxia-skill
display_name_en: Baoliangxia · AI Image & Video
description_zh: 通过爆量匣（baoliangxia）Agent Gateway 生成图片与视频，覆盖文生图、图生图、参考图/参考视频/参考音频驱动、首尾帧、数字人口播与对口型、视频超分、剧集带货短剧广告，并支持本地素材上传、生成进度查询与结果下载。默认图片模型 doubao-seedream-4.5，默认视频模型 doubao-seedance-2.0。
description_en: Generate images and videos through the Baoliangxia Agent Gateway - text-to-image, image-to-image, reference-image/video/audio driven generation, first/last-frame video, digital-human talking head and lip-sync, video upscaling, and short-drama ads, with local asset upload, generation status polling and result download. Defaults are doubao-seedream-4.5 for images and doubao-seedance-2.0 for videos.
user-invocable: true
metadata:
  {
    "openclaw":
      {
        "emoji": "🎬",
        "requires":
          {
            "bins": ["python3"],
            "env": ["BAOLIANGXIA_AGENT_GATEWAY_API_KEY"]
          },
        "primaryEnv": "BAOLIANGXIA_AGENT_GATEWAY_API_KEY"
      }
  }
---

# baoliangxia-skill

Use the bundled Python scripts to call baoliangxia-skill. Preserve the user's prompt unless they explicitly request rewriting.

## First-use guidance

Give this concise onboarding response in order, before discussing advanced model options, when the user is using this skill for the first time or asks how to use it:

1. If the skill is not already available to their Agent, offer to install the skill into their Agent. Ask permission before installing it, then follow the "Install or update with the skills CLI" steps in the Installation section.
2. The Agent, not the user, checks whether Python is available after installation. Explain that Python 3 is required. If it is unavailable, offer to install Python after obtaining approval, then verify it before proceeding.
3. If `BAOLIANGXIA_AGENT_GATEWAY_API_KEY` is not configured, or the user asks where to get a key, give the create-key steps below before any generation. Then explain that the key must be set as that environment variable. Let the user either configure it themselves or provide their key for the AI to configure. If they provide a key, treat it as a secret: use it only for that configuration, never echo or repeat it, and never put it in project files, source control, prompts, or logs. Subsequent scripts must read the key from the environment variable.
4. Once the skill, Python, and key are ready, tell the user to send a plain-language request in the Agent. State that images default to `doubao-seedream-4.5` and videos default to `doubao-seedance-2.0` when no model is requested. The Agent handles generation, waiting, downloading, and presenting the result.

### Create a key

When the user has no key yet, include these steps in the user-facing reply. Do not replace them with a generic "set an API key" line, and do not send the user anywhere except `https://baoliangxia.com/`.

1. Open the 爆量匣 platform at https://baoliangxia.com/.
2. Register an account, or log in if they already have one.
3. Click the avatar at the bottom left.
4. Open the API/CLI page.
5. Create their own key.

The same steps apply on their own when a later request finds `BAOLIANGXIA_AGENT_GATEWAY_API_KEY` unset. Stop before submitting a generation and give this path again. Skip the install and Python steps when those are already done.

### Agent-native examples

- “用 baoliangxia-skill 生成一张雨夜霓虹街道的电影感插画。”
- “用 baoliangxia-skill 生成一段 5 秒的产品广告视频。”
- “把这张图片作为参考，生成一张同风格的海报。”

Keep the user-facing response focused on what to do in the Agent. Do not include terminal instructions or implementation details unless the user specifically asks for them. The create-key steps are required in that reply whenever the user has no key; they are not implementation details.

## Authentication

For generation requests, read the API key from `BAOLIANGXIA_AGENT_GATEWAY_API_KEY`. Never place it in commands, files, prompts, or logs. The sole exception is a user explicitly providing their key to authorize the AI to configure this environment variable; handle that key using the first-use guidance above. If the variable is unset, or the user says they do not have a key, stop and follow "Create a key" above.

The default service URL is `https://baoliangxia.com/`. Override it with `BAOLIANGXIA_AGENT_GATEWAY_BASE_URL` or `--base-url` only when the user supplies another deployment.

## Model routing

Determine the exact model before building arguments. If the user does not name a model, use `doubao-seedream-4.5` for images and `doubao-seedance-2.0` for videos.

If the user does not name an aspect ratio, resolution, or clarity (清晰度), do not copy sample values from a reference. Omit `--aspect-ratio` and `--resolution`. `scripts/create_model_generation.py` fills both from that model's configured default. Explicit user values always win. A default written in the model document wins over the shared fallback. Where the document states none, the ratio is `16:9` when the model exposes it, and the resolution is the supported tier nearest 720p with that model's exact spelling. Image models without a documented size use `1K` when offered, otherwise the lowest tier. Models that cannot express a field get no default for it. `happyhorse-1.1` omits the ratio when an image or video is attached. `MiniMax-H3` uses `adaptive` in that case. `--list-models` prints the text-only `defaultAspectRatio` and `defaultResolution`.

Read only the selected row's reference. Shared family references are intentional. Submit the exact database identifier in the first column, even when the reference uses a different upstream name. In particular:

- Image 2 async → `zl-pep-image-2-async`
- Image 2.5 async → `zl-pep-image-2.5-flare-async` or `zl-pep-image-2.5-sunburst-async`
- Nano Banana 3.1 Flash → `zl-ooe-3.1-flash-image-t`
- 剧集带货 / Vidu Short Ads → `vidu-short_drama_ads_fast`

Every available row uses `scripts/create_model_generation.py "PROMPT" --model MODEL [options]`. Run `--list-models` for the machine-readable catalog. Add `--dry-run` to validate and inspect the exact endpoint and payload without reading credentials or making a network request.

| Exact database model identifier | Read only this reference | Availability |
|---|---|---|
| `doubao-seedream-4.5` | `references/models/doubao-seedream-4.5.md` | available |
| `doubao-seedream-5.0-lite` | `references/models/doubao-seedream-5.0-lite.md` | available |
| `doubao-seedream-5.0-pro` | `references/models/doubao-seedream-5.0-pro.md` | available |
| `zl-ooe-3.1-flash-image-t` | `references/models/zl-ooe-3.1-flash-image.md` | available |
| `zl-pep-image-2-async` | `references/models/zl-pep-image-2.md` | available |
| `zl-pep-image-2.5-flare-async` | `references/models/zl-pep-image-2.md` | available |
| `zl-pep-image-2.5-sunburst-async` | `references/models/zl-pep-image-2.md` | available |
| `doubao-seedance-2.0` | `references/models/doubao-seedance-2.0.md` | available |
| `doubao-seedance-2.0-fast` | `references/models/doubao-seedance-2.0.md` | available |
| `doubao-seedance-2.0-mini` | `references/models/doubao-seedance-2.0.md` | available |
| `doubao-seedance-2.5` | `references/models/doubao-seedance-2.5.md` | available |
| `happyhorse-1.1` | `references/models/happyhorse-1.1.md` | available |
| `jielan-video` | `references/models/jielan-video.md` | available |
| `jielan-video-lite` | `references/models/jielan-video.md` | available |
| `jielan-video-mini` | `references/models/jielan-video.md` | available |
| `kling-v3-omni` | `references/models/kling-v3-omni.md` | available |
| `MiniMax-H3` | `references/models/minimax-h3.md` | available |
| `video-sr` | `references/models/video-sr.md` | fail-closed until Gateway exposes SR metadata |
| `vidu` | `references/models/vidu-solutions.md` | available for text-driven lip sync |
| `vidu-short_drama_ads_fast` | `references/models/vidu-short-ads.md` | available |
| `viduq2-pro` | `references/models/vidu-solutions.md` | available for text-driven digital human |
| `viduq2-turbo` | `references/models/vidu-solutions.md` | available for text-driven digital human |
| `viduq3-ad` | `references/models/vidu-q3.md` | available |
| `viduq3-mix` | `references/models/vidu-q3.md` | available |
| `wan3.0-video` | `references/models/wan3.0-video.md` | available |
| `wan3.0-video-prime` | `references/models/wan3.0-video.md` | available |

Do not substitute an upstream documentation name such as `gpt-image-2-async` or `zl-video` for the database identifier.

## Execution contract

1. Read the selected model reference.
2. Upload every local reference asset with `scripts/upload_file.py FILE` and retain each `uploadId`.
3. Translate user intent to flags using the reference's **参数拼装** table. Omit `--aspect-ratio` and `--resolution` when the user did not specify them, so the script can apply the model default. The script also supplies declared Gateway option defaults; pass optional controls only when the user requests a different value.
   For Gateway-exposed model controls, use repeatable `--option KEY=VALUE`; `--watermark true|false` is shorthand for the model's `watermark` option. Boolean options accept only lowercase `true` or `false`. Repeat `--reference-audio-id ID` for reference audio; do not combine it with legacy `--audio-upload-id`. Reference audio is source material, while options such as `audio=false` control generated sound.
4. If the request appears under **不可用能力**, stop before submission. Do not silently drop it, approximate it with another field, or hide it in metadata.
5. For multiple outputs or independent requests, use `scripts/create_batch_generations.py` as described below. For one output, run `scripts/create_model_generation.py` and retain `generationId` plus `idempotencyKey`.
6. The batch script waits and downloads automatically. For a single task, run `scripts/query_generation.py GENERATION_ID --wait --output-dir OUTPUT_DIR`.
7. Present the result using the fixed structure in **Result presentation**.

All scripts accept `--help`. On Windows, use `python` or `py -3` when `python3` is unavailable.

## Multiple images or videos

Use `create_batch_generations.py "PROMPT" --model MODEL --count N` for the same prompt and parameters. For different prompts/models, read [references/batch-generation.md](references/batch-generation.md) and prepare one `--jobs-file`. Independent jobs belong in one batch, so their creation requests overlap before waiting for results. If a later task depends on an earlier output, complete that dependency first.

| Effective model capability | Batch behavior |
|---|---|
| All available video models; `doubao-seedream-5.0-pro`; `zl-ooe-3.1-flash-image-t`; Image 2.5 async models | Submit N independent tasks concurrently without `n`, then poll them together. Default HTTP concurrency is 5, configurable up to 20. |
| `doubao-seedream-4.5`, `doubao-seedream-5.0-lite` | One task at a time per prompt, `n=min(remaining, 15-reference_count)`; wait for completed, count actual outputs, then request only the shortfall. |
| `zl-pep-image-2-async` | Same completion/count/top-up loop, at most 10 outputs per task. |

`--count` is the total target; `--n` remains a single-task parameter and is not accepted by the batch entry point. Do not run a create→wait loop once per video/single-output image. Do not launch competing top-ups for the same quantity-capable image job. `--list-models` reports `supportsOutputCount`, `maxOutputsPerRequest`, and `batchStrategy`.

Each request gets a separate idempotency key saved in `OUTPUT_DIR/batch.json` before submission. A 429 retries the same key with the server's delay (at most 3 attempts); existing Gateway queues and concurrency limits still apply. A failed/stopped task, zero outputs, uncertain submission, query timeout, or download error never triggers an automatic replacement generation. Report partial results and the remaining count. On timeout, continue querying the saved generation IDs. For uncertain submission, replay only the exact saved request with its saved key; never restart the batch with fresh keys. See the batch reference for recovery. Never report a whole batch as successful until every requested output is available locally.

## Result presentation

After a generation reaches `completed` and the files are downloaded, reply with the fixed structure below. Write it in the user's language (default 中文) and keep the section labels exactly as shown. Show the media itself (image preview or video file) alongside this text when the Agent supports it.

```markdown
**<图片|视频|插画|海报…>已生成 ✅**

**规格**：<比例/方向> · <分辨率档位>（<像素宽×高>） · `<exact model id>` · <文生图|图生图|文生视频|图生视频…> · <文件大小或时长>

**内容要点**
- <主体与场景>
- <构图/镜头/光线>
- <色调/风格>

**文件**
`<absolute path of the downloaded file>`

本次生成消耗约 <N> 积分。   <!-- optional: only when the Gateway reports a cost -->

**说明**
- <only when a default was applied or the request was adjusted; see rules below>

**可调整方向**
- <resolution recommendation based on the current result and supported model tiers>
- <1–3 other concrete follow-up options>

告诉我要改哪一点即可。
```

Rules:

1. **Status line.** One short line: the asset type plus `已生成 ✅`. On `failed` or `stopped`, replace it with `生成失败 ❌` or `生成已停止 ⏹`, state the reason returned by the Gateway, and skip the remaining sections except 可调整方向 (suggest a retry or a changed parameter).
2. **规格.** One line, items separated by ` · `. The model identifier is wrapped in backticks. Fill the ratio, resolution, pixel size, and file size or duration from the actual result or the submitted parameters, never from memory. Drop an item rather than guess it.
3. **内容要点.** 3 bullets or one compact paragraph describing what is actually in the result: subject and scene, composition or camera, color and style. Describe what you can see or what the prompt specified. Do not invent details.
4. **文件.** Give the full local path of every downloaded file in a code span, one per line. For several outputs, list them in order.
5. **说明.** Include this section only when something needs explaining. Typical cases: the user left the ratio or resolution unset so the model default was used (say which value and why), the user's wording was only partly specific (for example 只说了"横版"), or a requested capability was unavailable. Omit the whole section when nothing needs explaining.
6. **积分消耗.** Mention `本次生成消耗约 N 积分` right after 文件 only when the Gateway response reports a cost. Never estimate or invent it.
7. **可调整方向.** Offer 2–4 short, concrete options the user can pick. For a completed result with a known resolution, include one recommendation based on its current tier, the user's intended use, and the selected model reference's supported resolutions:
   - If a higher tier is available, name the current tier and a specific supported upgrade, and explain when it is useful. For example, `当前为 2K；如需大幅展示或后续裁切，可提升到 4K` or `当前为 720p；如需更清晰的全屏播放，可提升到 1080p`. Use these examples only when the selected model supports those tiers; do not assume every model or variant does.
   - If the result is already at the model's highest supported tier, recommend keeping that resolution and improving composition, lighting, or detail instead. For example, `当前为 4K，已是该模型支持的最高档位；建议保留分辨率，微调构图或光线`.
   - If the current resolution or supported tiers are unknown, offer other adjustments instead of guessing a resolution recommendation. For failed or stopped tasks, follow rule 1.
   Keep the remaining options relevant to the result, such as a different ratio, camera angle, color mood, or adding or removing an element. Recommend only supported changes; these are suggestions for the user to choose, not authorization to regenerate. Do not invent cost or generation-time savings.
8. **Closing line.** End with exactly one short invitation, `告诉我要改哪一点即可。`, and nothing after it.
9. **Do not** paste raw JSON, `generationId`, `idempotencyKey`, endpoints, or script output into this reply unless the user asks.

Example for a text-to-image result:

```markdown
**图片已生成 ✅**

**规格**：16:9 横版 · 2K（2848×1600） · `doubao-seedream-4.5` · 文生图 · 约 0.85 MB

**内容要点**
- 静物近景：窗边木桌为画面主体，窗外交代山间木屋环境
- 桌上一杯咖啡与一本摊开的书，晨光斜射形成长条暖影
- 日系清新质感：柔和暖阳、低饱和浅木色与米白，通透干净的清晨氛围

**文件**
`C:\Users\me\baoliangxia_results\GENERATION_ID\01.jpg`

**说明**
- 你只指定了"横版"，未指定比例与分辨率，因此按模型默认出图：比例取 16:9 横版，分辨率采用 2K。

**可调整方向**
- 换成 21:9 更宽的电影感横幅，或 3:2 更接近胶片静物比例
- 当前为 2K；日常展示可保留，如需大幅展示或后续裁切，建议提升到该模型支持的 4K
- 调整氛围：更冷的晨曦色调 / 更强的暖色逆光 / 更克制的极简留白

告诉我要改哪一点即可。
```

## Shared commands

```bash
python3 {baseDir}/scripts/create_model_generation.py --list-models
python3 {baseDir}/scripts/create_model_generation.py "USER_PROMPT" \
  --model MiniMax-H3 --duration 5 --aspect-ratio 16:9 --dry-run
python3 {baseDir}/scripts/upload_file.py /path/to/reference.png
python3 {baseDir}/scripts/create_model_generation.py "USER_PROMPT" \
  --model doubao-seedream-4.5 --input-upload-id upl_xxx
python3 {baseDir}/scripts/query_generation.py GENERATION_ID --wait \
  --output-dir /path/to/baoliangxia_results/GENERATION_ID
```

Generation payloads accept uploaded assets only as `{ "uploadId": "upl_xxx" }`. Do not pass a local path, external URL, Base64, or Data URL directly to a creation script.

`pending` and `running` are intermediate. `completed`, `failed`, and `stopped` are terminal. Only `completed` is success.

For an uncertain retry of the same logical request, reuse the returned `idempotencyKey` with `--idempotency-key`. When prompt, model, media, or parameters change, use a new key.

## Common mistakes

| Mistake | Correct behavior |
|---|---|
| Copying the upstream model name from a reference | Use the exact database identifier from the routing table |
| Passing a resolution with the wrong case | Preserve the documented value exactly, such as `1080P` for Wan and `1080p` for Seedance |
| Passing a control the Gateway cannot express | Stop and report the unavailable capability |
| Copying a sample ratio or resolution when the user did not ask for one | Omit `--aspect-ratio` and `--resolution` and let the script apply the model default |
| Loading every model reference | Load only the selected row's reference |
| Telling a first-time user, or a user with no key, only to set an environment variable | Send them to https://baoliangxia.com/ to register or log in, then bottom-left avatar → API/CLI → create their own key |

## Installation

Install `SKILL.md`, `scripts/`, and `references/`. Do not install `.env`, cache directories, or credentials.

### Install or update with the skills CLI 

The skill is published at `https://github.com/zlhub-baoliangxia/baoliangxia-skills`. Ask the user for permission before installing or updating, then run one of these commands. Node.js (for `npx`) must be available.

```bash
# Install (user-level, for Codex)
npx skills add zlhub-baoliangxia/baoliangxia-skills --skill baoliangxia-skills -g -a codex -y

# Update an installed copy to the latest version
npx skills update baoliangxia-skills -g -y
```

- Replace `-a codex` with another agent name (for example `cursor` or `claude-code`) when the user runs a different Agent. Omit `-g` for a project-level install.
- If `update` reports nothing to do but the user expects a newer version, re-run the `add` command. It pulls the latest version from GitHub and overwrites the installed copy.
- Never remove or overwrite the user's `BAOLIANGXIA_AGENT_GATEWAY_API_KEY`. It lives in the environment, not in the skill directory, so updating the skill does not affect it.
- A newly installed or updated skill is picked up by the Agent in a new session. Tell the user to restart the Agent or open a new conversation.
