# 技能一天检查一次更新

日期：2026-11-16

## 目标

`baoliangxia-skills` 和 `baoliangxia-viral-replication` 在用户这次请求做完之后，最多每天检查一次发布版本。已是最新、未满 24 小时、或检查失败时不产生任何输出。发现尚未提示过的新版本时，只追加一行字，不自动安装。

## 行为

1. 上传、提交、等待、下载和结果呈现先完成。检查不插在这些步骤前面，也不推迟它们。首次引导、技能未安装、没有 Python 或没有 API Key 时跳过。
2. 然后运行该技能自己的 `scripts/check_update.py`，给进程大约 3 秒。脚本的网络读取超时是 2 秒。
3. 若这次检查需要单独的联网授权，跳过，不问用户。
4. 标准输出为空、超时或报错：不提更新。
5. 有输出时，把那一行原样接在结果后面。不改成提问，不等待回答。只有用户随后要求更新，才执行 `npx skills update <技能名>`。更新不改 API Key，完成后告知新开一次对话。

## 一天一次

戳记不放在技能目录里，避免更新技能时被覆盖，也不会进 Git。

- Windows：`%LOCALAPPDATA%\baoliangxia-skills\update-check.json`
- 没有 `LOCALAPPDATA` 时：`%USERPROFILE%\AppData\Local\baoliangxia-skills\update-check.json`
- macOS / Linux：`~/.cache/baoliangxia-skills/update-check.json`

文件按技能名分条目，两个技能互不覆盖。`checkedAt` 距现在不足 24 小时就退出，不访问网络，也不改文件。满 24 小时、时间戳无法解析、或时间戳在未来，才检查。

检查开始前先写下 `checkedAt`。之后请求失败、进程被打断、或远程版本无法解析，当天都不再重试。失败时保留原来的 `notifiedVersion`。

## 版本比较

本地版本和技能名读自旁边 `SKILL.md` 的 frontmatter。远程只读 GitHub 上对应文件的前 4096 字节：

`https://raw.githubusercontent.com/zlhub-baoliangxia/baoliangxia-skills/main/skills/<name>/SKILL.md`

请求不带 Authorization，不读取 `BAOLIANGXIA_AGENT_GATEWAY_API_KEY`。技能名只允许小写字母、数字和连字符；不合法或本地没有数字版本时，记下本次检查后直接返回。

版本按点分的数字比较，`1.0.10` 高于 `1.0.9`，`1.0` 等于 `1.0.0`。

- 远程更高，且 `notifiedVersion` 还不是这个远程版本：输出一行，并记下 `notifiedVersion`。
- 同一个新版本之后再次检查：不输出。
- 远程等于或低于本地：不输出，并清掉 `notifiedVersion`。本地更高视为开发副本，同样不提示。

固定输出：

`爆量匣技能有新版本 1.0.7（当前 1.0.6）。说一声「更新技能」我就帮你更新；更新后需要新开一次对话才生效。`

## 版本号

`baoliangxia-skills` 为 `1.0.7`。`baoliangxia-viral-replication` 补上首个版本号 `1.0.0`。两个技能各自带一份相同的 `scripts/check_update.py`，因为它们可以分开安装。

## 不做

不自动安装，不开机检查，不每天重复提醒同一版本，检查失败不重试，不把戳记写入技能目录。
