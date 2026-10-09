# Marketing Agent (Claude + Firecrawl)

An AI marketing strategist that researches the live web before it answers.
Claude handles the strategy and writing. [Firecrawl](https://firecrawl.dev) searches the web and reads websites.

## What it can do

- Competitor research: positioning, pricing, offers, messaging
- Landing-page and SEO audits of any URL
- Content ideas grounded in what's ranking right now
- Ad, email and landing-page copy
- Go-to-market plans, saved as Markdown reports in `reports/`

## Tools the agent uses

| Tool | What it does |
|---|---|
| `search_web` | Firecrawl search: top results for a query |
| `scrape_page` | Reads one page as clean Markdown |
| `map_site` | Lists a site's URLs (finds pricing, blog and feature pages) |
| `crawl_site` | Reads several pages of one site at once |
| `save_report` | Saves a finished deliverable to `reports/` |

## Files

- `marketing_agent.py`: the agent (tools, prompt, Claude loop) and the command-line chat
- `web_app.py`: the web server (FastAPI)
- `static/index.html`: the web page; `static/vendor/` holds the Markdown libraries so it works offline

## Setup

You need Python 3.10 or newer (check with `python3 --version`). The Python that comes with macOS
is 3.9, which is too old: `pip` then fails with "No matching distribution found for anthropic".
Install a current Python from https://www.python.org/downloads/ first.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your keys
```

You need:
- An Anthropic API key: https://console.anthropic.com
- A Firecrawl API key: https://firecrawl.dev

## Run it

### Web interface

```bash
uvicorn web_app:app --reload
```

Then open http://127.0.0.1:8000. You get a chat window that shows what the agent is
searching and reading as it works, starter prompts, and a sidebar with every saved report
(click one to read it or download it).

Conversations are kept in memory, so they reset when you restart the server.
The app has no login, so run it on your own computer and don't expose it to the internet.

### Command line

Interactive chat:

```bash
python marketing_agent.py
```

One-off task:

```bash
python marketing_agent.py "Compare the pricing pages of notion.so and coda.io and suggest how a new competitor should position itself. Save it as a report."
```

## Example prompts

- "Audit the homepage messaging of https://example.com and rewrite the hero section three ways."
- "Find the top 5 competitors for an AI bookkeeping app for freelancers and summarize their positioning."
- "Give me 10 blog post ideas for a vegan meal-kit brand based on what's ranking now."
- "Write a 3-email launch sequence for our new product, based on our site https://example.com."

Firecrawl credits: `crawl_site` uses one credit per page, so the agent caps crawls at 15 pages.
