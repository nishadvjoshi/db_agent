# MySQL Context Agent: Technical API Documentation

The **MySQL Context Agent** exposes three primary endpoint features that power the Conversational BI backend. This document outlines the technical specifics, the flow of data, and two example input/output structures for each major feature.

---

## 1. Concept Explanation (`/explain-concept`)

**Description:**
This feature provides domain-specific context for business terms. It cross-references an internal healthcare glossary (e.g., `healthcare_glossary.yml`) with the crawled database catalog to identify which database schemas and tables are most relevant to the user's concept.

**Internal Flow:**
1. Text tokenization and synonym resolution using `Glossary.find_concepts`.
2. Candidate mapping via MySQL metadata retrieval (`retrieve_candidates`).
3. Payload construction marrying the business definition with physical DB tables.

### Example 1: Direct Concept Match
**Input (POST):**
```json
{
  "run_id": "d9a644e1-60ad-4ba4-bbad-4df71facc3e1",
  "concept": "Caremap"
}
```

**Output (JSON):**
```json
{
  "concept": "Caremap",
  "glossary": {
    "description": "A standardized path of care for a specific condition",
    "synonyms": ["clinical pathway", "care plan", "treatment protocol"],
    "table_hints": ["caremaps", "caremap_steps"]
  },
  "candidate_tables": [
    {
      "table": "physician_portal.caremaps",
      "score": 14,
      "hits": [...]
    },
    {
      "table": "physician_portal.caremap_steps",
      "score": 8,
      "hits": [...]
    }
  ],
  "notes": [
    "Glossary gives domain meaning; candidates are matched against actual schema.",
    "Add your data dictionary and refine hints for higher accuracy."
  ]
}
```

### Example 2: Unrecognized Concept (Fallback)
**Input (POST):**
```json
{
  "run_id": "d9a644e1-60ad-4ba4-bbad-4df71facc3e1",
  "concept": "Telemetry Logs"
}
```

**Output (JSON):**
```json
{
  "concept": "Telemetry Logs",
  "glossary": null,
  "candidate_tables": [],
  "notes": [
    "Glossary gives domain meaning; candidates are matched against actual schema.",
    "Add your data dictionary and refine hints for higher accuracy."
  ]
}
```

---

## 2. Text-to-SQL Generation (`/ask`)

**Description:**
This feature converts natural language questions into safe, read-only SQL queries. It leverages a local Language Model (e.g., `llama3.1:8b`) mapped to the database metadata.

**Safety & PHI Hardening (`sql_guardrails.py`):**
- **Action Guardrails:** DDL and DML operations (INSERT, DROP, UPDATE, etc.) are strictly blocked.
- **Limits:** Every query is forcibly appended with a `LIMIT` clause (default 50).
- **PHI Masking:** During the metadata crawl, Microsoft Presidio tags columns containing Protected Health Information (e.g., `PHI_PERSON`, `PHI_PHONE_NUMBER`). If the LLM's generated query references these columns or attempts a blind `SELECT *` over a table containing them, the query is blocked and forced into a `"CLARIFY"` action.

### Example 1: Safe Analytical Query
**Input (POST):**
```json
{
  "run_id": "d9a644e1-60ad-4ba4-bbad-4df71facc3e1",
  "question": "how many appointments are there in total?"
}
```

**Output (JSON):**
```json
{
  "question": "how many appointments are there in total?",
  "provider_used": "local",
  "confidence": 1.0,
  "detected_intent": "AGGREGATION",
  "action": "SQL",
  "candidate_tables": [
    {"table": "physician_portal.appointments", "score": 50, "hits": [...]}
  ],
  "sql": "SELECT COUNT(*) FROM physician_portal.appointments LIMIT 50;",
  "answer": null,
  "used_tables": ["physician_portal.appointments"],
  "needs_clarification": false,
  "clarification_question": null,
  "debug": {}
}
```

### Example 2: Unsafe PHI Query (Blocked)
**Input (POST):**
```json
{
  "run_id": "d9a644e1-60ad-4ba4-bbad-4df71facc3e1",
  "question": "what are the names and phone numbers of the physicians?"
}
```

