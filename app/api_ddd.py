from fastapi import APIRouter
from pydantic import BaseModel

from app.catalog_store import CatalogStore
from app.skills import (
    DomainDiscoverySkill, BoundedContextSkill, UbiquitousLanguageSkill,
    ContextMappingSkill, AggregateModelingSkill, DomainEventSkill, DataProductSkill,
    GrainDefinitionSkill, DimensionalTranslationSkill, ConceptualToLogicalSkill,
    SchemaGenerationSkill
)

router = APIRouter(prefix="/api/skills/ddd")

class BaseRunRequest(BaseModel):
    run_id: str

@router.post("/discover")
def run_domain_discovery(req: BaseRunRequest):
    skill = DomainDiscoverySkill(req.run_id)
    result = skill.execute()
    store = CatalogStore()
    store.save_ddd_artifact(req.run_id, "discovered_domains", result)
    return {"status": "success", "data": result}

@router.post("/bounded_contexts")
def run_bounded_contexts(req: BaseRunRequest):
    store = CatalogStore()
    domains_artifact = store.get_ddd_artifact(req.run_id, "discovered_domains")
    domains = domains_artifact.get("domains", []) if domains_artifact else []
    
    skill = BoundedContextSkill(req.run_id)
    result = skill.execute(domains=domains)
    store.save_ddd_artifact(req.run_id, "bounded_contexts", result)
    return {"status": "success", "data": result}

@router.post("/ubiquitous_language")
def run_ubiquitous_language(req: BaseRunRequest):
    store = CatalogStore()
    bc_artifact = store.get_ddd_artifact(req.run_id, "bounded_contexts")
    bounded_contexts = bc_artifact.get("bounded_contexts", []) if bc_artifact else []
    
    skill = UbiquitousLanguageSkill(req.run_id)
    result = skill.execute(bounded_contexts=bounded_contexts)
    store.save_ddd_artifact(req.run_id, "ubiquitous_language", result)
    return {"status": "success", "data": result}

@router.post("/context_mapping")
def run_context_mapping(req: BaseRunRequest):
    store = CatalogStore()
    bc_artifact = store.get_ddd_artifact(req.run_id, "bounded_contexts")
    bounded_contexts = bc_artifact.get("bounded_contexts", []) if bc_artifact else []
    
    skill = ContextMappingSkill(req.run_id)
    result = skill.execute(bounded_contexts=bounded_contexts)
    store.save_ddd_artifact(req.run_id, "context_mapping", result)
    return {"status": "success", "data": result}

@router.post("/aggregate_modeling")
def run_aggregate_modeling(req: BaseRunRequest):
    store = CatalogStore()
    bc_artifact = store.get_ddd_artifact(req.run_id, "bounded_contexts")
    bounded_contexts = bc_artifact.get("bounded_contexts", []) if bc_artifact else []
    
    skill = AggregateModelingSkill(req.run_id)
    result = skill.execute(bounded_contexts=bounded_contexts)
    store.save_ddd_artifact(req.run_id, "aggregate_modeling", result)
    return {"status": "success", "data": result}

@router.post("/domain_events")
def run_domain_events(req: BaseRunRequest):
    store = CatalogStore()
    agg_artifact = store.get_ddd_artifact(req.run_id, "aggregate_modeling")
    aggregates = agg_artifact.get("aggregates", []) if agg_artifact else []
    
    skill = DomainEventSkill(req.run_id)
    result = skill.execute(aggregates=aggregates)
    store.save_ddd_artifact(req.run_id, "domain_events", result)
    return {"status": "success", "data": result}

@router.post("/data_products")
def run_data_products(req: BaseRunRequest):
    store = CatalogStore()
    domains_artifact = store.get_ddd_artifact(req.run_id, "discovered_domains")
    domains = domains_artifact.get("domains", []) if domains_artifact else []
    
    skill = DataProductSkill(req.run_id)
    result = skill.execute(domains=domains)
    store.save_ddd_artifact(req.run_id, "data_products", result)
    return {"status": "success", "data": result}

