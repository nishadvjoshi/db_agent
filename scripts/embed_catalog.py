import os
import sys
import chromadb
import ollama
from chromadb.utils import embedding_functions

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db_mysql import get_mysql_conn

class OllamaEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, model_name: str="nomic-embed-text"):
        self.model_name = model_name

    def __call__(self, input: list[str]) -> list[list[float]]:
        # Ollama's embed endpoint takes an array of texts
        resp = ollama.embed(model=self.model_name, input=input)
        return resp["embeddings"]

def build_vector_index(run_id: str):
    print(f"Building Vector Index for run: {run_id}")
    
    # 1. Connect to MySQL and fetch definitions
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    
    # Fetch Tables
    cur.execute('''
        SELECT table_name, ai_description, ai_generated_by
        FROM ai_agent_catalog.catalog_tables 
        WHERE run_id=%s AND ai_description IS NOT NULL
    ''', (run_id,))
    tables = cur.fetchall()
    
    # Fetch Columns
    cur.execute('''
        SELECT schema_name, table_name, column_name, data_type, ai_description 
        FROM ai_agent_catalog.catalog_columns 
        WHERE run_id=%s AND ai_description IS NOT NULL
    ''', (run_id,))
    columns = cur.fetchall()
    
    cur.close()
    conn.close()

    # 2. Setup ChromaDB client (local persistent DB)
    chroma_path = os.path.join(os.path.dirname(__file__), "..", "chroma_data")
    os.makedirs(chroma_path, exist_ok=True)
    client = chromadb.PersistentClient(path=chroma_path)
    
    emb_fn = OllamaEmbeddingFunction(model_name="nomic-embed-text")
    
    # We use get_or_create to allow idempotent updates
    collection = client.get_or_create_collection(
        name="catalog_embeddings",
        embedding_function=emb_fn
    )
    
    # 3. Batch and load data
    ids = []
    documents = []
    metadatas = []
    
    for t in tables:
        doc_id = f"table::{t['table_name']}"
        text = f"Table: {t['table_name']}. Description: {t['ai_description']}"
        ids.append(doc_id)
        documents.append(text)
        metadatas.append({"type": "table", "table": t['table_name'], "run_id": run_id})
        
    for c in columns:
        doc_id = f"column::{c['schema_name']}.{c['table_name']}.{c['column_name']}"
        text = f"Column: {c['column_name']} in table {c['table_name']} (Type {c['data_type']}). Description: {c['ai_description']}"
        ids.append(doc_id)
        documents.append(text)
        metadatas.append({
            "type": "column", 
            "schema": c['schema_name'],
            "table": c['table_name'], 
            "column": c['column_name'],
            "run_id": run_id
        })
        
    if not ids:
        print("No AI descriptions found to embed.")
        return

    print(f"Embedding {len(ids)} total entities into Chroma...")
    # Chroma handles batching, but we can do chunks of 100 to be safe
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size]
        )
        print(f"Upserted batch {i} to {i+min(batch_size, len(ids)-i)}")

    print("Embedding complete!")

if __name__ == "__main__":
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT run_id FROM ai_agent_catalog.catalog_runs ORDER BY created_at DESC LIMIT 1;")
    row = cur.fetchone()
    conn.close()
    if row:
        build_vector_index(row["run_id"])
    else:
        print("No run_id found in database.")
