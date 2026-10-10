# Project notes: where we left off

Last updated: 2026-10-10

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
- **Setup files:** `requirements.txt`, `.env.example`, `.gitignore`, `README.md`. The README
  says Python 3.10 or newer is required.

## Where the code is

- Repo: `jmgdl62/AGENTIC-AI`
- `main`: the first version, the command-line agent only.
- `claude/vibrant-ptolemy-t35mqv`: everything (web interface, prompt caching, these notes).
  **Pull request [jmgdl62/AGENTIC-AI#2](https://github.com/jmgdl62/AGENTIC-AI/pull/2)** merges
  it into `main`. It's open, has no conflicts and no review comments, and is ready to merge.
- `claude/session-context-om2jif`: an older copy from the Oct 7 session. It's redundant: delete
  it once `main` is the default branch.

## Running it on the Mac (Mac Studio, user `chemagil`)

Progress so far, in `~/AGENTIC-AI`:

1. Both keys are in `.env`.
2. The Python that comes with macOS (3.9) was too old: `pip` failed with "No matching
   distribution found for anthropic>=1.11.0". Fix: install Python 3.10+ from
   https://www.python.org/downloads/, then recreate the virtual environment:
   ```bash
   cd ~/AGENTIC-AI
   rm -rf .venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   uvicorn web_app:app --reload     # then open http://127.0.0.1:8000
   ```
3. **Current blocker:** the web app runs, but Claude returns
   `401 authentication_error: invalid x-api-key`. Likely causes, in order:
   - The key isn't a Claude API key. It must come from https://console.anthropic.com → API Keys,
     start with `sk-ant-api`, and the account needs credits under Billing. A Claude.ai Pro or Max
     subscription (including the "Chema DLmax" account) does **not** include API access.
   - The `.env` line is malformed. It must be `ANTHROPIC_API_KEY=sk-ant-api...`: no quotes, no
     spaces, one line.
   - An old `ANTHROPIC_API_KEY` set in the Terminal overrides `.env`.

   Check without revealing the key:
   ```bash
   echo "Terminal: ${ANTHROPIC_API_KEY:0:10}"     # if anything prints, run: unset ANTHROPIC_API_KEY
   grep ANTHROPIC .env | cut -c1-28              # should start with ANTHROPIC_API_KEY=sk-ant-api
   ```

Each time after that, either start it by hand:
```bash
cd ~/AGENTIC-AI
source .venv/bin/activate
uvicorn web_app:app --reload
```
or have it start by itself at every login (`scripts/mac_autostart.sh`, added 2026-10-10, not yet
tried on a real Mac):
```bash
cd ~/AGENTIC-AI
bash scripts/mac_autostart.sh install    # also: status, restart, uninstall
```

## What hasn't been tested

- No real call to Claude or Firecrawl has succeeded yet (the 401 above). Everything was tested
  against a fake Claude API only.
- First real test once the key works: run
  `SHOW_CACHE_STATS=1 python marketing_agent.py "Find 3 competitors of notion.so"`. Check that
  the web tools return real results and that, from the second step on, most tokens show as
  "cached".

## Open to-dos

- **Fix the 401** (above), then do the first real test.
- **Merge [jmgdl62/AGENTIC-AI#2](https://github.com/jmgdl62/AGENTIC-AI/pull/2)** once you're
  happy with it.
- **Default branch:** make `main` the default on GitHub (repo Settings → General → Default
  branch). This needs a desktop browser and admin rights on the repo. An earlier attempt failed
  for a reason we didn't pin down. After that, delete `claude/session-context-om2jif`.
- **Unrelated:** your profile mentions unpublishing `chefAi_agent.html`. That file isn't in this
  repo; it's probably a published artifact or lives in another repo.

## Ideas for later

- Add a login before putting the web app online. It has no authentication right now.
- Save chats so they survive a server restart. They're kept in memory now and lost on restart.
- Other possible additions: brand-voice settings, exporting reports to PDF or Google Docs,
  scheduled competitor monitoring.

## How to pick up again

Start a new Claude Code session on `jmgdl62/AGENTIC-AI` and say:
"Read PROJECT_NOTES.md on branch claude/vibrant-ptolemy-t35mqv and continue the marketing agent."
