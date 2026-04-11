from fastapi import FastAPI
from pydantic import BaseModel
from app.crawler import crawl_mysql
from app.profiler import profile_run
from app.agent import propose_sql, explain_concept
from app.modeling import kpi_to_model

app = FastAPI(title="MySQL Context Agent (MVP)")

class CrawlRequest(BaseModel):
    include_schemas: list[str] | None = None
    exclude_schemas: list[str] | None = None
    run_profiler: bool = False

class AskRequest(BaseModel):
    run_id: str
    question: str
    context: dict | None = None

class ExplainConceptRequest(BaseModel):
    run_id: str
    concept: str

class KPIModelRequest(BaseModel):
    run_id: str
    kpi: str

@app.post("/crawl")
def crawl(req: CrawlRequest):
    run_id = crawl_mysql(req.include_schemas, req.exclude_schemas)
    if req.run_profiler:
        profile_run(run_id, schemas=req.include_schemas)
    return {"run_id": run_id}

@app.post("/explain-concept")
def explain(req: ExplainConceptRequest):
    return explain_concept(req.run_id, req.concept)

@app.post("/ask")
def ask(req: AskRequest):
    return propose_sql(req.run_id, req.question, context=req.context or {})

@app.post("/kpi-to-model")
def model(req: KPIModelRequest):
    return kpi_to_model(req.run_id, req.kpi)
