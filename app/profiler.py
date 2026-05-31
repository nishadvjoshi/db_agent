import re
try:
    from presidio_analyzer import AnalyzerEngine
    HAS_PRESIDIO = True
except Exception:
    HAS_PRESIDIO = False
from app.db_mysql import get_mysql_conn
from app.catalog_store import CatalogStore
from app.config import settings

class PHIDetector:
    def __init__(self):
        # Initialize the Presidio analyzer with a confidence threshold if available
        self.analyzer = AnalyzerEngine(default_score_threshold=0.4) if HAS_PRESIDIO else None
    
    def detect_phi(self, sample_values: list) -> tuple[str, float]:
        """Analyzes a list of data samples to identify PHI entities."""
        if not sample_values:
            return "unknown", 0.0
        
        # Combine samples into a single string for analysis
        text_to_analyze = " | ".join([str(v) for v in sample_values if v is not None])
        if not text_to_analyze.strip():
            return "unknown", 0.0

        if not self.analyzer:
            return "unknown", 0.0

        results = self.analyzer.analyze(text=text_to_analyze, language='en')
        
        if not results:
            return "non-phi", 1.0
        
        # Count the frequency of detected entity types (e.g., PERSON, PHONE_NUMBER)
        findings = {}
        for res in results:
            findings[res.entity_type] = findings.get(res.entity_type, 0) + 1
        
        # Identify the most frequent PHI entity found in the sample set
        top_entity = max(findings, key=findings.get)
        return top_entity, 0.8
SEMANTIC_RULES = [
    ("PHI_email", re.compile(r"email", re.I)),
    ("PHI_phone", re.compile(r"phone|mobile|contact", re.I)),
    ("PHI_dob", re.compile(r"dob", re.I)),
    ("date", re.compile(r"date|dt|created|updated|timestamp|time", re.I)),
    ("amount", re.compile(r"amount|amt|price|cost|paid|pay|charge|balance|copay", re.I)),
    ("status", re.compile(r"status|state|flag|is_|has_", re.I)),
    ("PHI_name", re.compile(r"name|nm|first|last|full", re.I)),
    ("PHI_medical_code", re.compile(r"icd|ndc", re.I)),
    ("code", re.compile(r"code|cd|type|category", re.I)),
    ("PHI_mrn", re.compile(r"mrn", re.I)),
    ("id", re.compile(r"_id$|^id$|key|identifier", re.I)),
]

def infer_semantic_type(column_name: str, mysql_data_type: str, phi_detector: PHIDetector = None, samples: list = None) -> str:
    # Ignore system audit dates from being aggressively tagged as PHI
    system_dates = {"created_at", "updated_at", "created_date", "modified_date"}
    if column_name.lower() in system_dates:
        return "date"

    # Priority 1: NLP analysis of the actual data content using Presidio
    if phi_detector and samples:
        phi_type, confidence = phi_detector.detect_phi(samples)
        if confidence > 0.5 and phi_type != "non-phi":
            return f"PHI_{phi_type}"

    # Priority 2: Fallback to existing regex-based semantic rules
    dt = (mysql_data_type or "").lower()
    if dt in ("date", "datetime", "timestamp", "time", "year"):
        return "date"
    for label, rx in SEMANTIC_RULES:
        if rx.search(column_name):
            return label
    if dt in ("int", "bigint", "smallint", "tinyint"):
        return "number"
    if dt in ("decimal", "numeric", "float", "double"):
        return "number"
    if dt in ("varchar", "text", "char", "longtext", "mediumtext"):
        return "text"
    return "unknown"

def profile_run(run_id: str, schemas=None, conn_id: str = None):
    store = CatalogStore()
    detector = PHIDetector()
    
    # Setup target connection using adapter
    from app.config import settings
    from app.adapters.factory import get_adapter
    
    target_params = {
        "host": settings.target_db_host,
        "port": settings.target_db_port,
        "user": settings.target_db_user,
        "password": settings.target_db_password,
        "database": settings.target_db_name,
    }
    db_type = settings.target_db_type

    if conn_id:
        conn = store.get_connection(conn_id)
        if conn:
            db_type = conn.get("db_type", "mysql").lower()
            target_params = {
                "host": conn.get("host"),
                "port": conn.get("port"),
                "user": conn.get("username"),
                "password": conn.get("password"),
                "database": conn.get("database_name"),
            }
    
    target_params = {k: v for k, v in target_params.items() if v}
    adapter = get_adapter(db_type, target_params)

    con = store._conn()
    cur_cat = con.cursor()
    try:
        cur_cat.execute(
            "SELECT schema_name, table_name FROM `catalog_tables` WHERE run_id=%s",
            (run_id,)
        )
        rows = cur_cat.fetchall()
    finally:
        cur_cat.close()
        con.close()

    schema_filter = set(schemas) if schemas else None

    for schema_name, table_name in rows:
        if schema_filter and schema_name not in schema_filter:
            continue

        con2 = store._conn()
        cur2 = con2.cursor()
        try:
            cur2.execute(
                """SELECT column_name, data_type FROM `catalog_columns`
                   WHERE run_id=%s AND schema_name=%s AND table_name=%s""",
                (run_id, schema_name, table_name),
            )
            cols = cur2.fetchall()
        finally:
            cur2.close()
            con2.close()

        for col_name, data_type in cols:
            sample_vals, null_count, distinct_count = [], None, None
            try:
                # Query target database via adapter
                samples_res = adapter.execute_query(
                    f"SELECT `{col_name}` AS v FROM `{schema_name}`.`{table_name}` "
                    f"WHERE `{col_name}` IS NOT NULL LIMIT {settings.sample_rows}"
                )
                sample_vals = [r.get("v") or r.get("V") for r in samples_res]

                null_res = adapter.execute_query(
                    f"SELECT COUNT(*) AS c FROM `{schema_name}`.`{table_name}` WHERE `{col_name}` IS NULL"
                )
                null_count = int(null_res[0].get("c") or null_res[0].get("C", 0)) if null_res else 0

                dist_res = adapter.execute_query(
                    f"SELECT COUNT(DISTINCT `{col_name}`) AS c FROM `{schema_name}`.`{table_name}`"
                )
                distinct_count = int(dist_res[0].get("c") or dist_res[0].get("C", 0)) if dist_res else 0
            except Exception:
                pass

            inferred = infer_semantic_type(col_name, data_type, detector, sample_vals)

            store.upsert_profile(
                run_id, schema_name, table_name, col_name, inferred,
                distinct_count, null_count, sample_vals
            )
