import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { BarChart2, Loader2, Info } from 'lucide-react';
import mermaid from 'mermaid';

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

interface ProposedFact {
  schema: string;
  table: string;
  scores: { fact: number };
}

interface ProposedDim {
  schema: string;
  table: string;
  scores: { dim: number };
}

export default function ModelerScreen({ activeRunId }: { activeRunId: string | null }) {
  const [kpi, setKpi] = useState('');
  const [loading, setLoading] = useState(false);
  const [modelRes, setModelRes] = useState<any>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('diagram');
  const [zoom, setZoom] = useState(1);
  
  const mermaidRef = useRef<HTMLDivElement>(null);
  const API_URL = 'http://localhost:8000/api';

  const handleGenerate = async () => {
    if (!kpi || !activeRunId) return;
    setLoading(true);
    setError('');
    setModelRes(null);
    try {
      const res = await axios.post(`${API_URL}/kpi-to-model`, {
        run_id: activeRunId,
        kpi
      });
      setModelRes(res.data);
    } catch (err: any) {
      setError(err.message || 'Failed to generate model');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'diagram' && modelRes && mermaidRef.current) {
      const renderDiagram = async () => {
        let code = "erDiagram\n";
        const facts: ProposedFact[] = modelRes.proposed_facts || [];
        const dims: ProposedDim[] = modelRes.proposed_dimensions || [];
        
        facts.forEach(f => {
          code += `    ${f.table} {\n        int id PK\n        string role "FACT"\n    }\n`;
          dims.forEach(d => {
            code += `    ${f.table} ||--o{ ${d.table} : references\n`;
          });
        });
        dims.forEach(d => {
          code += `    ${d.table} {\n        int id PK\n        string role "DIM"\n    }\n`;
        });

        try {
          const { svg } = await mermaid.render('mermaid-svg', code);
          if (mermaidRef.current) {
            mermaidRef.current.innerHTML = svg;
          }
        } catch (e) {
          console.error("Mermaid error", e);
        }
      };
      renderDiagram();
    }
  }, [activeTab, modelRes]);

  if (!activeRunId) {
    return (
      <div className="glass-panel" style={{ textAlign: 'center', padding: '60px' }}>
        <Info size={48} color="var(--accent-secondary)" style={{ marginBottom: '16px' }} />
        <h2>No Active Catalog</h2>
        <p>Please select a database connection and activate a run first.</p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h1>Data Modeler</h1>
        <p>Generate semantic data models and visualize entity relationships based on your reporting requirements.</p>
      </div>

      <div className="glass-panel" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <input 
            type="text" 
            className="input-field" 
            placeholder="Enter a Reporting Requirement or KPI (e.g., 'monthly patient appointments')" 
            value={kpi}
            onChange={e => setKpi(e.target.value)}
          />
          <button className="btn" onClick={handleGenerate} disabled={loading || !kpi}>
            {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <BarChart2 size={18} />}
            Generate Model
          </button>
        </div>
        {error && <div style={{ color: 'var(--danger)', marginTop: '12px' }}>{error}</div>}
      </div>

      {modelRes && (
        <div className="glass-panel">
          <div className="tabs">
            <div className={`tab ${activeTab === 'diagram' ? 'active' : ''}`} onClick={() => setActiveTab('diagram')}>🏗️ Architecture Diagram</div>
            <div className={`tab ${activeTab === 'entities' ? 'active' : ''}`} onClick={() => setActiveTab('entities')}>🗂️ Proposed Entities</div>
            <div className={`tab ${activeTab === 'semantic' ? 'active' : ''}`} onClick={() => setActiveTab('semantic')}>📝 Semantic Layer</div>
          </div>

          <div style={{ padding: '16px 0' }}>
            {activeTab === 'diagram' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.85rem' }} onClick={() => setZoom(z => Math.max(0.2, z - 0.2))}>Zoom Out</button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.85rem' }} onClick={() => setZoom(1)}>Reset</button>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.85rem' }} onClick={() => setZoom(z => Math.min(3, z + 0.2))}>Zoom In</button>
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

            {activeTab === 'entities' && (
              <div className="grid-2">
                <div>
                  <h3>📈 Proposed Facts</h3>
                  <table className="data-table">
                    <thead><tr><th>Schema</th><th>Table</th><th>Score</th></tr></thead>
                    <tbody>
                      {(modelRes.proposed_facts || []).map((f: ProposedFact, i: number) => (
                        <tr key={i}><td>{f.schema}</td><td>{f.table}</td><td>{f.scores.fact.toFixed(2)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div>
                  <h3>🧩 Proposed Dimensions</h3>
                  <table className="data-table">
                    <thead><tr><th>Schema</th><th>Table</th><th>Score</th></tr></thead>
                    <tbody>
                      {(modelRes.proposed_dimensions || []).map((d: ProposedDim, i: number) => (
                        <tr key={i}><td>{d.schema}</td><td>{d.table}</td><td>{d.scores.dim.toFixed(2)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'semantic' && (() => {
              const formatSemanticModel = (content: any) => {
                if (!content) return 'No semantic model generated.';
                if (typeof content === 'string') {
                  try {
                    const cleaned = content.replace(/^```(json|yaml|)\n?/i, '').replace(/```$/i, '').trim();
                    const parsed = JSON.parse(cleaned);
                    if (parsed.yaml) return parsed.yaml;
                    return JSON.stringify(parsed, null, 2);
                  } catch (e) {
                    return content.replace(/\\n/g, '\n');
                  }
                }
                return JSON.stringify(content, null, 2);
              };

              return (
                <pre style={{ background: '#0f172a', padding: '24px', borderRadius: '8px', color: '#e0f2fe', overflowX: 'auto', marginBottom: '16px', fontSize: '16px', lineHeight: '1.5', border: '1px solid #1e293b', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.2)' }}>
                  {formatSemanticModel(modelRes.semantic_layer_model)}
                </pre>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}
