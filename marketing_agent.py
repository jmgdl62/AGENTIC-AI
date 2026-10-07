"""Marketing agent: Claude does the marketing thinking, Firecrawl reads the web.

Usage:
    python marketing_agent.py                      # interactive chat
    python marketing_agent.py "Audit stripe.com's landing page messaging"
"""

import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Callable

import anthropic
from anthropic import beta_tool
from dotenv import load_dotenv
from firecrawl import Firecrawl

load_dotenv()

MODEL = "claude-opus-5-5"
MAX_PAGE_CHARS = 20_000  # keep a single scraped page from flooding the context
REPORTS_DIR = Path(__file__).parent / "reports"

SYSTEM_PROMPT = """You are a senior marketing strategist with live web access through Firecrawl.

You help with competitor research, positioning and messaging, landing-page and SEO audits,
content ideas, ad and email copy, and go-to-market plans.

How to work:
- Ground claims in what you actually read. Use search_web to find sources, map_site to see a
  site's structure, scrape_page to read specific pages, and crawl_site when you need several
  pages from one site at once (it is slower and costs more Firecrawl credits).
- Cite the URLs you relied on.
- Be concrete: quote real headlines, name real offers and prices, and give copy the user can
  ship, not generic advice.
- When the user asks for a deliverable (report, plan, copy deck), write it in Markdown and save
  it with save_report, then tell them the file path."""

firecrawl = Firecrawl(api_key=os.environ.get("FIRECRAWL_API_KEY"))
client = anthropic.Anthropic()


