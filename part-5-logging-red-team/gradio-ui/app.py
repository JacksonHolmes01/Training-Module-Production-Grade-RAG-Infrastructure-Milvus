"""
gradio-ui/app.py: browser chat UI for the Milvus RAG lab.

The UI talks only to NGINX (never directly to the API or the database)
and sends the API key server-side. The key never reaches the browser.
"""

import os

import gradio as gr
import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://nginx:8088").rstrip("/")
def _read_key() -> str:
    path = os.getenv("EDGE_API_KEY_FILE", "")
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv("EDGE_API_KEY", "")


EDGE_API_KEY = _read_key()
HTTP_TIMEOUT_S = float(os.getenv("GRADIO_HTTP_TIMEOUT_S", "600") or 600)


def _headers() -> dict:
    return {"X-API-Key": EDGE_API_KEY}


def chat_fn(message: str, history: list) -> str:
    if not EDGE_API_KEY:
        return "UI misconfigured: EDGE_API_KEY is missing."
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT_S) as client:
            r = client.post(f"{API_BASE_URL}/chat", json={"message": message}, headers=_headers())
        if r.status_code != 200:
            return f"Error: HTTP {r.status_code} from API: {r.text[:300]}"
        data = r.json()
    except httpx.TimeoutException:
        return f"Request timed out after {HTTP_TIMEOUT_S:.0f}s. The model may still be loading; try again."
    except Exception as e:
        return f"UI could not reach the API: {type(e).__name__}"

    answer = (data.get("answer") or "").strip()
    sources = data.get("sources") or []
    if sources:
        answer += "\n\n---\n**Sources (retrieved from Milvus):**\n"
        for i, s in enumerate(sources, start=1):
            sim = 1 - float(s.get("distance", 1))
            answer += f"{i}. {s.get('title') or 'Untitled'} (similarity {sim:.2f})\n"
    return answer


def health_text() -> str:
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE_URL}/health", headers=_headers())
        return f"HTTP {r.status_code}\n{r.text}"
    except Exception as e:
        return f"Health check failed: {type(e).__name__}"


with gr.Blocks(title="Secure AI Lab: Milvus RAG") as demo:
    gr.Markdown(
        "# Secure AI Lab: Chat with Your Dataset\n"
        "- **Milvus** stores documents and runs similarity search\n"
        "- **Ollama** runs the local LLM and embedding model\n"
        "- **NGINX** requires an API key for every request\n"
    )
    with gr.Row():
        with gr.Column(scale=2):
            gr.ChatInterface(chat_fn, type="messages")
        with gr.Column(scale=1):
            gr.Markdown("## System status")
            btn = gr.Button("Refresh /health")
            out = gr.Textbox(label="API health", lines=10)
            btn.click(fn=health_text, outputs=out)

demo.launch(server_name="0.0.0.0", server_port=7860, show_api=False)
