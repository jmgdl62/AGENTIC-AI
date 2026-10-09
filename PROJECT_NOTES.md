# Project notes: where we left off

Last updated: 2026-10-07

## What this project is

A marketing agent: Claude does the marketing strategy and writing, and Firecrawl reads the web
(search, scrape, map, crawl). You can use it from the command line or from a web page.

## What's done

- **Agent** (`marketing_agent.py`): Claude (`claude-opus-5-5`) with five tools: `search_web`,
  `scrape_page`, `map_site`, `crawl_site` (capped at 15 pages) and `save_report` (writes Markdown
  to `reports/`). Pages longer than about 20,000 characters are cut off. If Claude declines a
  request, the API retries it on a fallback model (`fallbacks="default"`).
- **Prompt caching:** the tools and system prompt have a 1-hour cache breakpoint, and the
  conversation uses automatic caching (5 minutes). Run with `SHOW_CACHE_STATS=1` to see cached
  vs. uncached tokens per step. Tested only against a fake API so far.
- **Command line:** `python marketing_agent.py` to chat, or `python marketing_agent.py "task"`
  for a single task.
- **Web interface** (`web_app.py` + `static/index.html`): a FastAPI server. The chat page shows
  live progress, has starter prompts, and has a sidebar of saved reports you can view and
  download. It works on phones and in dark mode. The Markdown libraries are bundled in
  `static/vendor/`, so the page works without loading anything from the internet.
- **Setup files:** `requirements.txt`, `.env.example`, `.gitignore`, `README.md`.

## How it was tested

- No real API keys were available, so neither Claude nor Firecrawl has been called for real.
- The Claude side was tested against a fake API: the tool loop, report saving, the progress
  stream and the web page all worked, on desktop and on phone.
- **Not tested yet:** the Firecrawl tools against the real Firecrawl service. Do this first
  once you have keys.

## Where the code is

- Repo: `jmgdl62/AGENTIC-AI`
- Branch: `claude/session-context-om2jif`. This is the only branch, and GitHub currently treats
  it as the default.
- There is no `main` branch, so **no pull request has been opened**.

## Open decision: pull request

A pull request needs a branch to merge into. Choose one:

1. **Make `main` the command-line agent.** Create `main` at the first commit ("Add
   Firecrawl-powered marketing agent"). The PR then contains only the web interface. Nothing is
   rewritten.
2. **Rewrite the history.** Create an empty `main` and rebuild this branch on top of it with a
   force-push. The PR then contains everything. This step was blocked as destructive and needs
   your approval.
3. **Skip the PR.** Keep working on this branch as it is.

Afterwards, make `main` the default branch on GitHub under Settings → General.

## Ideas for next steps

- Add real keys to `.env` and do a full test run (see "How it was tested").
- Add a login before putting the web app online. It has no authentication right now.
- Save chats so they survive a server restart. They're kept in memory now and lost on restart.
- Other possible additions: brand-voice settings, exporting reports to PDF or Google Docs,
  scheduled competitor monitoring.

## How to pick up again

Start a new session on this repo and say something like:
"Read PROJECT_NOTES.md and continue the marketing agent."

To run it locally:

```bash
pip install -r requirements.txt
cp .env.example .env               # add ANTHROPIC_API_KEY and FIRECRAWL_API_KEY
uvicorn web_app:app --reload       # then open http://127.0.0.1:8000
```
