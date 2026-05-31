import { useState, useEffect } from 'react';
import { Database, MessageSquare, BarChart2, ShieldAlert, Settings, LayoutDashboard, Moon, Sun, Droplet, Search } from 'lucide-react';
import ConnectionsScreen from './components/ConnectionsScreen';
import ChatScreen from './components/ChatScreen';
import ModelerScreen from './components/ModelerScreen';
import PHIDashboardScreen from './components/PHIDashboardScreen';
import DWPipelineScreen from './components/DWPipelineScreen';

function App() {
  const [currentScreen, setCurrentScreen] = useState('connections');
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const renderScreen = () => {
    switch (currentScreen) {
      case 'connections':
        return <ConnectionsScreen onRunSelect={setActiveRunId} onNavigate={setCurrentScreen} activeRunId={activeRunId} />;
      case 'chat':
        return <ChatScreen activeRunId={activeRunId} />;
      case 'modeler':
        return <ModelerScreen activeRunId={activeRunId} />;
      case 'edw_architect':
        return <EDWArchitectScreen activeRunId={activeRunId} />;
      case 'phi_dashboard':
        return <PHIDashboardScreen activeRunId={activeRunId} />;
      case 'dw_pipeline':
        return <DWPipelineScreen activeRunId={activeRunId} />;
      default:
        return <ConnectionsScreen onRunSelect={setActiveRunId} onNavigate={setCurrentScreen} activeRunId={activeRunId} />;
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem', paddingBottom: '16px', borderBottom: '1px solid var(--border-glass)' }}>
          <Database size={24} color="var(--accent-secondary)" /> AI Catalog Agent
        </h2>
        
        <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div className={`nav-item ${currentScreen === 'connections' ? 'active' : ''}`} onClick={() => setCurrentScreen('connections')}>
            <Settings size={20} /> Connections
          </div>
          <div className={`nav-item ${currentScreen === 'chat' ? 'active' : ''}`} onClick={() => setCurrentScreen('chat')}>
            <MessageSquare size={20} /> Agent Chat
          </div>
          <div className={`nav-item ${currentScreen === 'modeler' ? 'active' : ''}`} onClick={() => setCurrentScreen('modeler')}>
            <BarChart2 size={20} /> Data Modeler
          </div>
          <div className={`nav-item ${currentScreen === 'dw_pipeline' ? 'active' : ''}`} onClick={() => setCurrentScreen('dw_pipeline')}>
            <LayoutDashboard size={20} /> Data Warehouse Pipeline
          </div>
          <div className={`nav-item ${currentScreen === 'phi_dashboard' ? 'active' : ''}`} onClick={() => setCurrentScreen('phi_dashboard')}>
            <ShieldAlert size={20} /> PHI Dashboard
          </div>
        </div>

        <div style={{ marginTop: 'auto', padding: '16px', background: 'var(--bg-glass)', borderRadius: '8px', fontSize: '0.85rem' }}>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>Active Catalog Run</div>
          <div style={{ color: activeRunId ? 'var(--success)' : 'var(--danger)', fontWeight: 600, wordBreak: 'break-all' }}>
            {activeRunId ? `${activeRunId.substring(0,8)}...` : 'None Selected'}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', marginTop: '16px' }}>
          <button className={`theme-btn ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')} title="Dark Theme">
            <Moon size={16} />
          </button>
          <button className={`theme-btn ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')} title="Light Theme">
            <Sun size={16} />
          </button>
          <button className={`theme-btn ${theme === 'ocean' ? 'active' : ''}`} onClick={() => setTheme('ocean')} title="Ocean Theme">
            <Droplet size={16} />
          </button>
        </div>
      </aside>

      <main className="main-content">
        {renderScreen()}
      </main>
    </div>
  );
}

export default App;
