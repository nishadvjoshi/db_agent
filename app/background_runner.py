import threading
import uuid
from typing import List, Optional
from app.catalog_store import CatalogStore
from app.crawler import crawl_database
from app.profiler import profile_run
from app.llm.catalog_describer import CatalogDescriber
from scripts.embed_catalog import build_vector_index

def start_background_analysis(conn_id: str, include_schemas: Optional[List[str]] = None) -> str:
    run_id = str(uuid.uuid4())
    store = CatalogStore()
    
    # Pre-register the run in catalog_runs so UI can find it
    store.save_run(run_id)
    store.log_run_event(run_id, "INFO", f"Started analysis for connection {conn_id}")

    thread = threading.Thread(
        target=_run_analysis_pipeline,
        args=(run_id, conn_id, include_schemas)
    )
    thread.daemon = True
    thread.start()
    return run_id

def _run_analysis_pipeline(run_id: str, conn_id: str, include_schemas: Optional[List[str]] = None):
    store = CatalogStore()
    try:
        store.log_run_event(run_id, "INFO", "Step 1/4: Crawling database schema...")
        # Note: We need to modify crawl_database to accept conn_id instead of just using default
        # For now, we assume it's using the default config if conn_id is not passed to it.
        # Ideally, crawl_database will be updated to take conn_id
        
        # Here we mock passing the conn_id for now, we'll update crawler to use it
        crawl_database(include_schemas=include_schemas, run_id=run_id, conn_id=conn_id)
        
        store.log_run_event(run_id, "INFO", "Step 2/4: Profiling sensitive data and PHI...")
        profile_run(run_id, schemas=include_schemas, conn_id=conn_id)
        
        store.log_run_event(run_id, "INFO", "Step 3/4: Generating AI descriptions for tables and columns...")
        catalog = store.get_catalog(run_id)
        describer = CatalogDescriber()
        schemas = catalog.get("schemas", [])
        for s in schemas:
            s_name = s.get("name")
            tables = s.get("tables", [])
            for i, t in enumerate(tables):
                t_name = t.get("name")
                store.log_run_event(run_id, "INFO", f"Describing table {s_name}.{t_name} ({i+1}/{len(tables)})...")
                desc, llm_name = describer.generate_table_description(s_name, t_name, t.get("columns", []))
                store.upsert_catalog_description(run_id, s_name, t_name, "", desc, llm_name)
                
                for c in t.get("columns", []):
                    c_name = c.get("name")
                    c_desc, c_llm = describer.generate_column_description(s_name, t_name, c_name, c.get("data_type"))
                    store.upsert_catalog_description(run_id, s_name, t_name, c_name, c_desc, c_llm)
        
        store.log_run_event(run_id, "INFO", "Step 4/4: Embedding catalog into Vector Database (ChromaDB)...")
        build_vector_index(run_id)
        
        store.log_run_event(run_id, "SUCCESS", "Catalog built successfully!")
    except Exception as e:
        store.log_run_event(run_id, "ERROR", f"Analysis failed: {str(e)}")
