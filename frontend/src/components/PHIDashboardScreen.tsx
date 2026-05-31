import { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, Info, Search } from 'lucide-react';

interface PHIColumn {
  Database_Name: string;
  Table_Name: string;
  Column_Name: string;
  PHI_Type: string;
}

export default function PHIDashboardScreen({ activeRunId }: { activeRunId: string | null }) {
  const [data, setData] = useState<PHIColumn[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [dbSearch, setDbSearch] = useState('');
  const [tableSearch, setTableSearch] = useState('');
  const [colSearch, setColSearch] = useState('');

  const API_URL = 'http://localhost:8000/api';

  useEffect(() => {
    if (activeRunId) fetchPHI();
  }, [activeRunId]);

  const fetchPHI = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_URL}/runs/${activeRunId}/phi`);
      setData(res.data.phi_columns || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!activeRunId) {
    return (
      <div className="glass-panel" style={{ textAlign: 'center', padding: '60px' }}>
        <Info size={48} color="var(--accent-secondary)" style={{ marginBottom: '16px' }} />
        <h2>No Active Catalog</h2>
        <p>Please select a database connection and activate a run first.</p>
      </div>
    );
  }

  const filteredData = data.filter(r => 
    r.Database_Name.toLowerCase().includes(dbSearch.toLowerCase()) &&
    r.Table_Name.toLowerCase().includes(tableSearch.toLowerCase()) &&
    r.Column_Name.toLowerCase().includes(colSearch.toLowerCase())
  );

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
        <ShieldAlert size={40} color="var(--danger)" />
        <div>
          <h1 style={{ margin: 0 }}>PHI Dashboard</h1>
          <p style={{ margin: 0 }}>Review all Protected Health Information (PHI) columns identified by the AI profiler.</p>
        </div>
      </div>

      <div className="glass-panel">
        <div className="grid-3" style={{ marginBottom: '24px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--text-secondary)" style={{ position: 'absolute', top: '14px', left: '14px' }} />
            <input 
              className="input-field" 
              style={{ paddingLeft: '40px' }} 
              placeholder="Search Database..." 
              value={dbSearch}
              onChange={e => setDbSearch(e.target.value)}
            />
          </div>
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--text-secondary)" style={{ position: 'absolute', top: '14px', left: '14px' }} />
            <input 
              className="input-field" 
              style={{ paddingLeft: '40px' }} 
              placeholder="Search Table..." 
              value={tableSearch}
              onChange={e => setTableSearch(e.target.value)}
            />
          </div>
          <div style={{ position: 'relative' }}>
            <Search size={16} color="var(--text-secondary)" style={{ position: 'absolute', top: '14px', left: '14px' }} />
            <input 
              className="input-field" 
              style={{ paddingLeft: '40px' }} 
              placeholder="Search Column..." 
              value={colSearch}
              onChange={e => setColSearch(e.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <p>Loading PHI data...</p>
        ) : filteredData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            <ShieldAlert size={32} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p>No PHI columns found matching your criteria.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <div style={{ marginBottom: '16px', fontWeight: 500, color: 'var(--accent-secondary)' }}>
              Found {filteredData.length} PHI Columns
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Database Name</th>
                  <th>Table Name</th>
                  <th>Column Name</th>
                  <th>PHI Type</th>
                </tr>
              </thead>
              <tbody>
                {filteredData.map((row, i) => (
                  <tr key={i}>
                    <td>{row.Database_Name}</td>
                    <td>{row.Table_Name}</td>
                    <td>{row.Column_Name}</td>
                    <td><span style={{ background: 'rgba(239, 68, 68, 0.2)', color: 'var(--danger)', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 600 }}>{row.PHI_Type}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
