"""
gradio-ui/app.py — Chat UI for the Milvus RAG lab.

Connects to the NGINX edge proxy, forwards the API key, and displays
answers with source citations from Milvus.
"""

import os
import httpx
import gradio as gr

API_BASE_URL = os.getenv("API_BASE_URL", "http://edge-nginx:8088").rstrip("/")
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")

def _timeout_s(default: float = 600.0) -> float:
    raw = (os.getenv("GRADIO_HTTP_TIMEOUT_S") or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default

HTTP_TIMEOUT_S = _timeout_s()


def call_api(path: str, payload: dict) -> dict:
    if not EDGE_API_KEY:
        return {"error": "EDGE_API_KEY is not set for the UI container."}
    headers = {"X-API-Key": EDGE_API_KEY}
    timeout = httpx.Timeout(
        timeout=HTTP_TIMEOUT_S,
        connect=30.0,
        read=HTTP_TIMEOUT_S,
        write=30.0,
        pool=30.0,
    )
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{API_BASE_URL}{path}", json=payload, headers=headers)
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        return {
            "error": (
                f"Request timed out after {HTTP_TIMEOUT_S}s. "
                "Try increasing GRADIO_HTTP_TIMEOUT_S in your .env and rebuilding gradio-ui."
            )
        }
    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = e.response.text
        except Exception:
            pass
        return {"error": f"HTTP {e.response.status_code} from API: {body or str(e)}"}
    except Exception as e:
        return {"error": f"UI -> API call failed: {type(e).__name__}: {e}"}


def chat_fn(message: str, history: list) -> str:
    data = call_api("/chat", {"message": message})
    if "error" in data:
        return f"⚠️ Error: {data['error']}"

    answer  = (data.get("answer") or "").strip()
    sources = data.get("sources") or []

    if sources:
        answer += "\n\n---\n**Sources (retrieved from Milvus):**\n"
        for i, s in enumerate(sources, start=1):
            title = s.get("title") or "Untitled"
            url   = s.get("url")   or ""
            score = s.get("distance") or s.get("score") or ""
            score_str = f" (score={round(float(score), 3)})" if score else ""
            link  = f" — {url}" if url else ""
            answer += f"{i}. {title}{link}{score_str}\n"

    return answer


def health_text() -> str:
    if not EDGE_API_KEY:
        return "UI misconfigured: EDGE_API_KEY is missing."
    headers = {"X-API-Key": EDGE_API_KEY}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE_URL}/health", headers=headers)
            return f"HTTP {r.status_code}:\n{r.text}"
    except Exception as e:
        return f"Health check failed: {type(e).__name__}: {e}"


with gr.Blocks(title="Milvus RAG Lab — Chat UI") as demo:
    gr.Markdown(
        "# Production RAG Lab — Chat with Your Dataset\n"
        "This UI uses:\n"
        "- **Milvus** for vector storage and similarity search\n"
        "- **Ollama** for local LLM inference and embeddings\n"
        "- **NGINX** as an authenticated API gateway\n\n"
        f"*UI timeout: {HTTP_TIMEOUT_S}s — set via `GRADIO_HTTP_TIMEOUT_S` in `.env`*"
    )
    with gr.Row():
        with gr.Column(scale=2):
            gr.ChatInterface(chat_fn)
        with gr.Column(scale=1):
            gr.Markdown("## System status")
            btn = gr.Button("Refresh /health")
            out = gr.Textbox(label="API health output", lines=10)
            btn.click(fn=health_text, outputs=out)

demo.launch(server_name="0.0.0.0", server_port=7860)
