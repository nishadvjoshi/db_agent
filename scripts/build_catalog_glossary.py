import argparse
import sys
import logging
from app.catalog_store import CatalogStore
from app.llm.catalog_describer import CatalogDescriber

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate AI descriptions for database catalog.")
    parser.add_argument("--run-id", type=str, help="Specific run_id to process. If omitted, uses the latest run.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing descriptions.")
    args = parser.parse_args()

    store = CatalogStore()
    
    run_id = args.run_id
    if not run_id:
        con = store._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute("SELECT run_id FROM `catalog_runs` ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                run_id = row["run_id"]
        finally:
            cur.close()
            con.close()
            
    if not run_id:
        logger.error("No catalog runs found. Please run the crawler first.")
        sys.exit(1)

    logger.info(f"Processing catalog for run_id: {run_id}")
    
    catalog = store.get_catalog(run_id)
    schemas = catalog.get("schemas", [])
    if not schemas:
        logger.warning("No schemas found in catalog.")
        sys.exit(0)

    describer = CatalogDescriber()
    
    for s in schemas:
        schema_name = s.get("name")
        for t in s.get("tables", []):
            table_name = t.get("name")
            columns = t.get("columns", [])
            
            existing_table_desc = t.get("catalog_description")
            
            # Describe Table
            if not existing_table_desc or args.force:
                logger.info(f"Generating description for table '{schema_name}.{table_name}'...")
                desc, llm_name = describer.generate_table_description(schema_name, table_name, columns)
                store.upsert_catalog_description(run_id, schema_name, table_name, "", desc, llm_name)
            else:
                logger.debug(f"Skipping table '{schema_name}.{table_name}' (already has description)")
                
            # Describe Columns
            for c in columns:
                col_name = c.get("name")
                data_type = c.get("data_type")
                existing_col_desc = c.get("catalog_description")
                
                if not existing_col_desc or args.force:
                    logger.info(f"  Generating description for column '{col_name}'...")
                    desc, llm_name = describer.generate_column_description(schema_name, table_name, col_name, data_type)
                    store.upsert_catalog_description(run_id, schema_name, table_name, col_name, desc, llm_name)
                else:
                    logger.debug(f"  Skipping column '{col_name}' (already has description)")

    logger.info("Finished building catalog glossary.")

if __name__ == "__main__":
    main()
