import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, Terminal, Loader2, Info, MessageSquare } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  data?: any[];
  provider?: string;
  confidence?: string;
}

export default function ChatScreen({ activeRunId }: { activeRunId: string | null }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const API_URL = 'http://localhost:8000/api';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (activeRunId) {
      axios.get(`${API_URL}/chat/messages/${activeRunId}`).then(res => {
        if (res.data.messages) {
          const msgs = res.data.messages.map((m: any) => ({
            role: m.role,
            content: m.content,
            sql: m.sql_query,
            data: m.data_json ? JSON.parse(m.data_json) : undefined,
            provider: m.provider,
            confidence: m.confidence
          }));
          setMessages(msgs);
        }
      }).catch(err => console.error("Failed to fetch chat history", err));
    }
  }, [activeRunId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !activeRunId) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // Save user message to history
      await axios.post(`${API_URL}/chat/messages`, {
        run_id: activeRunId,
        role: 'user',
        content: userMsg.content
      });
      // 1. Get proposed SQL
      const askRes = await axios.post(`${API_URL}/ask`, {
        run_id: activeRunId,
        question: userMsg.content,
        context: {}
      });

      const { sql, action, clarification_question, answer, provider_used, confidence } = askRes.data;
      
      let replyContent = "Here are the results:";
      if (action === "CLARIFY") replyContent = clarification_question || "I need more info.";
      if (action === "ANSWER") replyContent = answer || "I processed your request.";

      let rowData: any[] = [];
      
      // 2. Execute SQL if available
      if (sql) {
        try {
          const queryRes = await axios.post(`${API_URL}/query/execute`, { sql });
          if (queryRes.data.rows) {
            rowData = queryRes.data.rows;
          }
        } catch (err) {
          console.error("SQL Execution failed", err);
        }
      }

      const asstMsg: Message = {
        role: 'assistant',
        content: replyContent,
        sql,
        data: rowData.length > 0 ? rowData : undefined,
        provider: provider_used,
        confidence: String(confidence)
      };
      setMessages(prev => [...prev, asstMsg]);

      // Save AI message to history
      await axios.post(`${API_URL}/chat/messages`, {
        run_id: activeRunId,
        role: 'assistant',
        content: replyContent,
        sql_query: sql,
        data_json: rowData.length > 0 ? JSON.stringify(rowData) : null,
        provider: provider_used,
        confidence: String(confidence)
      });

    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const renderDataDisplay = (data: any[]) => {
    if (!data || data.length === 0) return null;
    
    const keys = Object.keys(data[0]);
    // Determine if we can render a simple bar chart
    let chartable = false;
    let xAxisKey = '';
    let yAxisKey = '';
    
    if (keys.length >= 2) {
      const stringKeys = keys.filter(k => typeof data[0][k] === 'string');
      const numberKeys = keys.filter(k => typeof data[0][k] === 'number');
      if (stringKeys.length > 0 && numberKeys.length > 0) {
        chartable = true;
        xAxisKey = stringKeys[0];
        yAxisKey = numberKeys[0];
      }
    }

    return (
      <div style={{ marginTop: '16px' }}>
        {chartable && data.length > 1 && (
          <div style={{ height: '300px', marginBottom: '24px', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '8px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data}>
                <XAxis dataKey={xAxisKey} stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip contentStyle={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-glass)' }} />
                <Bar dataKey={yAxisKey} fill="var(--accent-primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        
        <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
          <table className="data-table">
            <thead>
              <tr>
                {keys.map(k => <th key={k}>{k}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.slice(0, 10).map((row, i) => (
                <tr key={i}>
                  {keys.map(k => <td key={k}>{String(row[k])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          {data.length > 10 && <div style={{ padding: '8px 16px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Showing 10 of {data.length} rows...</div>}
        </div>
      </div>
    );
  };

  if (!activeRunId) {
    return (
      <div className="glass-panel" style={{ textAlign: 'center', padding: '60px' }}>
        <Info size={48} color="var(--accent-secondary)" style={{ marginBottom: '16px' }} />
        <h2>No Active Catalog</h2>
        <p>Please select a database connection and activate a run before chatting.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)' }}>
      <div>
        <h1>Agent Chat</h1>
        <p>Ask natural language questions to query the database safely.</p>
      </div>

      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 0 }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {messages.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
              <MessageSquare size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
              <h3>Start a conversation</h3>
              <p>Try asking: "How many active users do we have?"</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role === 'user' ? 'chat-user' : 'chat-assistant'}`}>
                {msg.role === 'assistant' && (
                  <div style={{ minWidth: '40px', display: 'flex', justifyContent: 'center' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 'bold' }}>
                      AI
                    </div>
                  </div>
                )}
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <div style={{ fontWeight: 600, marginBottom: '4px', color: msg.role === 'user' ? 'var(--accent-secondary)' : 'var(--text-primary)' }}>
                    {msg.role === 'user' ? 'You' : 'AI Agent'}
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  
                  {msg.sql && (
                    <div style={{ marginTop: '16px' }}>
                      <details style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                        <summary style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
                          <Terminal size={16} /> View Generated SQL (Provider: {msg.provider}, Confidence: {msg.confidence})
                        </summary>
                        <pre style={{ marginTop: '12px', color: '#10b981', overflowX: 'auto' }}>
                          {msg.sql}
                        </pre>
                      </details>
                    </div>
                  )}

                  {msg.data && renderDataDisplay(msg.data)}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '20px' }}>
              <Loader2 size={24} color="var(--accent-primary)" style={{ animation: 'spin 1s linear infinite' }} />
              <span style={{ color: 'var(--text-secondary)', marginLeft: '8px' }}>Agent is thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ padding: '24px', borderTop: '1px solid var(--border-glass)', background: 'rgba(0,0,0,0.2)' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '12px' }}>
            <input 
              type="text" 
              className="input-field" 
              placeholder="E.g. What were our top 5 products last month?" 
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={loading}
              style={{ padding: '16px' }}
            />
            <button type="submit" className="btn" disabled={loading} style={{ padding: '0 24px' }}>
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
