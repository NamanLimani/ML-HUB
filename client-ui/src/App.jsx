import { useState, useRef, useEffect } from 'react';
import { Server, Play, Folder, Lock, Mail, Hash, Activity, Terminal, CheckCircle, LogOut, UploadCloud, Microscope } from 'lucide-react';

function App() {
  const [step, setStep] = useState(1); 
  const [mode, setMode] = useState('train'); // NEW: 'train' or 'test'
  
  const [credentials, setCredentials] = useState({ email: '', password: '' });
  const [config, setConfig] = useState({ jobId: '', pipelineType: 'cnn', dataPath: '' });
  
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState('');
  const terminalEndRef = useRef(null);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!credentials.email || !credentials.password) {
      setStatus('❌ Please enter both email and password.');
      return;
    }
    setLoading(true);
    setStatus('Authenticating with Hub...');

    try {
      const formData = new URLSearchParams();
      formData.append('username', credentials.email);
      formData.append('password', credentials.password);

      const response = await fetch('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });

      if (!response.ok) throw new Error('Invalid email or password');

      setStatus('');
      setStep(2);
    } catch (err) {
      setStatus(`❌ Auth Failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartProcess = async (e) => {
    e.preventDefault();
    if (!config.jobId || !config.dataPath) {
      setStatus('❌ Please provide a Job ID and select a Data Folder.');
      return;
    }

    setStatus('Connecting to local Edge Server...');
    setLoading(true);
    setLogs(''); 

    try {
      // We pass the "mode" to the backend so it knows whether to train or just test
      const response = await fetch('http://127.0.0.1:8001/start-local-training', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
          job_id: parseInt(config.jobId),
          data_path: config.dataPath,
          pipeline_type: config.pipelineType,
          run_mode: mode // 'train' or 'test'
        })
      });

      if (!response.ok) throw new Error('Network response was not ok');

      setStatus(`${mode === 'train' ? 'Training' : 'Testing'} Started! Streaming logs from Docker...`);
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: !done });
          setLogs((prev) => prev + chunk);
        }
      }
      
      setStatus('✅ Process Complete!');
    } catch (err) {
      setStatus(`❌ Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setStep(1);
    setCredentials({ email: '', password: '' });
    setConfig({ jobId: '', pipelineType: 'cnn', dataPath: '' });
    setLogs('');
    setStatus('');
  };

  // Trigger the Native OS File Picker!
  const handleBrowseFiles = async () => {
    // Check if we are running inside Electron
    if (window.electronAPI) {
      const folderPath = await window.electronAPI.selectFolder();
      if (folderPath) {
        setConfig({...config, dataPath: folderPath}); // Update the UI with the real Mac path
      }
    } else {
      // Fallback if testing in a normal browser
      alert("Native file picker is only available in the Desktop App mode.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className={`bg-white w-full rounded-2xl shadow-xl border border-slate-100 overflow-hidden flex flex-col md:flex-row transition-all duration-500 ${step === 1 ? 'max-w-md' : 'max-w-4xl'}`}>
        
        {/* === STEP 1: LOGIN SCREEN === */}
        {step === 1 && (
          <div className="w-full flex flex-col">
            <div className="bg-slate-900 p-8 text-white text-center flex flex-col items-center">
              <Server className="text-blue-400 mb-3" size={40} />
              <h1 className="text-2xl font-bold">ML Hub Edge</h1>
              <p className="text-slate-400 text-sm mt-1">Sign in to connect your node</p>
            </div>

            <form onSubmit={handleLogin} className="p-8 space-y-5">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Client Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 text-slate-400" size={18} />
                  <input type="email" required value={credentials.email} onChange={(e) => setCredentials({...credentials, email: e.target.value})} className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 text-slate-400" size={18} />
                  <input type="password" required value={credentials.password} onChange={(e) => setCredentials({...credentials, password: e.target.value})} className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
              </div>

              {status && (
                <div className={`p-3 rounded-lg text-sm font-medium ${status.includes('❌') ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>
                  {status}
                </div>
              )}

              <button type="submit" disabled={loading} className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50 mt-4">
                {loading ? 'Verifying...' : 'Authenticate'}
              </button>
            </form>
          </div>
        )}

        {/* === STEP 2: DASHBOARD === */}
        {step === 2 && (
          <>
            {/* LEFT SIDE: Control Panel */}
            <div className="w-full md:w-1/2 flex flex-col border-r border-slate-100">
              <div className="bg-slate-900 p-6 text-white flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <Server className="text-blue-400" size={24} />
                  <div>
                    <h1 className="text-lg font-bold">Edge Node Active</h1>
                    <p className="text-slate-400 text-xs flex items-center gap-1"><CheckCircle size={12}/> {credentials.email}</p>
                  </div>
                </div>
                <button onClick={handleLogout} className="text-slate-400 hover:text-white transition-colors" title="Logout">
                  <LogOut size={20} />
                </button>
              </div>

              {/* TABS: Train vs Test */}
              <div className="flex border-b border-slate-200">
                <button 
                  onClick={() => setMode('train')}
                  className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 transition-colors ${mode === 'train' ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600' : 'text-slate-500 hover:bg-slate-50'}`}
                >
                  <UploadCloud size={18} /> Train & Sync
                </button>
                <button 
                  onClick={() => setMode('test')}
                  className={`flex-1 py-3 text-sm font-bold flex items-center justify-center gap-2 transition-colors ${mode === 'test' ? 'bg-purple-50 text-purple-700 border-b-2 border-purple-600' : 'text-slate-500 hover:bg-slate-50'}`}
                >
                  <Microscope size={18} /> Local Evaluation
                </button>
              </div>

              <form onSubmit={handleStartProcess} className="p-6 space-y-5 flex-1">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Target Job ID</label>
                    <div className="relative">
                      <Hash className="absolute left-3 top-2.5 text-slate-400" size={18} />
                      <input type="number" required min="1" value={config.jobId} onChange={(e) => setConfig({...config, jobId: e.target.value})} className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="e.g. 1" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Architecture</label>
                    <div className="relative">
                      <Activity className="absolute left-3 top-2.5 text-slate-400" size={18} />
                      <select value={config.pipelineType} onChange={(e) => setConfig({...config, pipelineType: e.target.value})} className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
                        <option value="cnn">CNN (Image Data)</option>
                        <option value="mlp">MLP (Tabular Data)</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* THE NEW NATIVE BROWSE BUTTON */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Local Data Folder</label>
                  <div className="flex gap-2">
                    <button 
                      type="button" 
                      onClick={handleBrowseFiles}
                      className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg border border-slate-300 transition-colors"
                    >
                      <Folder size={18} /> Browse...
                    </button>
                    <input 
                      type="text" readOnly required value={config.dataPath} 
                      className="flex-1 px-3 py-2 border border-slate-200 rounded-lg outline-none bg-slate-50 text-slate-500 font-mono text-sm" 
                      placeholder="No folder selected" 
                    />
                  </div>
                </div>

                {status && (
                  <div className={`p-3 rounded-lg text-sm font-medium ${status.includes('Error') || status.includes('❌') ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}>
                    {status}
                  </div>
                )}

                <button type="submit" disabled={loading} className={`w-full mt-auto py-3 px-4 text-white font-bold rounded-lg shadow-md transition-colors flex items-center justify-center gap-2 disabled:opacity-50 ${mode === 'train' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-purple-600 hover:bg-purple-700'}`}>
                  <Play size={20} fill="currentColor" />
                  {loading ? 'Engine Running...' : (mode === 'train' ? 'Start Local Training' : 'Run Local Evaluation')}
                </button>
              </form>
            </div>

            {/* RIGHT SIDE: Live Terminal Output */}
            <div className="w-full md:w-1/2 bg-[#0d1117] text-gray-300 p-4 font-mono text-sm flex flex-col h-96 md:h-auto">
              <div className="flex items-center gap-2 mb-3 border-b border-gray-700 pb-2 text-gray-400">
                <Terminal size={16} />
                <span className="font-semibold uppercase tracking-wider text-xs">Docker Node Console ({mode.toUpperCase()})</span>
              </div>
              
              <div className="flex-1 overflow-y-auto whitespace-pre-wrap wrap-break-words pr-2 custom-scrollbar">
                {logs ? logs : <span className="text-gray-600 italic">Awaiting execution command...</span>}
                <div ref={terminalEndRef} />
              </div>
            </div>
          </>
        )}

      </div>
    </div>
  );
}

export default App;