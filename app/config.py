import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yml"

class Settings:
    def __init__(self):
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Missing config.yml at: {CONFIG_PATH}")

        cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

        self.environment = cfg.get("environment", "dev")

        mysql = cfg.get("mysql", {}) or {}
        self.mysql_host = mysql.get("host", "localhost")
        self.mysql_port = int(mysql.get("port", 3306))
        self.mysql_user = mysql.get("user", "root")
        self.mysql_password = mysql.get("password", "")
        self.mysql_database = mysql.get("database", "")

        target = cfg.get("target_db", {}) or {}
        self.target_db_type = target.get("type", "mysql")
        self.target_db_host = target.get("host", self.mysql_host)
        self.target_db_port = int(target.get("port", self.mysql_port))
        self.target_db_user = target.get("user", self.mysql_user)
        self.target_db_password = target.get("password", self.mysql_password)
        self.target_db_name = target.get("database", self.mysql_database)

        catalog = cfg.get("catalog", {}) or {}
        self.catalog_schema = catalog.get("schema", "ai_agent_catalog")

        agent = cfg.get("agent", {}) or {}
        self.sample_rows = int(agent.get("sample_rows", 200))
        self.max_tables_return = int(agent.get("max_tables_return", 15))
        self.force_limit = int(agent.get("force_limit", 200))

        profiling = cfg.get("profiling", {}) or {}
        self.profiling_enabled = bool(profiling.get("enabled", True))
        
        # Read LLM settings
        llm = cfg.get("llm", {}) or {}
        self.llm_prefer = llm.get("prefer", "local")
        self.llm_min_confidence = float(llm.get("min_confidence", 0.75))
        self.llm_fallback_order = llm.get("fallback_order", ["openai", "gemini"])
        self.llm_local = llm.get("local", {}) or {}
        self.llm_local_timeout = int(self.llm_local.get("timeout", 15))
        self.llm_openai = llm.get("openai", {}) or {}
        self.llm_gemini = llm.get("gemini", {}) or {}

settings = Settings()
