# NotebookLM MCP CLI Guide for AI Agents

This guide provides instructions on how to use the `notebooklm-mcp-cli` (`nlm`) within this project. The CLI allows you to interact with Google NotebookLM directly from your terminal, enabling research, source ingestion, and content generation.

## 🚀 Getting Started

### Authentication
The user has already logged in and authenticated. If you encounter authentication errors, ask the user to run:
```bash
nlm login
```

### Common Flags
- `--json`: Output structured data (ideal for parsing).
- `--quiet`: Output only IDs (useful for piping).
- `--confirm`: Automatically confirm prompts (use for all generation/deletion commands).

---

## 📚 Notebook Management

Notebooks are the primary containers for your research.

| Action | Command |
|--------|---------|
| List Notebooks | `nlm notebook list` |
| Create Notebook | `nlm notebook create "Title"` |
| Get Details | `nlm notebook get <id>` |
| Delete Notebook | `nlm notebook delete <id> --confirm` |

---

## 📎 Source Management

Sources are the documents, URLs, or text snippets you add to a notebook.

### Adding Sources
| Type | Command |
|------|---------|
| URL | `nlm source add <notebook-id> --url "https://..."` |
| Local File | `nlm source add <notebook-id> --file "path/to/doc.pdf"` |
| Raw Text | `nlm source add <notebook-id> --text "Your text here" --title "Note Title"` |
| Google Drive | `nlm source add <notebook-id> --drive-id "ID"` |

### Managing Sources
- **List Sources:** `nlm source list <notebook-id>`
- **Check Status:** `nlm source status <notebook-id>` (Useful to see if processing is finished)
- **Sync Drive Sources:** `nlm source sync <notebook-id>`

---

## 💬 Querying & Chat

Use queries to extract information from your notebook sources.

### One-Shot Q&A
```bash
nlm notebook query <notebook-id> "Your question here"
```

> [!IMPORTANT]
> **Do not use `nlm chat start`.** This opens an interactive REPL which is difficult for agents to control. Always use `nlm notebook query` or `nlm query notebook` for one-shot interactions.

---

## 🔍 Deep Research

The CLI can perform autonomous research and add findings to your notebooks.

1. **Start Research:**
   ```bash
   nlm research start "topic" --notebook-id <id> --mode deep
   ```
2. **Check Status:**
   ```bash
   nlm research status <notebook-id>
   ```
3. **Import Findings:**
   ```bash
   nlm research import <notebook-id> <task-id>
   ```

---

## 🎨 Artifact Generation (Studio)

NotebookLM can generate various artifacts based on your sources.

| Artifact Type | Command |
|---------------|---------|
| Audio Overview | `nlm audio create <notebook-id> --confirm` |
| Study Guide | `nlm report create <notebook-id> --format "Study Guide" --confirm` |
| Quiz | `nlm quiz create <notebook-id> --count 10 --confirm` |
| Flashcards | `nlm flashcards create <notebook-id> --confirm` |
| Mind Map | `nlm mindmap create <notebook-id> --confirm` |

### Downloading Artifacts
1. Check status and get Artifact ID: `nlm studio status <notebook-id>`
2. Download: `nlm download <type> <notebook-id> <artifact-id> --output "path/to/file"`

---

## 🛠️ Agent Integration (MCP)

You can integrate this CLI as an MCP server for AI tools like Antigravity.

### MCP Setup
To list supported tools:
```bash
nlm setup list
```

To add the MCP server to Antigravity:
```bash
nlm setup add Antigravity
```

### Skills
Install the NotebookLM skill for specific tools:
```bash
nlm skill install Antigravity
```

---

## 💡 Best Practices for Agents

1. **Capture IDs:** Many commands return IDs. Always capture these to use in subsequent commands.
2. **Use Aliases:** If working with a notebook frequently, set an alias:
   ```bash
   nlm alias set my_project <notebook-id>
   ```
3. **Wait for Processing:** After adding sources or starting research, wait for the status to be "ready" before querying.
4. **Safety First:** Always ask for user confirmation before deleting notebooks or sources.
5. **Token Efficiency:** Prefer `nlm notebook list` (compact) over `nlm notebook list --json` unless you specifically need to parse the JSON.