@router.post("/grain_definition")
def run_grain_definition(req: BaseRunRequest):
    store = CatalogStore()
    agg_artifact = store.get_ddd_artifact(req.run_id, "aggregate_modeling")
    events_artifact = store.get_ddd_artifact(req.run_id, "domain_events")
    
    aggregates = agg_artifact.get("aggregates", []) if agg_artifact else []
    domain_events = events_artifact.get("domain_events", []) if events_artifact else []
    
    skill = GrainDefinitionSkill(req.run_id)
    result = skill.execute(aggregates=aggregates, domain_events=domain_events)
    store.save_ddd_artifact(req.run_id, "grain_definition", result)
    return {"status": "success", "data": result}

@router.post("/dimensional_translation")
def run_dimensional_translation(req: BaseRunRequest):
    store = CatalogStore()
    grain_artifact = store.get_ddd_artifact(req.run_id, "grain_definition")
    agg_artifact = store.get_ddd_artifact(req.run_id, "aggregate_modeling")
    
    processes = grain_artifact.get("processes", []) if grain_artifact else []
    aggregates = agg_artifact.get("aggregates", []) if agg_artifact else []
    
    skill = DimensionalTranslationSkill(req.run_id)
    result = skill.execute(processes=processes, aggregates=aggregates)
    store.save_ddd_artifact(req.run_id, "dimensional_translation", result)
    return {"status": "success", "data": result}

@router.post("/conceptual_to_logical")
def run_conceptual_to_logical(req: BaseRunRequest):
    store = CatalogStore()
    dim_artifact = store.get_ddd_artifact(req.run_id, "dimensional_translation")
    
    facts = dim_artifact.get("facts", []) if dim_artifact else []
    dimensions = dim_artifact.get("dimensions", []) if dim_artifact else []
    
    skill = ConceptualToLogicalSkill(req.run_id)
    result = skill.execute(facts=facts, dimensions=dimensions)
    store.save_ddd_artifact(req.run_id, "conceptual_to_logical", result)
    return {"status": "success", "data": result}

@router.post("/schema_generation")
def run_schema_generation(req: BaseRunRequest):
    store = CatalogStore()
    logic_artifact = store.get_ddd_artifact(req.run_id, "conceptual_to_logical")
    
    logical_schema = logic_artifact.get("logical_schema", []) if logic_artifact else []
    
    skill = SchemaGenerationSkill(req.run_id)
    result = skill.execute(logical_schema=logical_schema)
    store.save_ddd_artifact(req.run_id, "schema_generation", result)
    return {"status": "success", "data": result}

from pydantic import BaseModel
class DeployRequest(BaseModel):
    ddl: str
    conn_id: str
    warehouse_name: str

@router.post("/deploy_ddl")
def deploy_ddl(req: DeployRequest):
    from app.db_factory import DatabaseConnector
    import logging
    
    conn = DatabaseConnector.get_connection(req.conn_id)
    if not conn:
        return {"success": False, "error": "Connection not found"}
        
    try:
        mysql_conn = conn.connect()
        cursor = mysql_conn.cursor()
        
        # Ensure database exists and select it
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{req.warehouse_name}`")
        cursor.execute(f"USE `{req.warehouse_name}`")
        
        # Execute each statement
        statements = req.ddl.split(';')
        for stmt in statements:
            if stmt.strip():
                cursor.execute(stmt)
                
        mysql_conn.commit()
        return {"success": True}
    except Exception as e:
        logging.error(f"Deploy error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        if 'mysql_conn' in locals() and mysql_conn.is_connected():
            cursor.close()
            mysql_conn.close()

@router.get("/artifacts/{run_id}")
def get_all_artifacts(run_id: str):
    store = CatalogStore()
    return {
        "discovered_domains": store.get_ddd_artifact(run_id, "discovered_domains"),
        "bounded_contexts": store.get_ddd_artifact(run_id, "bounded_contexts"),
        "ubiquitous_language": store.get_ddd_artifact(run_id, "ubiquitous_language"),
        "context_mapping": store.get_ddd_artifact(run_id, "context_mapping"),
        "aggregate_modeling": store.get_ddd_artifact(run_id, "aggregate_modeling"),
        "domain_events": store.get_ddd_artifact(run_id, "domain_events"),
        "data_products": store.get_ddd_artifact(run_id, "data_products"),
        "grain_definition": store.get_ddd_artifact(run_id, "grain_definition"),
        "dimensional_translation": store.get_ddd_artifact(run_id, "dimensional_translation"),
        "conceptual_to_logical": store.get_ddd_artifact(run_id, "conceptual_to_logical"),
        "schema_generation": store.get_ddd_artifact(run_id, "schema_generation"),
    }
