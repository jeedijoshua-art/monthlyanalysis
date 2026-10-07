import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, Database, ChevronRight, FileSpreadsheet, AlertTriangle, CheckCircle2, Code, Search, LogOut, Clock, X } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie } from 'recharts';

const API_URL = 'http://localhost:8000/api';

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<{email: string, id: number} | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [datasets, setDatasets] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedDatasets, setSelectedDatasets] = useState<number[]>([]);
  const [showEvidence, setShowEvidence] = useState(false);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
      fetchDatasets();
      fetchHistory();
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const res = await axios.get(`${API_URL}/auth/me`);
      setUser(res.data);
    } catch {
      handleLogout();
    }
  };

  const fetchDatasets = async () => {
    try {
      const res = await axios.get(`${API_URL}/datasets`);
      setDatasets(res.data);
      if (res.data.length > 0 && selectedDatasets.length === 0) {
        setSelectedDatasets([res.data[0].id]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_URL}/history`);
      setHistory(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await axios.post(`${API_URL}/auth/${authMode}`, { email, password });
      localStorage.setItem('token', res.data.access_token);
      setToken(res.data.access_token);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Authentication failed");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setDatasets([]);
    setHistory([]);
    setResult(null);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    setUploading(true);
    setError(null);
    try {
      await axios.post(`${API_URL}/upload`, formData);
      await fetchDatasets();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async (q: string = question) => {
    if (!q.trim()) return;
    if (selectedDatasets.length === 0) {
      setError("Please select at least one dataset.");
      return;
    }
    
    setQuestion(q);
    setAsking(true);
    setError(null);
    setResult(null);
    setShowEvidence(false);
    
    try {
      const res = await axios.post(`${API_URL}/ask`, {
        question: q,
        dataset_ids: selectedDatasets
      });
      setResult(res.data);
      await fetchHistory();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Analysis failed");
    } finally {
      setAsking(false);
    }
  };

  const toggleDataset = (id: number) => {
    if (selectedDatasets.includes(id)) {
      setSelectedDatasets(selectedDatasets.filter(d => d !== id));
    } else {
      setSelectedDatasets([...selectedDatasets, id]);
    }
  };

  const renderChart = () => {
    if (!result?.evidence?.visualization || !result.result || typeof result.result !== 'object') return null;
    const data = Array.isArray(result.result) ? result.result : 
                 (typeof result.result === 'object' && result.result !== null ? 
                  Object.entries(result.result).map(([k, v]) => ({ name: k, value: v })) : []);
    if (data.length === 0) return null;

    const visType = result.evidence.visualization.toLowerCase();
    
    return (
      <div className="h-64 mt-4 w-full bg-slate-800 p-4 rounded-lg border border-slate-700">
        <ResponsiveContainer width="100%" height="100%">
          {visType === 'bar' ? (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155' }} />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          ) : visType === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155' }} />
              <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
            </LineChart>
          ) : (
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} fill="#3b82f6" label />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155' }} />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    );
  };

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900 text-slate-200">
        <div className="bg-slate-800 p-8 rounded-xl shadow-2xl border border-slate-700 w-full max-w-md">
          <div className="flex items-center justify-center gap-2 mb-6">
            <Database className="text-blue-500" size={32} />
            <h1 className="text-3xl font-bold text-white tracking-tight">DataProof AI</h1>
          </div>
          <h2 className="text-xl mb-6 text-center">{authMode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
          
          {error && <div className="bg-red-500/20 text-red-300 p-3 rounded mb-4 text-sm">{error}</div>}
          
          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1 text-slate-400">Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)} 
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 text-slate-400">Password</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)} 
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-white focus:ring-2 focus:ring-blue-500" />
            </div>
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition-colors">
              {authMode === 'login' ? 'Log In' : 'Sign Up'}
            </button>
          </form>
          
          <div className="mt-4 text-center text-sm text-slate-400">
            {authMode === 'login' ? "Don't have an account? " : "Already have an account? "}
            <button onClick={() => {setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(null)}} className="text-blue-400 hover:underline">
              {authMode === 'login' ? 'Sign up' : 'Log in'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-900 text-slate-200 font-sans">
      {/* Sidebar */}
      <div className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-5 border-b border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="text-blue-500" />
            <h1 className="text-xl font-bold text-white tracking-tight">DataProof AI</h1>
          </div>
          <button onClick={handleLogout} className="text-slate-400 hover:text-white" title="Logout">
            <LogOut size={18} />
          </button>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto space-y-6">
          <div>
            <h2 className="text-xs uppercase text-slate-400 font-semibold mb-3 tracking-wider flex items-center justify-between">
              Your Datasets
            </h2>
            <div className="space-y-2">
              {datasets.map((dataset) => {
                const isSelected = selectedDatasets.includes(dataset.id);
                return (
                  <div key={dataset.id} onClick={() => toggleDataset(dataset.id)}
                    className={`p-3 rounded-lg cursor-pointer transition-colors border ${isSelected ? 'bg-blue-900/30 border-blue-500/50' : 'bg-slate-700/50 border-transparent hover:bg-slate-700'}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <FileSpreadsheet size={16} className={isSelected ? "text-blue-400" : "text-slate-400"} />
                      <span className={`font-medium truncate ${isSelected ? "text-blue-200" : "text-slate-200"}`}>{dataset.filename}</span>
                    </div>
                    <div className="text-xs text-slate-400 flex justify-between">
                      <span>{dataset.profile.rows.toLocaleString()} rows</span>
                      <span className={dataset.profile.columns_info && Object.values(dataset.profile.columns_info).some((c: any) => c.missing > 0) ? "text-orange-400" : "text-emerald-400"}>
                        {dataset.profile.columns_info && Object.values(dataset.profile.columns_info).some((c: any) => c.missing > 0) ? "Messy data" : "Clean"}
                      </span>
                    </div>
                  </div>
                );
              })}
              {datasets.length === 0 && <div className="text-sm text-slate-500 italic p-2">No datasets uploaded yet.</div>}
            </div>
          </div>

          <div>
            <h2 className="text-xs uppercase text-slate-400 font-semibold mb-3 tracking-wider flex items-center gap-1">
              <Clock size={14}/> Recent Analysis
            </h2>
            <div className="space-y-2">
              {history.map((h) => (
                <div key={h.id} onClick={() => { setQuestion(h.question); handleAsk(h.question); }}
                  className="text-sm bg-slate-700/30 p-2 rounded cursor-pointer hover:bg-slate-700 border border-transparent hover:border-slate-600 truncate text-slate-300">
                  "{h.question}"
                </div>
              ))}
              {history.length === 0 && <div className="text-sm text-slate-500 italic p-2">No history.</div>}
            </div>
          </div>
        </div>
        
        <div className="p-4 border-t border-slate-700">
          <label className="flex items-center justify-center gap-2 w-full bg-slate-700 hover:bg-slate-600 text-white p-2.5 rounded-lg cursor-pointer transition-colors border border-slate-600">
            <Upload size={18} />
            <span className="font-medium text-sm">Upload Dataset</span>
            <input type="file" className="hidden" accept=".csv,.xlsx" onChange={handleUpload} disabled={uploading} />
          </label>
          {uploading && <div className="text-xs text-center mt-2 text-slate-400 animate-pulse">Uploading and profiling...</div>}
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <div className="p-6 max-w-4xl w-full mx-auto flex-1 overflow-y-auto flex flex-col">
          
          <div className="mb-8 mt-4 text-center">
            <h2 className="text-3xl font-bold text-white mb-2">Ask your data anything</h2>
            <p className="text-slate-400">Generate verified answers powered by Python</p>
          </div>
          
          {/* Search Box */}
          <div className="relative mb-8 shadow-lg shadow-black/20 rounded-xl">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <Search className="text-slate-400" size={20} />
            </div>
            <input type="text" 
              className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl py-4 pl-12 pr-28 focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg"
              placeholder="e.g. Which region generated the highest revenue?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            />
            <button onClick={() => handleAsk()} disabled={asking || !question.trim()}
              className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800/50 text-white px-5 rounded-lg font-medium">
              {asking ? 'Running...' : 'Analyze'}
            </button>
          </div>
          
          {error && (
            <div className="bg-red-900/30 border border-red-500/50 text-red-200 p-4 rounded-xl mb-6 flex items-start gap-3">
              <AlertTriangle className="shrink-0 mt-0.5" size={20} />
              <div><h4 className="font-semibold text-red-100">Error</h4><p className="text-sm mt-1">{error}</p></div>
            </div>
          )}
          
          {/* Results Area */}
          {result && (
            <div className="flex flex-col gap-6 pb-20 animate-in fade-in duration-500">
              <div className={`rounded-xl border p-6 shadow-lg ${result.status === 'success' ? 'bg-slate-800 border-slate-700' : 'bg-orange-900/20 border-orange-700/50'}`}>
                {result.status === 'success' ? (
                  <>
                    <div className="flex items-center gap-2 mb-4 text-emerald-400 font-semibold bg-emerald-900/30 w-max px-3 py-1 rounded-full border border-emerald-800/50 text-sm">
                      <CheckCircle2 size={16} /><span>VERIFIED</span>
                    </div>
                    <div className="text-2xl text-white font-medium mb-2 break-words">
                      {typeof result.result === 'object' && result.result !== null ? 
                        (
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                              <thead>
                                <tr className="border-b border-slate-700">
                                  <th className="pb-2">Key</th><th className="pb-2">Value</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(result.result).map(([k, v]: [string, any], i) => (
                                  <tr key={i} className="border-b border-slate-700/50">
                                    <td className="py-2 text-slate-300">{k}</td>
                                    <td className="py-2 font-medium">{String(v)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (<span>{String(result.result)}</span>)
                      }
                    </div>
                    {renderChart()}
                  </>
                ) : result.status === 'refused' ? (
                  <>
                    <div className="flex items-center gap-2 mb-4 text-orange-400 font-semibold bg-orange-900/30 w-max px-3 py-1 rounded-full border border-orange-800/50 text-sm">
                      <AlertTriangle size={16} /><span>CANNOT DETERMINE RELIABLY</span>
                    </div>
                    <div className="text-lg text-orange-100 font-medium">
                      {result.reason || "The data does not contain the required information."}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2 mb-4 text-red-400 font-semibold bg-red-900/30 w-max px-3 py-1 rounded-full border border-red-800/50 text-sm">
                      <X size={16} /><span>EXECUTION FAILED</span>
                    </div>
                    <div className="text-lg text-red-100 mb-2">
                      {result.message || result.error}
                    </div>
                  </>
                )}
                
                <button onClick={() => setShowEvidence(!showEvidence)}
                  className="mt-6 flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 font-medium">
                  <ChevronRight size={16} className={`transform transition-transform ${showEvidence ? 'rotate-90' : ''}`} />
                  Evidence & Reasoning
                </button>
              </div>
              
              {showEvidence && result.evidence && (
                <div className="grid grid-cols-1 gap-4 animate-in slide-in-from-top-2 fade-in duration-300">
                  <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-md">
                    <h3 className="text-sm uppercase tracking-wider text-slate-400 font-bold mb-4 flex items-center gap-2">
                      <Search size={16} /> Verification Details
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <div className="text-xs text-slate-500 mb-1">Datasets Included</div>
                        <div className="flex flex-wrap gap-2">
                          {result.evidence.required_datasets?.map((ds: string) => (
                            <span key={ds} className="bg-slate-700 px-2 py-1 rounded text-xs text-slate-200 border border-slate-600">{ds}</span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 mb-1">Columns Used</div>
                        <div className="flex flex-wrap gap-2">
                          {result.evidence.required_columns?.map((col: string) => (
                            <span key={col} className="bg-slate-700 px-2 py-1 rounded text-xs text-slate-200 border border-slate-600">{col}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                    {result.status === 'success' && (
                      <div className="mt-4 pt-4 border-t border-slate-700 grid grid-cols-2">
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Execution Status</div>
                          <div className="text-sm text-emerald-400 flex items-center gap-1"><CheckCircle2 size={14}/> Success</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Compute Time</div>
                          <div className="text-sm text-slate-300">{result.execution_time_ms} ms</div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {result.code && (
                    <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-md">
                      <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex justify-between items-center">
                        <span className="text-xs font-medium flex items-center gap-2 text-slate-300"><Code size={14} className="text-blue-400"/> Generated Python</span>
                      </div>
                      <pre className="p-4 overflow-x-auto text-sm font-mono text-slate-300">
                        <code>{result.code}</code>
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
