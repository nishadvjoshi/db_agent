# 🏗️ MySQL AI Agent Architecture

Here is a comprehensive architecture diagram covering the exact steps, services, and technologies used in this project. The layout follows a "Draw.io" style aesthetic with color-coded boundaries for Frontend, AI/NLP, Data Pipelines, and Storage.

```mermaid
flowchart TD
    %% Draw.io Style Classes
    classDef frontend fill:#dae8fc,stroke:#6c8ebf,stroke-width:2px,color:#000
    classDef db fill:#d5e8d4,stroke:#82b366,stroke-width:2px,color:#000
    classDef ai fill:#ffe6cc,stroke:#d79b00,stroke-width:2px,color:#000
    classDef nlp fill:#e1d5e7,stroke:#9673a6,stroke-width:2px,color:#000
    classDef core fill:#fff2cc,stroke:#d6b656,stroke-width:2px,color:#000
    classDef vector fill:#f8cecc,stroke:#b85450,stroke-width:2px,color:#000

    User((User)) --> |Interacts| UI

    subgraph "Streamlit Frontend (app_ui.py)"
        direction LR
        UI[Conversational UI & Chat]:::frontend
        Modeler[Data Modeler View]:::frontend
    end

    subgraph "Data Orchestration Pipeline"
        direction TB
        Crawler[1. Metadata Crawler<br/>(Python Adapters)]:::core
        Profiler[2. Data Profiler & PHI Tagger<br/>(Microsoft Presidio NLP)]:::nlp
        Glossary[3. AI Glossary Builder<br/>(Ollama Llama 3.1)]:::ai
        Indexer[4. Semantic Vector Indexer<br/>(Nomic Embeddings)]:::vector
    end

    subgraph "Core Agent Engine"
        direction TB
        Planner[SQL Reasoning Agent<br/>(Local LLM / OpenAI / Gemini)]:::ai
        Guardrails[Privacy Guardrails & Rules<br/>(AST Validation)]:::nlp
        Executor[Query Execution Engine<br/>(Pandas DataFrames)]:::core
        Visualizer[Dynamic Chart Generator<br/>(Plotly)]:::frontend
    end

    subgraph "Storage & Databases"
        TargetDB[(Target Database<br/>MySQL/Redshift/SQLServer)]:::db
        CatalogDB[(AI Catalog Metadata<br/>MySQL Native)]:::db
        VectorDB[(Semantic Index<br/>Local ChromaDB)]:::vector
    end

    %% Pipeline Flow
    UI --> |Triggers Analysis| Crawler
    Crawler --> |Extracts DDL| TargetDB
    Crawler --> |Saves Schema| CatalogDB
    
    Crawler --> Profiler
    Profiler --> |Scans 200 Rows for PHI| TargetDB
    Profiler --> |Updates Catalog Tags| CatalogDB
    
    Profiler --> Glossary
    Glossary --> |Reads Schema| CatalogDB
    Glossary --> |Writes AI Docs| CatalogDB
    
    Glossary --> Indexer
    Indexer --> |Reads AI Docs| CatalogDB
    Indexer --> |Upserts Vectors| VectorDB

    %% Query Flow
    UI --> |Natural Language Query| Planner
    Modeler -.-> |Generates Cube.js YAML| Planner
    
    Planner --> |1. Similarity Search| VectorDB
    Planner --> |2. Fetch Filtered DDL| CatalogDB
    Planner --> |3. Generate SQL| Guardrails
    
    Guardrails --> |4. Validates READ-ONLY| Executor
    Executor --> |5. Execute Safe SQL| TargetDB
    Executor --> |6. Return Results| Visualizer
    Visualizer --> |7. Render Chart UI| UI
```

### Component Breakdown & Technologies Used
1. **Frontend**: Built entirely with **Streamlit** for rapid UI generation, allowing conversational chat, markdown rendering, and interactive Plotly data visualizations.
2. **Data Orchestration Pipeline**: 
    - Scans the target database schemas and extracts relationships using raw **Python** adapters.
    - Utilizes **Microsoft Presidio (NLP)** to analyze row samples and proactively tag PII/PHI so the AI learns what *not* to query.
    - Uses **Ollama (Llama 3.1)** locally to generate robust human-readable descriptions of all obscure columns.
    - Uses **ChromaDB + Nomic Text Embeddings** to turn those descriptions into searchable high-dimensional vectors.
3. **Core Agent Engine**: The brain. When you ask a question, the Agent performs Cosine Similarity against the VectorDB, fetches only the 5-10 relevant tables, and builds a tight execution plan. It falls back to **OpenAI/Gemini** if the local LLM struggles with complexity.
4. **Storage**: Completely standalone. Instead of relying on fragile SQLite files, the entire AI Catalog lives beautifully inside a structured **MySQL** database (`ai_agent_catalog`).
