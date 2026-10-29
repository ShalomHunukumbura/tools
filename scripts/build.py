# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6", "jinja2>=3.1"]
# ///
"""Build the site into dist/ from tools.yaml, outputs/ and data/stats.json.

    uv run scripts/build.py

Also writes dist/tools.json, which the GitHub profile README is generated from.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SITE_URL = "https://shalomhunukumbura.github.io/tools/"
TERM_FOLD_LINES = 14  # longer outputs start folded, with a button to show the rest


# --- terminal output ------------------------------------------------------------

# Token classes, in priority order. Only what helps reading: rule IDs and redaction
# markers in the accent colour, failures in red, passes in the accent, labels faint.
_TOKENS = [
    ("code", r"\b(?:AG|LL)\d{3}\b"),
    ("mark", r"<(?:email|credential|phone|jwt|api-key|url-credentials)>"),
    ("bad", r"✗|\bNEW\b|\berror\b|\bfailed\b|\bfail(?:s)?\b(?= the run)"),
    ("ok", r"✓|\bpassed\b|\bAll clear\b"),
    ("strong", r"\bwarning\b"),
    ("label", r"^\s+(?:fix|message|template|first seen in|in \w+\(\)):"),
]
_TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKENS), re.MULTILINE)
_RULE_LINE = re.compile(r"^(=+) (.+?) (=+)$")


_PROGRESS_LINE = re.compile(r"^([.sFEx]+)\s{3,}(\[\s*\d+%\])$")


def tidy(line: str) -> str:
    """Shorten pytest's 80-column padding (===== rules, `..    [100%]`) so it doesn't
    force sideways scrolling in a narrow card. The text of the output is unchanged."""
    rule = _RULE_LINE.match(line)
    if rule:
        return f"=== {rule[2]} ==="
    return _PROGRESS_LINE.sub(r"\1  \2", line)


def highlight_line(line: str) -> str:
    line = tidy(line)
    rule = _RULE_LINE.match(line)
    if rule:  # pytest section header: ===== log-leak =====
        return f'<span class="t-faint">{html.escape(rule[1])} </span><span class="t-strong">{html.escape(rule[2])}</span><span class="t-faint"> {html.escape(rule[3])}</span>'
    out, pos = [], 0
    for m in _TOKEN_RE.finditer(line):
        out.append(html.escape(line[pos : m.start()]))
        out.append(f'<span class="t-{m.lastgroup}">{html.escape(m.group())}</span>')
        pos = m.end()
    out.append(html.escape(line[pos:]))
    return "".join(out)


def read_output(slug: str) -> dict | None:
    path = ROOT / "outputs" / f"{slug}.txt"
    if not path.exists():
        return None
    lines = path.read_text().rstrip("\n").split("\n")
    command: list[str] = []
    while lines and (lines[0].startswith("$ ") or (command and command[-1].endswith("\\"))):
        command.append(lines.pop(0))
    while lines and not lines[0].strip():
        lines.pop(0)
    return {
        "command": "\n".join(c.removeprefix("$ ") for c in command),
        "html": Markup("\n".join(highlight_line(line) for line in lines)),
        "folds": len(lines) > TERM_FOLD_LINES,
    }


# --- data -----------------------------------------------------------------------


def compact(n: int | None) -> str | None:
    if n is None:
        return None
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def load() -> dict:
    config = yaml.safe_load((ROOT / "tools.yaml").read_text())
    stats_path = ROOT / "data" / "stats.json"
    stats = json.loads(stats_path.read_text()) if stats_path.exists() else {"tools": {}}

    tools = []
    for order, tool in enumerate(config["tools"]):
        s = stats["tools"].get(tool["slug"], {})
        tools.append(
            {
                **tool,
                "order": order,
                "version": s.get("version"),
                "first_release": s.get("first_release", ""),
                "downloads": s.get("downloads_last_month"),
                "downloads_label": compact(s.get("downloads_last_month")),
                "stars": s.get("stars"),
                "output": read_output(tool["slug"]),
                "repo_url": f"https://github.com/{tool['repo']}" if tool.get("repo") else None,
                "pypi_url": f"https://pypi.org/project/{tool['pypi']}/" if tool.get("pypi") else None,
            }
        )

    live = [t for t in tools if t["status"] == "live"]
    # Newest release first; tools released the same day keep their tools.yaml order.
    live.sort(key=lambda t: t["order"])
    live.sort(key=lambda t: t["first_release"], reverse=True)
    upcoming = [t for t in tools if t["status"] != "live"]
    upcoming.sort(key=lambda t: (t["status"] != "building", t["order"]))

    downloads = [t["downloads"] for t in live if t["downloads"] is not None]
    stars = sum(t["stars"] or 0 for t in live)
    fetched = stats.get("fetched_at")
    updated = datetime.fromisoformat(fetched).date() if fetched else date.today()

    return {
        "owner": config["owner"],
        "live": live,
        "upcoming": upcoming,
        "categories": sorted({t["category"] for t in live}),
        "totals": {
            "live": len(live),
            "pypi": sum(1 for t in live if t.get("pypi")),
            "downloads": compact(sum(downloads)) if downloads else None,
            "stars": stars,
        },
        "updated": f"{updated.day} {updated:%b %Y}",
        "site_url": SITE_URL,
    }


# --- render ---------------------------------------------------------------------


def icon(name: str, label: str | None = None) -> Markup:
    """Inline a Phosphor icon (vendored in static/icons), sized by CSS."""
    svg = (ROOT / "static" / "icons" / f"{name}.svg").read_text().strip()
    attrs = f'class="icon" aria-label="{html.escape(label)}" role="img"' if label else 'class="icon" aria-hidden="true"'
    return Markup(svg.replace("<svg ", f"<svg {attrs} ", 1))


def main() -> None:
    data = load()
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["icon"] = icon

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST / "static", ignore=shutil.ignore_patterns("icons"))
    (DIST / "index.html").write_text(env.get_template("index.html.j2").render(**data))
    (DIST / ".nojekyll").write_text("")

    feed = [
        {
            "name": t["name"],
            "tagline": t["tagline"],
            "kind": t["kind"],
            "category": t["category"],
            "install": t["install"],
            "repo": t["repo_url"],
            "pypi": t["pypi_url"],
            "version": t["version"],
            "downloads_last_month": t["downloads"],
            "stars": t["stars"],
        }
        for t in data["live"]
    ]
    upcoming = [{"name": t["name"], "status": t["status"], "tagline": t["tagline"]} for t in data["upcoming"]]
    (DIST / "tools.json").write_text(
        json.dumps({"site": SITE_URL, "tools": feed, "upcoming": upcoming}, indent=2, ensure_ascii=False) + "\n"
    )
    print(f"built {DIST.relative_to(ROOT)}/ with {len(feed)} live tools")


if __name__ == "__main__":
    main()
