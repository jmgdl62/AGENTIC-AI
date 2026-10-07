"""Web interface for the marketing agent.

Run:
    uvicorn web_app:app --reload
Then open http://127.0.0.1:8000
"""

import json
import queue
import threading
import uuid
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from marketing_agent import REPORTS_DIR, run_turn

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Marketing Agent")

# Conversations live in memory: they reset when the server restarts.
sessions: dict[str, list] = {}
session_locks: dict[str, threading.Lock] = {}


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat")
def chat(req: ChatRequest):
    text = req.message.strip()
    if not text:
        raise HTTPException(400, "Message is empty.")

    session_id = req.session_id if req.session_id in sessions else str(uuid.uuid4())
    messages = sessions.setdefault(session_id, [])
    lock = session_locks.setdefault(session_id, threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "The agent is still working on your last message.")

    events: queue.Queue = queue.Queue()

    def worker() -> None:
        start = len(messages)
        messages.append({"role": "user", "content": text})
        try:
            run_turn(messages, on_event=lambda kind, data: events.put((kind, data)))
        except anthropic.RateLimitError:
            del messages[start:]
            events.put(("error", {"message": "Rate limited by the Claude API. Wait a moment and try again."}))
        except anthropic.APIStatusError as e:
            del messages[start:]
            events.put(("error", {"message": f"Claude API error {e.status_code}: {e.message}"}))
        except anthropic.APIConnectionError:
            del messages[start:]
            events.put(("error", {"message": "Could not reach the Claude API."}))
        except Exception as e:
            del messages[start:]
            events.put(("error", {"message": f"Unexpected error: {e}"}))
        finally:
            lock.release()
            events.put(("done", {}))

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        yield _sse("session", {"session_id": session_id})
        while True:
            kind, data = events.get()
            if kind == "tool":
                data = {"name": data["name"], "input": {k: v for k, v in data["input"].items() if k != "markdown"}}
            yield _sse(kind, data)
            if kind == "done":
                break

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/reset")
def reset(req: ChatRequest):
    sessions.pop(req.session_id or "", None)
    return {"ok": True}


@app.get("/api/reports")
def list_reports():
    if not REPORTS_DIR.exists():
        return []
    files = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": f.name, "size": f.stat().st_size} for f in files]


@app.get("/api/reports/{name}")
def get_report(name: str, download: bool = False):
    path = (REPORTS_DIR / name).resolve()
    if path.parent != REPORTS_DIR.resolve() or path.suffix != ".md" or not path.is_file():
        raise HTTPException(404, "Report not found.")
    if download:
        return FileResponse(path, media_type="text/markdown", filename=name)
    return {"name": name, "markdown": path.read_text(encoding="utf-8")}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
