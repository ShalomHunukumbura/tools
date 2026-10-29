# tools

The source for [shalomhunukumbura.github.io/tools](https://shalomhunukumbura.github.io/tools/):
every developer tool I've released, with real output from each one, and live numbers from
PyPI and GitHub.

## Add a tool

1. Add an entry to [`tools.yaml`](tools.yaml).
2. Save a real run of it as `outputs/<slug>.txt`. The first line is the command, starting
   with `$ `.
3. Push. The site rebuilds and deploys, and the tools section of my GitHub profile picks
   it up on its next daily run.

## Build locally

```bash
uv run scripts/fetch_stats.py   # live numbers into data/stats.json (optional)
uv run scripts/build.py         # the site into dist/
python3 -m http.server -d dist
```

The site also publishes [`tools.json`](https://shalomhunukumbura.github.io/tools/tools.json),
which the profile README is generated from.

## Credits

[Geist](https://vercel.com/font) fonts (SIL Open Font License, see
`static/fonts/LICENSE-geist.txt`) and [Phosphor](https://phosphoricons.com) icons (MIT).