def _clip(text: str, limit: int = MAX_PAGE_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[... clipped, {len(text) - limit} more characters not shown]"


@beta_tool
def search_web(query: str, limit: int = 5) -> str:
    """Search the web and return the top results (title, URL, snippet).

    Args:
        query: What to search for, e.g. "best project management tools for agencies 2026".
        limit: Number of results to return, 1-10.
    """
    try:
        results = firecrawl.search(query, limit=max(1, min(limit, 10)))
    except Exception as e:
        return f"Search failed: {e}"
    items = results.web or []
    if not items:
        return "No results."
    return "\n\n".join(
        f"{i}. {getattr(r, 'title', '') or '(no title)'}\n   {r.url}\n   {getattr(r, 'description', '') or ''}"
        for i, r in enumerate(items, 1)
    )


@beta_tool
def scrape_page(url: str) -> str:
    """Read one web page and return its main content as Markdown, plus title and meta description.

    Args:
        url: Full URL of the page, including https://.
    """
    try:
        doc = firecrawl.scrape(url, formats=["markdown"], only_main_content=True)
    except Exception as e:
        return f"Scrape failed for {url}: {e}"
    meta = doc.metadata
    header = (
        f"URL: {url}\n"
        f"Title: {getattr(meta, 'title', '') or ''}\n"
        f"Meta description: {getattr(meta, 'description', '') or ''}\n\n"
    )
    return header + _clip(doc.markdown or "(no text content)")


@beta_tool
def map_site(url: str, search: str = "", limit: int = 50) -> str:
    """List the URLs on a website, useful for finding pricing, features, blog or about pages.

    Args:
        url: The site's root URL, e.g. https://example.com.
        search: Optional keyword to filter URLs, e.g. "pricing" or "blog".
        limit: Maximum number of URLs to return, 1-200.
    """
    try:
        result = firecrawl.map(url, search=search or None, limit=max(1, min(limit, 200)))
    except Exception as e:
        return f"Map failed for {url}: {e}"
    links = result.links or []
    if not links:
        return "No URLs found."
    return "\n".join(
        f"- {link.url}" + (f"  ({link.title})" if getattr(link, "title", None) else "")
        for link in links
    )


@beta_tool
def crawl_site(url: str, limit: int = 5, include_paths: str = "") -> str:
    """Crawl several pages of one website and return each page's Markdown. Slower than scrape_page.

    Args:
        url: Starting URL, e.g. https://example.com/blog.
        limit: Maximum pages to crawl, 1-15.
        include_paths: Optional comma-separated path patterns to stay within, e.g. "/blog/.*,/guides/.*".
    """
    paths = [p.strip() for p in include_paths.split(",") if p.strip()] or None
    try:
        job = firecrawl.crawl(
            url,
            limit=max(1, min(limit, 15)),
            include_paths=paths,
            formats=["markdown"],
            only_main_content=True,
            timeout=180,
        )
    except Exception as e:
        return f"Crawl failed for {url}: {e}"
    pages = job.data or []
    if not pages:
        return f"Crawl finished with status '{job.status}' but returned no pages."
    per_page = MAX_PAGE_CHARS // max(1, len(pages)) + 2_000
    parts = []
    for doc in pages:
        page_url = getattr(doc.metadata, "source_url", None) or getattr(doc.metadata, "url", "") or ""
        title = getattr(doc.metadata, "title", "") or ""
        parts.append(f"## {title}\nURL: {page_url}\n\n{_clip(doc.markdown or '', per_page)}")
    return f"Crawled {len(pages)} pages.\n\n" + "\n\n---\n\n".join(parts)


@beta_tool
def save_report(title: str, markdown: str) -> str:
    """Save a finished deliverable (report, plan, copy deck) as a Markdown file.

    Args:
        title: Short title used for the filename, e.g. "Acme competitor analysis".
        markdown: The full document in Markdown.
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "report"
    path = REPORTS_DIR / f"{date.today().isoformat()}-{slug}.md"
    path.write_text(markdown, encoding="utf-8")
    return f"Saved to {path}"


TOOLS = [search_web, scrape_page, map_site, crawl_site, save_report]


def _print_event(kind: str, data: dict) -> None:
    if kind == "tool":
        args = ", ".join(f"{k}={str(v)[:60]!r}" for k, v in data["input"].items() if k != "markdown")
        print(f"  -> {data['name']}({args})", flush=True)
    elif kind == "text":
        print(f"\n{data['text']}\n")
    elif kind == "refusal":
        print("\n[The request was declined. Try rephrasing it.]\n")


def run_turn(messages: list, on_event: Callable[[str, dict], None] = _print_event) -> None:
    """Run one user turn through the tool runner, appending everything to `messages`.

    Progress is reported through `on_event(kind, data)`, where kind is "tool", "text" or "refusal".
    """
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        # If a request is declined by a safety classifier, let the API retry it on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    for message in runner:
        # The runner keeps its own history, so mirror it here to carry context across turns.
        messages.append({"role": "assistant", "content": message.content})
        for block in message.content:
            if block.type == "tool_use":
                on_event("tool", {"name": block.name, "input": dict(block.input)})
            elif block.type == "text" and message.stop_reason != "tool_use":
                on_event("text", {"text": block.text})
        if message.stop_reason == "refusal":
            on_event("refusal", {})
        tool_response = runner.generate_tool_call_response()  # cached, so tools still run once
        if tool_response is not None:
            messages.append(tool_response)


def main() -> None:
    if not os.environ.get("FIRECRAWL_API_KEY"):
        sys.exit("Set FIRECRAWL_API_KEY (see .env.example).")

    messages: list = []
    if len(sys.argv) > 1:
        messages.append({"role": "user", "content": " ".join(sys.argv[1:])})
        run_turn(messages)
        return

    print("Marketing agent ready. Ask for competitor research, audits, copy, plans... (Ctrl+C to quit)\n")
    while True:
        try:
            prompt = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not prompt:
            continue
        start = len(messages)
        messages.append({"role": "user", "content": prompt})
        try:
            run_turn(messages)
        except anthropic.RateLimitError:
            print("\n[Rate limited by the Claude API. Wait a moment and try again.]\n")
            del messages[start:]
        except anthropic.APIStatusError as e:
            print(f"\n[Claude API error {e.status_code}: {e.message}]\n")
            del messages[start:]
        except anthropic.APIConnectionError:
            print("\n[Could not reach the Claude API. Check your connection.]\n")
            del messages[start:]


if __name__ == "__main__":
    main()
