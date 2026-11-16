#!/usr/bin/env python3
"""Check once a day whether this installed skill is older than the published copy.

Prints one line when a newer version has not been mentioned yet. Prints nothing
when the skill is current, the check already ran within 24 hours, or the check
fails. This script never installs or overwrites anything, and it never reads
the API key.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

FETCH_TIMEOUT_SECONDS = 2
FETCH_BYTES = 4096
REMOTE_TEMPLATE = "https://raw.githubusercontent.com/zlhub-baoliangxia/baoliangxia-skills/main/skills/{name}/SKILL.md"
NOTICE = "爆量匣技能有新版本 {remote}（当前 {local}）。说一声「更新技能」我就帮你更新；更新后需要新开一次对话才生效。"
SAFE_NAME = re.compile(r"[a-z0-9-]+")


def stamp_path(system: str | None = None, environ: dict | None = None, home: Path | None = None) -> Path:
    system = os.name if system is None else system
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if system == "nt":
        base = environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / "baoliangxia-skills" / "update-check.json"
    return home / ".cache" / "baoliangxia-skills" / "update-check.json"


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    found: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        found[key.strip()] = value.strip().strip("\"'")
    return found


def parse_version(value: str) -> tuple[int, ...] | None:
    parts = value.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def compare_versions(left: str, right: str) -> int:
    a = parse_version(left)
    b = parse_version(right)
    if a is None or b is None:
        raise ValueError(f"not a numeric version: {left!r} {right!r}")
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    if a > b:
        return 1
    if a < b:
        return -1
    return 0


def format_time(now: datetime) -> str:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def is_due(entry: dict, now: datetime) -> bool:
    raw = entry.get("checkedAt")
    if not isinstance(raw, str):
        return True
    try:
        checked = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    if checked > now:
        return True
    return now - checked >= timedelta(hours=24)


def load_stamp(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_stamp(path: Path, data: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    except OSError:
        return False
    return True


def fetch_remote_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"Accept": "text/plain", "User-Agent": "baoliangxia-skill-update-check"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        return response.read(FETCH_BYTES).decode("utf-8", errors="replace")


def run_check(*, skill_dir: Path, stamp_path: Path, now: datetime, fetch) -> str:
    try:
        meta = parse_frontmatter((Path(skill_dir) / "SKILL.md").read_text(encoding="utf-8"))
    except OSError:
        return ""
    name = meta.get("name") or ""
    local = meta.get("version") or ""
    stamp = load_stamp(Path(stamp_path))
    current = stamp.get(name)
    entry = dict(current) if isinstance(current, dict) else {}
    if name and not is_due(entry, now):
        return ""

    entry["checkedAt"] = format_time(now)
    if parse_version(local):
        entry["localVersion"] = local
    if name:
        stamp[name] = entry
        if not write_stamp(Path(stamp_path), stamp):
            return ""
    if not parse_version(local) or not SAFE_NAME.fullmatch(name):
        return ""

    try:
        remote_text = fetch(REMOTE_TEMPLATE.format(name=name))
    except Exception:
        return ""
    remote = parse_frontmatter(remote_text or "").get("version") or ""
    if not parse_version(remote):
        return ""

    entry["checkedAt"] = format_time(now)
    entry["localVersion"] = local
    entry["remoteVersion"] = remote
    message = ""
    if compare_versions(remote, local) > 0:
        if entry.get("notifiedVersion") != remote:
            entry["notifiedVersion"] = remote
            message = NOTICE.format(remote=remote, local=local)
    else:
        entry.pop("notifiedVersion", None)
    stamp[name] = entry
    write_stamp(Path(stamp_path), stamp)
    return message


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if any(arg in {"-h", "--help"} for arg in args):
        print(
            "Check once a day for a newer published skill version. "
            "Prints one line, or nothing. Does not update the skill."
        )
        return 0
    try:
        text = run_check(
            skill_dir=Path(__file__).resolve().parent.parent,
            stamp_path=stamp_path(),
            now=datetime.now(timezone.utc),
            fetch=fetch_remote_text,
        )
    except Exception:
        return 0
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