**Output (JSON):**
```json
{
  "question": "what are the names and phone numbers of the physicians?",
  "provider_used": "none",
  "confidence": 0.0,
  "detected_intent": "UNKNOWN",
  "action": "CLARIFY",
  "candidate_tables": [
    {"table": "physician_portal.physicians", "score": 16, "hits": [...]}
  ],
  "sql": null,
  "answer": null,
  "used_tables": [],
  "needs_clarification": true,
  "clarification_question": "I couldn't confidently plan this. Can you mention a table/column or rephrase?",
  "debug": {
    "error": "Unsafe query: Cannot select sensitive PHI column 'phone' (PHI_DATE_TIME)"
  }
}
```

---

## 3. KPI to Semantic Model Generation (`/kpi-to-model`)

**Description:**
This feature bridges the gap between high-level business metrics and physical database structures. It parses a natural language KPI and outputs a structured Semantic Layer definition (YAML), which can be consumed by BI frontends (like Cube.js) for charting and visualization.

**Internal Flow:**
1. Parses the KPI using the glossary (`find_concepts`).
2. Retrieves and scores candidate tables.
3. Classifies tables heuristically as `FACT_CANDIDATE` (many rows, numeric + datetime columns) or `DIM_CANDIDATE` (text-heavy, ids).
4. Feeds the extracted metadata into the local LLM to generate a compliant Cube.js YAML syntax model mapping the measures and dimensions.

### Example 1: Standard KPI Conversion
**Input (POST):**
```json
{
  "run_id": "d9a644e1-60ad-4ba4-bbad-4df71facc3e1",
  "kpi": "No-show rate by physician per month"
}
```

**Output (JSON):**
```json
{
  "kpi": "No-show rate by physician per month",
  "concept_hits": [],
  "candidate_tables": [...],
  "proposed_facts": [
    {
      "schema": "physician_portal",
      "table": "appointments",
      "role": "FACT_CANDIDATE",
      "scores": {"fact": 4, "dim": 3}
    }
  ],
  "proposed_dimensions": [
    {
      "schema": "physician_portal",
      "table": "physicians",
      "role": "DIM_CANDIDATE",
      "scores": {"fact": 2, "dim": 3}
    }
  ],
  "semantic_layer_model": "cubes:\n  - name: physician_portal_appointments\n    sql: SELECT * FROM physician_portal.appointments\n    measures:\n      - name: no_show_rate\n        sql: COUNT(CASE WHEN status = 'no show' THEN 1 END) / COUNT(*)\n        type: number\n    dimensions:\n      - name: appointment_datetime\n        sql: appointment_datetime\n        type: time",
  "notes": [
    "MVP heuristics: improve by adding org-specific docs + synonyms.",
    "Next step: detect grain/measures/time columns and generate full fact/dim DDL."
  ],
  "confidence": 0.6
}
```

### Example 2: Metric requiring implicitly promoted Fact Table
**Input (POST):**
```json
{
  "run_id": "d9a644e1-60ad-4ba4-bbad-4df71facc3e1",
  "kpi": "Total count of registered patients"
}
```

**Output (JSON):**
```json
{
  "kpi": "Total count of registered patients",
  "concept_hits": [],
  "candidate_tables": [...],
  "proposed_facts": [
    {
      "schema": "physician_portal",
      "table": "patients",
      "role": "FACT_CANDIDATE",
      "scores": {"fact": 2, "dim": 4} 
    }
  ],
  "proposed_dimensions": [],
  "semantic_layer_model": "cubes:\n  - name: physician_portal_patients\n    sql: SELECT * FROM physician_portal.patients\n    measures:\n      - name: total_registered_patients\n        sql: COUNT(patient_id)\n        type: count\n    dimensions:\n      - name: created_at\n        sql: created_at\n        type: time",
  "notes": [
    "MVP heuristics: improve by adding org-specific docs + synonyms.",
    "Next step: detect grain/measures/time columns and generate full fact/dim DDL."
  ],
  "confidence": 0.6
}
```
*(Note: Because the request implies a metric aggregation, the system promotes the primary target table to act as the Fact table for the count measure, enabling dynamic model assembly).*
