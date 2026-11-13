# 🎬 baoliangxia-skills

> AI Agent Skills for [爆量匣（baoliangxia）](https://baoliangxia.com/) — 让你的 AI Agent 轻松调用爆量匣 Agent Gateway 的生图、生视频能力。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)

## ✨ 简介

**baoliangxia-skills** 是一个面向 AI Agent 的技能包（Skill），通过爆量匣的 Agent Gateway 提供 **AI 生图**、**AI 生视频** 等能力。Agent 可以按用户的自然语言需求选择模型、上传本地参考素材、提交生成任务、轮询进度，并把最终的图片/视频下载到本地。

本技能遵循 `SKILL.md` 技能规范，可被 `npx skills` 以及支持该规范的 AI Agent 平台（Cursor、Claude Code、Codex、OpenClaw 等）直接识别和调用。

## 📦 技能列表

| 技能 | 描述 | 脚本 |
|------|------|------|
| **baoliangxia-skills** | 爆量匣生图 / 生视频技能 — 按模型路由参数、上传素材、创建生成任务、等待并下载结果 | `create_model_generation.py` `upload_file.py` `query_generation.py` |

## 📥 快速安装

通过 `npx skills` 一键安装技能到你的项目中：

```bash 
# 交互式选择要安装的技能
npx skills add zlhub-baoliangxia/baoliangxia-skills

# 直接安装指定技能
npx skills add zlhub-baoliangxia/baoliangxia-skills --skill baoliangxia-skills
```

默认安装到当前项目。如需安装到用户级（所有项目共用），加上 `-g`，并用 `-a` 指定 Agent，例如 Codex：

```bash
npx skills add zlhub-baoliangxia/baoliangxia-skills --skill baoliangxia-skills -g -a codex -y
```

### 🔄 更新技能

仓库有新版本后，用同一个 CLI 即可更新到最新版：

```bash
# 更新已安装的全局（用户级）技能
npx skills update baoliangxia-skills -g -y

# 更新项目级技能
npx skills update baoliangxia-skills -p -y

# 查看已安装的技能
npx skills ls -g
```

- 如果 `update` 提示已是最新，但你确认仓库有新版本，可以重新执行上面的 `npx skills add ...` 命令，它会从 GitHub 拉取最新版并覆盖本地副本。
- 更新只替换技能文件，不会影响环境变量中的 `BAOLIANGXIA_AGENT_GATEWAY_API_KEY`。
- 更新后请重启 Agent 或新开一个会话，让新版技能生效。

### ⚙️ 配置 API Key

还没有 Key 时，先在爆量匣平台创建：

1. 打开 [爆量匣](https://baoliangxia.com/)。
2. 注册账号，或登录已有账号。
3. 点击左下角头像。
4. 打开 API/CLI 页面。
5. 创建自己的 Key。

创建完成后，把 Key 设置为环境变量即可使用：

```bash
# macOS / Linux
export BAOLIANGXIA_AGENT_GATEWAY_API_KEY="your-api-key"
```

```powershell
# Windows PowerShell（当前会话）
$env:BAOLIANGXIA_AGENT_GATEWAY_API_KEY = "your-api-key"
```

> 🎉 **就这么简单！** 安装后直接在 Agent 里用自然语言提需求即可，例如：
>
> - “用 baoliangxia-skills 生成一张雨夜霓虹街道的电影感插画。”
> - “用 baoliangxia-skills 生成一段 5 秒的产品广告视频。”
> - “把这张图片作为参考，生成一张同风格的海报。”
>
> 未指定模型时，图片默认使用 `doubao-seedream-4.5`，视频默认使用 `doubao-seedance-2.0`。

环境变量说明：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `BAOLIANGXIA_AGENT_GATEWAY_API_KEY` | ✅ | — | Agent Gateway API 鉴权密钥 |

> ⚠️ API Key 属于机密信息：请只通过环境变量配置，不要写入项目文件、提交到代码仓库、或粘贴到提示词/日志中。

## 🧠 支持的模型

所有模型统一通过 `create_model_generation.py --model <模型标识>` 调用，各模型的参数拼装规则和不可用能力见 [`references/models/`](skills/baoliangxia-skills/references/models)。

| 类型   | 模型标识                                                                                                                                                                                                                                       |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 图片   | `doubao-seedream-4.5` `doubao-seedream-5.0-lite` `doubao-seedream-5.0-pro` `zl-ooe-3.1-flash-image-t` `zl-pep-image-2-async` `zl-pep-image-2.5-flare-async` `zl-pep-image-2.5-sunburst-async` |
| 视频   | `doubao-seedance-2.0` `doubao-seedance-2.0-fast` `doubao-seedance-2.0-mini` `doubao-seedance-2.5` `happyhorse-1.1` `jielan-video` `jielan-video-lite` `jielan-video-mini` `kling-v3-omni` `MiniMax-H3` `wan3.0-video` `wan3.0-video-prime` |
| 爆款复刻 | 即将支持                                                                                                                                                                                                                                       |
| 视频超分 | 仅用于视频提升画质，使用 `skills/baoliangxia-skills/scripts/create_video_super_resolution.py` |

> 以 `python3 skills/baoliangxia-skills/scripts/create_model_generation.py --list-models` 的输出为准。

## 🛠️ 手动使用 / 调试

多视频和单输出图片会先并发提交、再统一等待；支持数量参数的图片按实际返回数量补缺。相同提示词使用 `create_batch_generations.py "提示词" --model 模型 --count 5`，不同提示词使用 `--jobs-file`。详细规则、清单格式及恢复方式见 [批量生成说明](skills/baoliangxia-skills/references/batch-generation.md)。

<details>
<summary>如果你需要手动调用脚本或调试，点击展开查看详细用法</summary>

### 前置要求

- **Python 3.8+**（仅使用标准库，无需安装额外依赖；Windows 上如无 `python3`，请使用 `python` 或 `py -3`）
- **`BAOLIANGXIA_AGENT_GATEWAY_API_KEY`** 环境变量已设置

### 查看模型目录

```bash
python3 skills/baoliangxia-skills/scripts/create_model_generation.py --list-models
```

### 预览请求（不发送、不读取密钥）

```bash
python3 skills/baoliangxia-skills/scripts/create_model_generation.py "一只在窗边的猫" \
  --model MiniMax-H3 --duration 5 --aspect-ratio 16:9 --dry-run
```

### 上传本地素材

```bash
python3 skills/baoliangxia-skills/scripts/upload_file.py /path/to/reference.png
```

**输出示例：**

```json
{
  "uploadId": "upl_123",
  "status": "completed"
}
```

生成任务只接受 `{ "uploadId": "upl_xxx" }` 形式的素材引用，不能直接传本地路径、外链、Base64 或 Data URL。

### 创建生成任务

```bash
# 文生图 / 图生图
python3 skills/baoliangxia-skills/scripts/create_model_generation.py "画一只在窗边的猫" \
  --model doubao-seedream-4.5 --input-upload-id upl_xxx

# 视频
python3 skills/baoliangxia-skills/scripts/create_model_generation.py "制作产品展示视频" \
  --model doubao-seedance-2.0 --resolution 1080p
```

**输出示例：**

```json
{
  "generationId": "gen_xxx",
  "idempotencyKey": "..."
}
```

如需对同一请求做不确定的重试，请复用返回的 `idempotencyKey`（`--idempotency-key`）；prompt、模型、素材或参数变化时使用新的 key。

### 查询进度 & 下载结果

```bash
# 查询一次
python3 skills/baoliangxia-skills/scripts/query_generation.py <GENERATION_ID>

# 轮询直到结束，并把结果下载到指定目录
python3 skills/baoliangxia-skills/scripts/query_generation.py <GENERATION_ID> --wait \
  --output-dir ./baoliangxia_results/<GENERATION_ID>
```

`pending` / `running` 为中间状态，`completed` / `failed` / `stopped` 为终态，只有 `completed` 表示成功。

</details>

## 📁 项目结构

```
baoliangxia-skills/
├── README.md
├── LICENSE
├── .gitignore
└── skills/
    └── baoliangxia-skills/                 # 爆量匣生图 / 生视频技能
        ├── SKILL.md                        # 技能描述文件
        ├── references/
        │   └── models/                     # 各模型的参数拼装规则（按需读取）
        └── scripts/
            ├── _common.py                  # 公共模块（鉴权、HTTP 请求、上传、下载）
            ├── _models.py                  # 模型目录与参数约束
            ├── _generation.py              # 生成请求公共逻辑
            ├── create_model_generation.py  # 统一创建入口（--model）
            ├── create_batch_generations.py # 批量并发 / 数量补缺 / 统一等待下载
            ├── _batch.py                   # 批量调度与提交前任务存档
            ├── upload_file.py              # 上传图片 / 视频 / 音频素材
            ├── query_generation.py         # 查询进度 / 等待 / 下载结果
            └── create_*.py                 # 按模型/类型的便捷入口（兼容旧用法）
```

## 🔧 API 参考

### 鉴权

所有 API 请求通过 HTTP Header 进行 Bearer Token 鉴权：

```
Authorization: Bearer <BAOLIANGXIA_AGENT_GATEWAY_API_KEY>
```

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/images/generations` | 创建图片生成任务 |
| `POST` | `/api/v1/videos/generations` | 创建视频生成任务 |
| `GET` | `/api/v1/generations/:generationId` | 查询生成任务状态与结果 |
| `POST` | `/api/v1/uploads/ticket` | 申请素材上传凭证 |
| `POST` | `/api/v1/uploads/:uploadId/complete` | 确认素材上传完成 |

## 🤖 Agent 集成指南

本技能包设计为被 AI Agent 自动调用。典型工作流如下：

```
用户指令 → Agent 选择模型并读取对应 references/models/*.md
              ↓
   （有本地参考素材）upload_file.py → uploadId
              ↓
   create_model_generation.py → generationId
              ↓
   query_generation.py --wait --output-dir → 本地文件
              ↓
        向用户展示生成结果
```

### 最佳实践

- **精确模型标识**：使用路由表中的模型标识，不要使用参考文档里的上游名称
- **只读所需参考**：只加载所选模型对应的那一份 `references/models/*.md`，避免占用上下文
- **尊重用户参数**：用户未指定比例/分辨率时省略 `--aspect-ratio` / `--resolution`，由脚本套用该模型的默认值；用户明确指定的值始终优先
- **不静默降级**：用户的需求命中参考文档的“不可用能力”时，直接告知用户，而不是用其他字段近似实现
- **先 dry-run**：对不确定的参数组合，先加 `--dry-run` 检查请求内容

## 🤝 贡献

欢迎提交 Pull Request 来添加新的模型或改进现有技能！

### 添加新模型

1. 在 `skills/baoliangxia-skills/scripts/_models.py` 的 `MODELS` 中登记模型及其参数约束
2. 在 `skills/baoliangxia-skills/references/models/` 下添加（或复用）参考文档，须包含“参数拼装”和“不可用能力”两节
3. 在 `SKILL.md` 的路由表中新增对应行
4. 更新本 README 的模型列表

## 📄 License

本项目采用 [MIT License](LICENSE) 开源。
