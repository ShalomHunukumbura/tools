# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Fetch live numbers for every released tool and write them to data/stats.json.

PyPI gives the version and release dates, pypistats.org the downloads in the last 30
days, GitHub the stars. A source that fails is skipped: the site shows what it has.

    uv run scripts/fetch_stats.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def get_json(url: str) -> dict | None:
    headers = {"User-Agent": "shalom-tools-site", "Accept": "application/json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
            return json.load(r)
    except Exception as exc:  # network, HTTP error, bad JSON: skip this number
        print(f"  skipped {url}: {exc}", file=sys.stderr)
        return None


def pypi_stats(package: str) -> dict:
    stats: dict = {}
    data = get_json(f"https://pypi.org/pypi/{package}/json")
    if data:
        stats["version"] = data["info"]["version"]
        uploads = sorted(files[0]["upload_time"] for files in data["releases"].values() if files)
        if uploads:
            stats["first_release"] = uploads[0][:10]
            stats["latest_release"] = uploads[-1][:10]
    downloads = get_json(f"https://pypistats.org/api/packages/{package}/recent")
    if downloads:
        stats["downloads_last_month"] = downloads["data"]["last_month"]
    return stats


def main() -> None:
    config = yaml.safe_load((ROOT / "tools.yaml").read_text())
    result: dict = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tools": {}}
    for tool in config["tools"]:
        if tool["status"] != "live":
            continue
        print(f"{tool['slug']}:")
        stats = pypi_stats(tool["pypi"]) if tool.get("pypi") else {}
        if tool.get("repo"):
            repo = get_json(f"https://api.github.com/repos/{tool['repo']}")
            if repo:
                stats["stars"] = repo["stargazers_count"]
        print(f"  {stats}")
        result["tools"][tool["slug"]] = stats

    out = ROOT / "data" / "stats.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
