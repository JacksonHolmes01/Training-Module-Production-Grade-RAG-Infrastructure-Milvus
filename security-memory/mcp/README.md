# Optional: MCP Integration for Automatic Memory Retrieval

This directory contains configuration examples for connecting the
`/memory/query` endpoint to IDE tools via the **Model Context Protocol (MCP)**.

MCP allows Cursor and other MCP-compatible IDEs to call your memory API
automatically in the background whenever you ask a security-related question,
eliminating the manual curl + paste step from the main workflow.

---

## What MCP does

Without MCP: you run curl manually, copy chunks, paste them into the IDE chat.

With MCP: the IDE calls `/memory/query` automatically, retrieves the chunks,
and injects them into the prompt before sending it to the AI. No manual steps.

---

## Cursor MCP configuration

Add this to your `~/.cursor/mcp.json` or `.cursor/mcp.json` in the repo root:

```json
{
  "mcpServers": {
    "security-memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"],
      "env": {
        "FETCH_BASE_URL": "http://localhost:8088",
        "FETCH_HEADERS": "{\"X-API-Key\": \"YOUR_EDGE_API_KEY_HERE\"}"
      }
    }
  }
}
```

Replace `YOUR_EDGE_API_KEY_HERE` with the value from your `.env` file.

---

## Testing MCP connectivity

Once configured, open Cursor and type:

```
Use the security memory to review my Dockerfile for CIS Docker Benchmark issues.
```

Cursor should automatically call `/memory/query` and use the retrieved chunks
in its response.

---

## Note

This is an advanced optional workflow. The manual curl approach in Lessons 4.2
and 4.3 achieves the same learning goal and is more transparent about what is
happening. Start with the manual workflow and add MCP once you are comfortable
with the concepts.
