# MySQL Context Agent (Streamlit MVP)

This project builds a fully autonomous AI agent that crawls a target MySQL database, constructs a robust vector-embedded catalog natively in MySQL, profiles columns for PHI using NLP, and securely translates natural human language into zero-shot SQL aggregations on a Streamlit dashboard.

All AI logic runs **100% locally** using Ollama (Llama 3.1 8b & Nomic Embeddings), providing high privacy guarantees and preventing data leakage.

## Architecture Features
- **MySQL Native Catalog**: Generates DDL dynamically over `ai_agent_catalog`. Drops all legacy `sqlite` code.
- **NLP PHI Guardrails**: Utilizes Presidio to dynamically classify textual attributes as `PHI_PERSON`, `PHI_DATE_TIME`, preventing the LLM from executing dangerous `SELECT *` commands indiscriminately.
- **Vector Search Context**: Uses `ChromaDB` offline to isolate only the exact data dimensions explicitly requested by a prompt.
- **Dynamic Fallbacks**: Features a native Python `get_client` LLM chain that automatically attempts to utilize local offline models, but gracefully falls back to OpenAI or Gemini when available.
- **Streamlit Web UI**: Chat naturally with your system. Review Agent reasoning, trace confidence parameters, and analyze outputs locally.

---

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install streamlit pandas chromadb ollama
```

## 2) Configure Dependencies (YAML)

Edit `config.yml` in the project root:

```yaml
mysql:
  host: localhost
  port: 3306
  user: root
  password: your_password_here
  database: physician_portal # The target analysis database

catalog:
  schema: ai_agent_catalog # The agent's knowledge brain

llm:
  prefer: local
  local:
    url: http://localhost:11434
    model: llama3.1:8b
```

## 3) Lifecycle Execution Operations

Before chatting with the database, we must allow the agent to learn the context definitions:

```bash
# 1. Rebuild the database dictionary structure
python scripts/crawl.py --include physician_portal

# 2. Re-evaluate NLP heuristics across live string values
python scripts/run_profile.py --schemas physician_portal

# 3. Instruct the LLM to learn concept terms dynamically
python scripts/build_catalog_glossary.py

# 4. Burn the dictionary structures into Vector Chroma representations
python scripts/embed_catalog.py
```

## 4) Interact (Streamlit UI)

Launch the conversational UX dashboard:
```bash
PYTHONPATH=. streamlit run app_ui.py
# open http://localhost:8501
```

## Notes
- The LLM System Prompt aggressively filters queries requesting explicitly-protected PHI tags. However, `WHERE` filtration is structurally permitted to enable chronological parsing (e.g., *“How many records today?”* works via `WHERE` parameter logic).
- To run advanced remote-fallback planning, you must un-comment your valid API keys in `config.yml`.
