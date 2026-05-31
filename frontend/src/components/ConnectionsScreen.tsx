import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Database, Play, History, Loader2, Search, Plus, X, Terminal, Server } from 'lucide-react';

interface Run {
  run_id: string;
  created_at: string;
}

interface Connection {
  connection_id: string;
  name: string;
  db_type: string;
  host: string;
  database_name: string;
}

interface LogEntry {
  log_id: number;
  timestamp: string;
  level: string;
  message: string;
}

export default function ConnectionsScreen({ onRunSelect, onNavigate, activeRunId }: { onRunSelect: (id: string) => void, onNavigate: (screen: string) => void, activeRunId: string | null }) {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedConn, setSelectedConn] = useState<Connection | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [showNewConnModal, setShowNewConnModal] = useState(false);
  
  // New connection form
  const [formData, setFormData] = useState({
    name: '', db_type: 'mysql', host: '', port: 3306, username: '', password: '', database_name: ''
  });

  // Live Logs
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [pollingRunId, setPollingRunId] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const API_URL = 'http://localhost:8000/api';

  useEffect(() => {
    fetchConnections();
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (pollingRunId) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_URL}/runs/${pollingRunId}/logs`);
          setLogs(res.data.logs || []);
          
          // Check if finished
          const lastLog = res.data.logs[res.data.logs.length - 1];
          if (lastLog && (lastLog.level === 'SUCCESS' || lastLog.level === 'ERROR')) {
            setAnalyzing(false);
            setPollingRunId(null);
            if (lastLog.level === 'SUCCESS') {
              onRunSelect(pollingRunId);
              // Wait a bit before redirecting
              setTimeout(() => onNavigate('chat'), 1500);
            }
          }
        } catch (e) {
          console.error(e);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [pollingRunId]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchConnections = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${API_URL}/connections`);
      setConnections(res.data.connections || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch connections');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectConn = async (conn: Connection) => {
    setSelectedConn(conn);
    try {
      const res = await axios.get(`${API_URL}/runs/${conn.database_name}`); // Alternatively filter runs by conn_id on backend if updated
      setRuns(res.data.runs || []);
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleStartAnalysis = async () => {
    if (!selectedConn) return;
    setAnalyzing(true);
    setLogs([]);
    try {
      const res = await axios.post(`${API_URL}/analyze`, {
        conn_id: selectedConn.connection_id,
        include_schemas: [selectedConn.database_name]
      });
      if (res.data.run_id) {
        setPollingRunId(res.data.run_id);
      }
    } catch (err: any) {
      setError(err.message || 'Analysis failed to start');
      setAnalyzing(false);
    }
  };

  const handleSaveConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/connections`, formData);
      setShowNewConnModal(false);
      fetchConnections();
    } catch (err: any) {
      setError(err.message || 'Failed to save connection');
    }
  };

  if (analyzing || pollingRunId) {
    return (
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <Loader2 size={48} color="var(--accent-secondary)" style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} />
          <h2 style={{ marginTop: '24px' }}>Analyzing {selectedConn?.name || 'Database'}</h2>
          <p>The AI Agent is processing metadata in the background...</p>
        </div>
        
        <div style={{ flex: 1, background: '#000', borderRadius: '8px', padding: '16px', overflowY: 'auto', fontFamily: 'monospace', color: '#0f0', border: '1px solid #333' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid #333', paddingBottom: '12px', marginBottom: '12px' }}>
            <Terminal size={18} color="#fff" />
            <span style={{ color: '#fff', fontWeight: 'bold' }}>Agent Terminal</span>
          </div>
          {logs.map((log) => (
            <div key={log.log_id} className="terminal-log" style={{ marginBottom: '8px', color: log.level === 'ERROR' ? '#f87171' : log.level === 'SUCCESS' ? '#4ade80' : '#a3e635' }}>
              <span style={{ color: '#888', marginRight: '8px' }}>[{new Date(log.timestamp).toLocaleTimeString()}]</span>
              <span style={{ fontWeight: 'bold', marginRight: '8px' }}>[{log.level}]</span>
              {log.message}
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Database Connections</h1>
          <p>Connect to a data source to generate its AI-powered Data Catalog.</p>
        </div>
        {!selectedConn && (
          <button className="btn" onClick={() => setShowNewConnModal(true)}>
            <Plus size={18} /> New Connection
          </button>
        )}
      </div>

      {error && <div style={{ color: 'var(--danger)', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)', borderRadius: '8px', margin: '16px 0' }}>{error}</div>}

      {!selectedConn ? (
        <div className="grid-3" style={{ marginTop: '24px' }}>
          {loading ? (
            <p>Loading connections...</p>
          ) : connections.length === 0 ? (
            <p style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', background: 'var(--bg-glass)', borderRadius: '12px' }}>
              No connections found. Click "New Connection" to add one.
            </p>
          ) : (
            connections.map(conn => (
              <div key={conn.connection_id} className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Server size={32} color={conn.db_type === 'redshift' ? '#f87171' : conn.db_type === 'sqlserver' ? '#60a5fa' : '#34d399'} />
                  <div>
                    <h3 style={{ margin: 0 }}>{conn.name}</h3>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{conn.db_type.toUpperCase()} • {conn.database_name}</p>
                  </div>
                </div>
                <button className="btn" onClick={() => handleSelectConn(conn)} style={{ width: '100%' }}>
                  View Analysis
                </button>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="glass-panel" style={{ marginTop: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <div>
              <h2>{selectedConn.name}</h2>
              <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{selectedConn.db_type.toUpperCase()} • {selectedConn.host} • {selectedConn.database_name}</p>
            </div>
            <button className="btn btn-secondary" onClick={() => setSelectedConn(null)}>Back to Connections</button>
          </div>

          <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div style={{ padding: '32px', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '12px', border: '1px solid rgba(59, 130, 246, 0.2)', textAlign: 'center' }}>
                <Database size={48} color="var(--accent-primary)" style={{ marginBottom: '16px' }} />
                <h3>Run AI Catalog Agent</h3>
                <p style={{ marginBottom: '24px', color: 'var(--text-secondary)' }}>Crawl metadata, profile for sensitive data, and rebuild AI embeddings for semantic search.</p>
                <button className="btn" onClick={handleStartAnalysis} style={{ padding: '12px 24px', fontSize: '1.1rem' }}>
                  <Play size={20} /> Start Analysis
                </button>
              </div>
            </div>

            <div style={{ flex: 1 }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <History size={20} /> Previous Runs
              </h3>
              {runs.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                  No previous analysis runs found.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {runs.map(run => (
                    <div key={run.run_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: 'var(--bg-secondary)', borderRadius: '8px', border: activeRunId === run.run_id ? '1px solid var(--success)' : '1px solid var(--border-glass)' }}>
                      <div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>ID: {run.run_id.substring(0,8)}...</div>
                        <div style={{ fontWeight: 500 }}>{new Date(run.created_at).toLocaleString()}</div>
                      </div>
                      <button 
                        className="btn btn-secondary" 
                        onClick={() => {
                          onRunSelect(run.run_id);
                          onNavigate('chat');
                        }}
                      >
                        {activeRunId === run.run_id ? 'Active' : 'Activate'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* New Connection Modal */}
      {showNewConnModal && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel modal-content" style={{ width: '100%', maxWidth: '500px', padding: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h2 style={{ margin: 0 }}>Add New Connection</h2>
              <button onClick={() => setShowNewConnModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer' }}>
                <X size={24} />
              </button>
            </div>
            
            <form onSubmit={handleSaveConnection} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Connection Name</label>
                <input required type="text" className="input-field" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="Production MySQL" />
              </div>
              
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Database Type</label>
                <select className="input-field" value={formData.db_type} onChange={e => setFormData({...formData, db_type: e.target.value})}>
                  <option value="mysql">MySQL</option>
                  <option value="sqlserver">SQL Server</option>
                  <option value="redshift">Amazon Redshift</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 2 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Host</label>
                  <input required type="text" className="input-field" value={formData.host} onChange={e => setFormData({...formData, host: e.target.value})} placeholder="localhost" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Port</label>
                  <input required type="number" className="input-field" value={formData.port} onChange={e => setFormData({...formData, port: parseInt(e.target.value)})} placeholder="3306" />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Database Name</label>
                <input required type="text" className="input-field" value={formData.database_name} onChange={e => setFormData({...formData, database_name: e.target.value})} placeholder="my_database" />
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Username</label>
                  <input required type="text" className="input-field" value={formData.username} onChange={e => setFormData({...formData, username: e.target.value})} placeholder="admin" />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>Password</label>
                  <input required type="password" className="input-field" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} placeholder="••••••••" />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowNewConnModal(false)}>Cancel</button>
                <button type="submit" className="btn">Save Connection</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
