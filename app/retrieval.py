import os
import chromadb
import ollama
from chromadb.utils import embedding_functions
from app.config import settings
from app.glossary import Glossary
from app.catalog_store import CatalogStore

class OllamaEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, model_name: str="nomic-embed-text"):
        self.model_name = model_name

    def __call__(self, input: list[str]) -> list[list[float]]:
        resp = ollama.embed(model=self.model_name, input=input)
        return resp["embeddings"]

def retrieve_candidates(run_id: str, text: str, max_tables=None):
    max_tables = max_tables or settings.max_tables_return

    # Expand query with Glossary context
    gl = Glossary()
    expanded_query = text
    for cname, payload in gl.find_concepts(text):
        expanded_query += " " + " ".join(payload.get("synonyms", []))
        expanded_query += " " + " ".join(payload.get("table_hints", []))

    # Connect to local ChromaDB
    chroma_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_data"))
    client = chromadb.PersistentClient(path=chroma_path)
    emb_fn = OllamaEmbeddingFunction(model_name="nomic-embed-text")
    try:
        collection = client.get_collection(name="catalog_embeddings", embedding_function=emb_fn)
    except Exception:
        print("Warning: Chroma collection not found. Run embed_catalog.py first!")
        return []

    # Query Top K vector matches
    results = collection.query(
        query_texts=[expanded_query],
        n_results=max_tables * 3, # over-fetch columns
        where={"run_id": run_id}
    )

    if not results["metadatas"] or not results["metadatas"][0]:
        return []

    # Aggregate scores (Chroma returns distance, lower is better. We invert it for 'score')
    top_table_names = set()
    table_scores = {}
    
    for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
        tbl_name = meta["table"]
        top_table_names.add(tbl_name)
        # Invert distance to score
        score = max(0, 2.0 - dist)
        table_scores[tbl_name] = table_scores.get(tbl_name, 0) + score

    # Fetch physical schema details for the winning tables
    store = CatalogStore()
    con = store._conn()
    cur = con.cursor()
    try:
        cur.execute(
            """SELECT schema_name, table_name, column_name, data_type
               FROM `catalog_columns` WHERE run_id=%s""",
            (run_id,),
        )
        cols = cur.fetchall()

        cur.execute(
            """SELECT schema_name, table_name, column_name, inferred_semantic_type
               FROM `catalog_profiles` WHERE run_id=%s""",
            (run_id,),
        )
        profiles = cur.fetchall()
        prof_map = {(s, t, c): sem for s, t, c, sem in profiles}

        hits = {}
        for s, t, c, dt in cols:
            if t not in top_table_names:
                continue
            
            sem = prof_map.get((s, t, c))
            key = f"{s}.{t}"
            
            # Sub-score just to sort columns inside the LLM prompt
            base_col_score = 1.0 if (c.lower() in text.lower()) else 0.1
            
            hits.setdefault(key, []).append(
                {"column": c, "data_type": dt, "semantic": sem, "score": base_col_score}
            )

        ranked = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)[:max_tables]
        
        # We need the schema prefix for the payload
        schema_lookup = {t: s for s, t, c, dt in cols}

        result = []
        for tbl_name, sc in ranked:
            sch = schema_lookup.get(tbl_name, "ai_agent_catalog")
            full_key = f"{sch}.{tbl_name}"
            result.append(
                {
                    "table": full_key,
                    "score": sc,
                    "hits": sorted(hits.get(full_key, []), key=lambda x: x["score"], reverse=True)[:15],
                }
            )
        return result
    finally:
        cur.close()
        con.close()
