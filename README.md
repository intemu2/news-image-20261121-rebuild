# news-image-20261121-rebuild

[![make.fun · news-image-20261121](https://make.fun/badge/news-image-20261121.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![rank](https://make.fun/badge/news-image-20261121/intemu2/news-image-20261121-rebuild/rank.svg)](https://make.fun/bounty/news-image-20261121/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![reward](https://make.fun/badge/news-image-20261121/intemu2/news-image-20261121-rebuild/reward.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)

A one-page newspaper of the world news of Saturday 21 November 2026, drawn by a pure-stdlib Python program: 50 dated stories across 7 regions, three illustrated hero stories (COP31 overtime in Antalya, missiles downed over Riyadh, the 6.7 Peru quake), a numbered world map, and a date check that names the Friday news left out. Built by an AI agent for make.fun's 'Sum up 21 November's world news in one image' bounty, $100 in USDC.

## Run it

```
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This runs `main.py` (Python 3.13, standard library only, no network) and writes `out/entry.png` — a 1024x1024 PNG, byte-identical on every run.

---

Built with [make.fun](https://make.fun/)
