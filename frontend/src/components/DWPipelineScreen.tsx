import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Loader2, Server, Map, BookOpen, Layers, Columns, Network, Play, Check, Database } from 'lucide-react';
import mermaid from 'mermaid';

const API_URL = 'http://localhost:8000/api';

export default function DWPipelineScreen({ activeRunId }: { activeRunId: string | null }) {
  const [loading, setLoading] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<any>({});
  const [activeTab, setActiveTab] = useState<'phase_a' | 'phase_b' | 'phase_c'>('phase_a');
  const [agentExpanded, setAgentExpanded] = useState(false);
  
  // Deployment State
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [deployed, setDeployed] = useState(false);
  const [deployConnId, setDeployConnId] = useState('');
  const [deployWarehouseName, setDeployWarehouseName] = useState('edw_production');
  const [connections, setConnections] = useState<any[]>([]);
  
  const mermaidRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1.0);

  useEffect(() => {
    if (activeRunId) {
      fetchArtifacts();
      fetchConnections();
    }
  }, [activeRunId]);

  const fetchArtifacts = async () => {
    try {
      const res = await axios.get(`${API_URL}/skills/ddd/artifacts/${activeRunId}`);
      setArtifacts(res.data);
    } catch (err) {
      console.error("Failed to fetch DDD artifacts", err);
    }
  };

  const fetchConnections = async () => {
    try {
      const res = await axios.get(`${API_URL}/connections`);
      const conns = res.data.connections || [];
      setConnections(conns);
      if (conns.length > 0) setDeployConnId(conns[0].connection_id);
    } catch (err) {
      console.error("Failed to fetch connections", err);
    }
  };

  const runSkill = async (endpoint: string, stateKey: string) => {
    if (!activeRunId) return;
    setLoading(stateKey);
    try {
      const res = await axios.post(`${API_URL}/skills/ddd/${endpoint}`, { run_id: activeRunId });
      setArtifacts((prev: any) => ({ ...prev, [stateKey]: res.data.data }));
    } catch (err) {
      console.error(`Skill ${endpoint} failed`, err);
    } finally {
      setLoading(null);
    }
  };

  const executeDeploy = async () => {
    if (!deployConnId) return alert('Please select a target connection.');
    if (!deployWarehouseName) return alert('Please specify a warehouse name.');
    
    setDeploying(true);
    try {
      const ddl = artifacts.schema_generation?.ddl;
      if (!ddl) throw new Error("No DDL generated");
      
      const res = await axios.post(`${API_URL}/skills/ddd/deploy_ddl`, { 
        ddl,
        conn_id: deployConnId,
        warehouse_name: deployWarehouseName
      });
      if (res.data.success) {
        setDeployed(true);
        setShowDeployModal(false);
      } else {
        alert("Deploy failed: " + res.data.error);
      }
    } catch (err) {
      console.error(err);
      alert("Deployment error: " + err);
    } finally {
      setDeploying(false);
    }
  };

  // Render Mermaid ER Diagram whenever logical_schema is available
  useEffect(() => {
    if (artifacts.conceptual_to_logical?.logical_schema && mermaidRef.current) {
      const renderDiagram = async () => {
        let code = "erDiagram\n";
        const sanitize = (s: string) => s.replace(/[^a-zA-Z0-9_]/g, '_');

        const schema = artifacts.conceptual_to_logical.logical_schema;

        schema.forEach((table: any) => {
          code += `    ${sanitize(table.table_name)} {\n`;
          table.columns?.forEach((c: any) => {
            const pk = c.is_primary_key ? "PK" : "";
            const fk = c.foreign_key_target ? "FK" : "";
            code += `        ${sanitize(c.type?.split('(')[0] || 'string')} ${sanitize(c.name)} ${pk} ${fk}\n`;
          });
          code += "    }\n";
          
          table.columns?.forEach((c: any) => {
            if (c.foreign_key_target) {
                // Determine target table from FK (assuming naming convention or just drawing line)
                // For a robust ER diagram we should parse the target table out.
                // If foreign_key_target is just the column name, we might not know the target table easily without scanning.
                // As a heuristic, if it ends in _id, we look for a table matching that prefix.
                let targetTable = c.foreign_key_target.split('.')[0];
                if (targetTable === c.foreign_key_target) {
                    // Try to infer from column name
                    targetTable = c.name.replace('_id', '');
                }
                
                const exists = schema.some((t:any) => t.table_name === targetTable || sanitize(t.table_name) === sanitize(targetTable));
                if (exists) {
                    code += `    ${sanitize(table.table_name)} }|--|| ${sanitize(targetTable)} : "${sanitize(c.name)}"\n`;
                }
            }
          });
        });

        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          themeVariables: {
            fontSize: '18px',
            primaryColor: '#e2e8f0',
            primaryTextColor: '#0f172a',
            primaryBorderColor: '#94a3b8',
            lineColor: '#64748b',
          }
        });

        try {
          const { svg } = await mermaid.render('unified-er-diagram', code);
          if (mermaidRef.current) mermaidRef.current.innerHTML = svg;
        } catch (e) {
          console.error("Mermaid error", e);
        }
      };
      renderDiagram();
    }
  }, [artifacts.conceptual_to_logical]);

  const getThinkingText = (skill: string) => {
    const texts: any = {
      discover: "Scanning source schemas, inferring domain boundaries from table foreign keys and naming conventions...",
      bounded_contexts: "Applying Strategic DDD heuristics to identify context maps and isolate domain models...",
      ubiquitous_language: "Extracting canonical business terms and generating a unified glossary across contexts...",
      context_mapping: "Determining upstream/downstream dependencies and integration patterns (Conformist, ACL)...",
      aggregate_modeling: "Grouping entities and value objects under distinct Aggregate Roots to enforce invariants...",
      domain_events: "Analyzing temporal columns to infer key business events for CDC and Fact table grain...",
      data_products: "Structuring bounded contexts into deployable Data Mesh products with defined SLAs...",
      grain_definition: "Tying business metrics to analytical grains (e.g. daily snapshot, accumulating snapshot)...",
      dimensional_translation: "Applying Kimball methodologies to translate Aggregates into Conformed Dimensions and Facts...",
      conceptual_to_logical: "Resolving many-to-many relationships, generating surrogate keys, and formalizing the logical Star Schema...",
      schema_generation: "Writing dialect-specific SQL DDL statements, optimizing data types, and ensuring idempotency..."
    };
    return texts[skill] || `Executing AI Skill: ${skill.replace(/_/g, ' ')}`;
  };

  if (!activeRunId) {
    return (
      <div className="glass-panel" style={{ textAlign: 'center', padding: '60px' }}>
        <h2>No Active Catalog</h2>
        <p>Please select a database connection and activate a run first.</p>
      </div>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 80px)', overflowY: 'auto', paddingBottom: '60px' }}>
      {loading && (
        <div 
          onClick={() => setAgentExpanded(!agentExpanded)}
          style={{ 
            position: 'fixed', bottom: '32px', right: '32px', 
            background: 'var(--bg-glass)', border: '1px solid var(--border-glass)', 
            padding: agentExpanded ? '24px' : '16px 24px', 
            borderRadius: '12px', 
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)', zIndex: 1000, 
            backdropFilter: 'blur(10px)',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            width: agentExpanded ? '350px' : 'auto',
            display: 'flex', flexDirection: agentExpanded ? 'column' : 'row',
            alignItems: agentExpanded ? 'flex-start' : 'center', gap: '16px' 
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', width: '100%' }}>
            <Loader2 className="spin" size={24} color="var(--accent-primary)" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Agent is thinking...</div>
              {!agentExpanded && <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Click for details</div>}
            </div>
            {agentExpanded && <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>[Collapse]</div>}
          </div>
          
          {agentExpanded && (
            <div style={{ marginTop: '8px', borderTop: '1px solid var(--border-glass)', paddingTop: '16px', width: '100%' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', marginBottom: '8px', fontWeight: 600 }}>
                Executing AI Skill: {loading.replace(/_/g, ' ')}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                {getThinkingText(loading)}
              </div>
              <div style={{ marginTop: '16px', display: 'flex', gap: '8px', flexDirection: 'column' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <Check size={14} color="var(--success)" /> Compiling Schema Metadata
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <Check size={14} color="var(--success)" /> Connecting to Database
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--accent-primary)' }}>
                  <Loader2 size={14} className="spin" /> Streaming to LLM Agent...
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div style={{ marginBottom: '24px' }}>
        <h1>Data Warehouse Pipeline</h1>
        <p>A cohesive journey from Strategic Domain-Driven Design (Phase A) through Analytical Modeling (Phase B) to Physical Deployment (Phase C).</p>
      </div>

      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-glass)', marginBottom: '32px' }}>
        <button 
          style={{ background: 'none', border: 'none', padding: '12px 16px', color: activeTab === 'phase_a' ? 'var(--accent-primary)' : 'var(--text-secondary)', borderBottom: activeTab === 'phase_a' ? '2px solid var(--accent-primary)' : '2px solid transparent', cursor: 'pointer', fontWeight: activeTab === 'phase_a' ? 600 : 400 }}
          onClick={() => setActiveTab('phase_a')}
        >
          Phase A: Strategic DDD
        </button>
        <button 
          style={{ background: 'none', border: 'none', padding: '12px 16px', color: activeTab === 'phase_b' ? '#3b82f6' : 'var(--text-secondary)', borderBottom: activeTab === 'phase_b' ? '2px solid #3b82f6' : '2px solid transparent', cursor: 'pointer', fontWeight: activeTab === 'phase_b' ? 600 : 400 }}
          onClick={() => setActiveTab('phase_b')}
        >
          Phase B: Analytical Bridge
        </button>
        <button 
          style={{ background: 'none', border: 'none', padding: '12px 16px', color: activeTab === 'phase_c' ? '#10b981' : 'var(--text-secondary)', borderBottom: activeTab === 'phase_c' ? '2px solid #10b981' : '2px solid transparent', cursor: 'pointer', fontWeight: activeTab === 'phase_c' ? 600 : 400 }}
          onClick={() => setActiveTab('phase_c')}
        >
          Phase C: Physical Implementation
        </button>
      </div>

      {/* PHASE A */}
      {activeTab === 'phase_a' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '24px', marginBottom: '48px' }}>
        
        {/* Step 1: Domain Discovery */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Server size={24} color="var(--accent-primary)" />
            <h3>1. Domain Discovery</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Scans schemas to identify core business domains.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('discover', 'discovered_domains')}
            disabled={loading !== null}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px' }}
          >
            {loading === 'discovered_domains' ? <Loader2 size={16} className="spin" /> : <Layers size={16} />}
            Run Discovery
          </button>
          
          {artifacts.discovered_domains && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: 'var(--accent-secondary)' }}>Found {artifacts.discovered_domains.domains?.length || 0} Domains</strong>
            </div>
          )}
        </div>

        {/* Step 2: Bounded Contexts */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Map size={24} color="#f59e0b" />
            <h3>2. Bounded Contexts</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Maps explicit context boundaries to prevent model corruption.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('bounded_contexts', 'bounded_contexts')}
            disabled={loading !== null || !artifacts.discovered_domains}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.discovered_domains ? 1 : 0.5 }}
          >
            {loading === 'bounded_contexts' ? <Loader2 size={16} className="spin" /> : <Map size={16} />}
            Identify Contexts
          </button>
          {artifacts.bounded_contexts && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#f59e0b' }}>Mapped {artifacts.bounded_contexts.bounded_contexts?.length || 0} Contexts</strong>
            </div>
          )}
        </div>

        {/* Step 3: Ubiquitous Language */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <BookOpen size={24} color="#10b981" />
            <h3>3. Ubiquitous Language</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Extracts a canonical business glossary for each context.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('ubiquitous_language', 'ubiquitous_language')}
            disabled={loading !== null || !artifacts.bounded_contexts}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.bounded_contexts ? 1 : 0.5 }}
          >
            {loading === 'ubiquitous_language' ? <Loader2 size={16} className="spin" /> : <BookOpen size={16} />}
            Extract Glossary
          </button>
          {artifacts.ubiquitous_language && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#10b981' }}>Extracted {artifacts.ubiquitous_language.glossary?.length || 0} Glossaries</strong>
            </div>
          )}
        </div>

        {/* Step 4: Context Mapping */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Map size={24} color="#8b5cf6" />
            <h3>4. Context Mapping</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Defines upstream and downstream relationships.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('context_mapping', 'context_mapping')}
            disabled={loading !== null || !artifacts.bounded_contexts}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.bounded_contexts ? 1 : 0.5 }}
          >
            {loading === 'context_mapping' ? <Loader2 size={16} className="spin" /> : <Map size={16} />}
            Map Contexts
          </button>
          {artifacts.context_mapping && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#8b5cf6' }}>Mapped {artifacts.context_mapping.context_map?.length || 0} Relationships</strong>
            </div>
          )}
        </div>

        {/* Step 5: Aggregate Modeling */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Layers size={24} color="#3b82f6" />
            <h3>5. Aggregate Modeling</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Defines aggregates, entities, and value objects.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('aggregate_modeling', 'aggregate_modeling')}
            disabled={loading !== null || !artifacts.bounded_contexts}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.bounded_contexts ? 1 : 0.5 }}
          >
            {loading === 'aggregate_modeling' ? <Loader2 size={16} className="spin" /> : <Layers size={16} />}
            Model Aggregates
          </button>
          {artifacts.aggregate_modeling && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#3b82f6' }}>Modeled {artifacts.aggregate_modeling.aggregates?.length || 0} Aggregates</strong>
            </div>
          )}
        </div>

        {/* Step 6: Domain Events */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Server size={24} color="#ef4444" />
            <h3>6. Domain Events</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Infers key domain events to seed Fact Tables.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('domain_events', 'domain_events')}
            disabled={loading !== null || !artifacts.aggregate_modeling}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.aggregate_modeling ? 1 : 0.5 }}
          >
            {loading === 'domain_events' ? <Loader2 size={16} className="spin" /> : <Server size={16} />}
            Infer Events
          </button>
          {artifacts.domain_events && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#ef4444' }}>Inferred {artifacts.domain_events.domain_events?.length || 0} Events</strong>
            </div>
          )}
        </div>

        {/* Step 7: Data Products */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Server size={24} color="#ec4899" />
            <h3>7. Data Products</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Defines output ports and SLAs (Data Mesh).
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('data_products', 'data_products')}
            disabled={loading !== null || !artifacts.discovered_domains}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.discovered_domains ? 1 : 0.5 }}
          >
            {loading === 'data_products' ? <Loader2 size={16} className="spin" /> : <Server size={16} />}
            Define Products
          </button>
          {artifacts.data_products && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#ec4899' }}>Defined {artifacts.data_products.data_products?.length || 0} Products</strong>
            </div>
          )}
        </div>
      </div>
      </>
      )}

      {/* PHASE B */}
      {activeTab === 'phase_b' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '24px', marginBottom: '48px' }}>
        
        {/* Step 8: Grain Definition */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Server size={24} color="#f59e0b" />
            <h3>8. Grain Definition</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Declares the analytical grain for each process and KPIs.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('grain_definition', 'grain_definition')}
            disabled={loading !== null || !artifacts.aggregate_modeling || !artifacts.domain_events}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: (artifacts.aggregate_modeling && artifacts.domain_events) ? 1 : 0.5 }}
          >
            {loading === 'grain_definition' ? <Loader2 size={16} className="spin" /> : <Server size={16} />}
            Define Grains
          </button>
          {artifacts.grain_definition && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#f59e0b' }}>Defined Grains for {artifacts.grain_definition.processes?.length || 0} Processes</strong>
            </div>
          )}
        </div>

        {/* Step 9: Dimensional Translation */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Network size={24} color="#3b82f6" />
            <h3>9. Dimensional Translation</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Maps DDD aggregates to Kimball Facts and Dimensions.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('dimensional_translation', 'dimensional_translation')}
            disabled={loading !== null || !artifacts.grain_definition}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.grain_definition ? 1 : 0.5 }}
          >
            {loading === 'dimensional_translation' ? <Loader2 size={16} className="spin" /> : <Network size={16} />}
            Translate to Kimball
          </button>
          {artifacts.dimensional_translation && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#3b82f6' }}>Translated {artifacts.dimensional_translation.facts?.length || 0} Facts & {artifacts.dimensional_translation.dimensions?.length || 0} Dimensions</strong>
            </div>
          )}
        </div>

        {/* Step 10: Logical Model */}
        <div className="glass-panel">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <Columns size={24} color="#8b5cf6" />
            <h3>10. Logical Model</h3>
          </div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '0.9rem' }}>
            Generates exact schema with surrogate/foreign keys.
          </p>
          <button 
            className="btn" 
            onClick={() => runSkill('conceptual_to_logical', 'conceptual_to_logical')}
            disabled={loading !== null || !artifacts.dimensional_translation}
            style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.dimensional_translation ? 1 : 0.5 }}
          >
            {loading === 'conceptual_to_logical' ? <Loader2 size={16} className="spin" /> : <Columns size={16} />}
            Generate Logical Model
          </button>
          {artifacts.conceptual_to_logical && (
            <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)', fontSize: '0.85rem' }}>
              <strong style={{ color: '#8b5cf6' }}>Generated Schema with {artifacts.conceptual_to_logical.logical_schema?.length || 0} Tables</strong>
            </div>
          )}
        </div>
      </div>

      {/* ER DIAGRAM (Shows after Step 10) */}
      {artifacts.conceptual_to_logical?.logical_schema && (
        <div className="glass-panel" style={{ marginBottom: '48px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3>📊 Entity Relationship Diagram</h3>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => setZoom(z => Math.max(0.2, z - 0.2))}>Zoom Out</button>
              <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => setZoom(1.0)}>Reset</button>
              <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => setZoom(z => Math.min(3, z + 0.2))}>Zoom In</button>
            </div>
          </div>
          <style>{`
            .mermaid-zoom-container svg {
              max-width: none !important;
              width: 100% !important;
              height: auto !important;
            }
          `}</style>
          <div style={{ overflow: 'auto', background: 'var(--bg-glass)', padding: '24px', borderRadius: '8px', border: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'center', minHeight: '400px' }}>
            <div className="mermaid-zoom-container" style={{ width: `${100 * zoom}%`, transition: 'width 0.2s ease-in-out', minWidth: '100%' }}>
              <div ref={mermaidRef}></div>
            </div>
          </div>
        </div>
      )}
      </>
      )}

      {/* PHASE C */}
      {activeTab === 'phase_c' && (
        <>
          <div className="glass-panel" style={{ marginBottom: '48px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <Database size={24} color="#10b981" />
          <h3>11. Schema Generation & Deployment</h3>
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
          Generate the physical MySQL DDL scripts and automatically deploy them to a target warehouse database.
        </p>
        <button 
          className="btn" 
          onClick={() => runSkill('schema_generation', 'schema_generation')}
          disabled={loading !== null || !artifacts.conceptual_to_logical}
          style={{ width: '300px', display: 'flex', justifyContent: 'center', gap: '8px', opacity: artifacts.conceptual_to_logical ? 1 : 0.5 }}
        >
          {loading === 'schema_generation' ? <Loader2 size={16} className="spin" /> : <Database size={16} />}
          Generate SQL DDL
        </button>

        {artifacts.schema_generation?.ddl && (
          <div style={{ marginTop: '24px' }}>
            <pre style={{ background: '#0f172a', padding: '24px', borderRadius: '8px', color: '#e0f2fe', overflowX: 'auto', marginBottom: '16px', fontSize: '14px', lineHeight: '1.5', border: '1px solid #1e293b', maxHeight: '400px' }}>
              {artifacts.schema_generation.ddl}
            </pre>
            
            {deployed ? (
              <div style={{ padding: '16px', background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', border: '1px solid var(--success)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                <Check size={20} /> Data Warehouse schema successfully deployed!
              </div>
            ) : (
              <button className="btn btn-danger" onClick={() => setShowDeployModal(true)} disabled={deploying}>
                <Play size={18} /> Deploy to Target Database
              </button>
            )}
          </div>
        )}
      </div>
      </>
      )}

      {/* Deployment Modal */}
      {showDeployModal && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel modal-content" style={{ width: '100%', maxWidth: '500px', padding: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h2 style={{ margin: 0 }}>Deploy Data Warehouse</h2>
              <button onClick={() => setShowDeployModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', fontSize: '1.5rem' }}>
                ×
              </button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Target Connection</label>
                <select className="input-field" value={deployConnId} onChange={e => setDeployConnId(e.target.value)}>
                  {connections.map(c => (
                    <option key={c.connection_id} value={c.connection_id}>{c.name} ({c.db_type})</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Warehouse / Schema Name</label>
                <input type="text" className="input-field" value={deployWarehouseName} onChange={e => setDeployWarehouseName(e.target.value)} placeholder="edw_production" />
                <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>The AI will create this database if it doesn't exist.</p>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
                <button className="btn btn-secondary" onClick={() => setShowDeployModal(false)}>Cancel</button>
                <button className="btn btn-danger" onClick={executeDeploy} disabled={deploying}>
                  {deploying ? <Loader2 size={18} className="spin" /> : <Play size={18} />} 
                  Execute DDL
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
