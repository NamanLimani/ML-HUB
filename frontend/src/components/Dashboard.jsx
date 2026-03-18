import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Activity, Play, Box, LogOut, Building2, PlusCircle, Users, Trash2, ClipboardList, History, X, Download } from 'lucide-react';
import LiveTelemetry from './LiveTelemetry';

const Dashboard = () => {
  // --- STATE ---
  const [currentUser, setCurrentUser] = useState(null);
  const [activeTab, setActiveTab] = useState('jobs'); // 'jobs', 'orgs', 'clients', 'audit'
  
  const [jobs, setJobs] = useState([]);
  const [organisations, setOrganisations] = useState([]);
  const [newOrgName, setNewOrgName] = useState('');
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  
  const [error, setError] = useState('');
  const [activeChartJob, setActiveChartJob] = useState(null);
  const [viewingHistoryFor, setViewingHistoryFor] = useState(null); // Tracks the modal
  
  const navigate = useNavigate();
  const token = localStorage.getItem('hub_jwt');

  // --- INITIALIZATION ---
  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    fetchUserProfile();
    fetchJobs();
    fetchOrganisations();
    fetchUsers();
    fetchAuditLogs();
  }, []);

  // --- API CALLS ---
  const fetchUserProfile = async () => {
    try {
      const response = await axios.get('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/users/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCurrentUser(response.data);
    } catch (err) {
      if (err.response?.status === 401) handleLogout();
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await axios.get('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/training-jobs/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setJobs(response.data);
    } catch (err) {
      setError('Failed to fetch training jobs.');
    }
  };

  const fetchOrganisations = async () => {
    try {
      const response = await axios.get('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/organisations/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOrganisations(response.data);
    } catch (err) {
      console.error('Failed to fetch orgs');
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/users/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (err) {
      console.error('Failed to fetch users');
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const response = await axios.get('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/metrics/history', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAuditLogs(response.data);
    } catch (err) {
      console.error('Failed to fetch audit history');
    }
  };

  // --- ACTIONS ---
  const handleLogout = () => {
    localStorage.removeItem('hub_jwt');
    navigate('/login');
  };

  const startJob = async (jobId) => {
    try {
      await axios.post(`https://numerous-coyote-naman-limani-8961fadf.koyeb.app/training-jobs/${jobId}/start`, null, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert(`Job ${jobId} successfully queued!`);
      fetchJobs();
    } catch (err) {
      alert(`Failed to start job: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleCreateOrg = async (e) => {
    e.preventDefault();
    try {
      await axios.post('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/organisations/', 
        { name: newOrgName },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setNewOrgName('');
      fetchOrganisations();
      alert("Organization successfully registered!");
    } catch (err) {
      alert(`Failed to create org: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDeleteUser = async (userId, userEmail) => {
    if (!window.confirm(`Are you sure you want to permanently delete ${userEmail}?`)) return;
    try {
      await axios.delete(`https://numerous-coyote-naman-limani-8961fadf.koyeb.app/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchUsers();
      alert("Client deleted successfully.");
    } catch (err) {
      alert(`Failed to delete client: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDeleteJob = async (jobId, jobName) => {
    if (!window.confirm(`Are you sure you want to permanently delete the job "${jobName}"?`)) return;
    try {
      await axios.delete(`https://numerous-coyote-naman-limani-8961fadf.koyeb.app/training-jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchJobs();
    } catch (err) {
      alert(`Failed to delete job: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDeleteOrg = async (orgId, orgName) => {
    if (!window.confirm(`Are you sure you want to permanently delete the organization "${orgName}"?`)) return;
    try {
      await axios.delete(`https://numerous-coyote-naman-limani-8961fadf.koyeb.app/organisations/${orgId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchOrganisations();
    } catch (err) {
      alert(`Delete failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  if (!currentUser) return <div className="p-8 text-center text-gray-500">Loading Profile...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      {/* Top Navigation Bar */}
      <header className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-gray-100 mb-8">
        <div className="flex items-center gap-2 text-blue-600">
          <Activity size={24} />
          <h1 className="text-xl font-bold text-gray-900">Decentralized ML Hub</h1>
        </div>
        
        <div className="flex items-center gap-6">
          {/* --- NEW DOWNLOAD BUTTON --- */}
          <a 
            href="/mlhub-edge-mac-arm64.dmg" 
            download="MLHub_Edge_Installer.dmg"
            className="flex items-center gap-2 px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 font-semibold rounded-lg transition-colors border border-blue-200 text-sm"
          >
            <Download size={16} />
            Download Edge Node
          </a>
          
          <div className="text-sm text-right border-l border-gray-200 pl-6">
            <p className="font-bold text-gray-800">{currentUser.email}</p>
            <p className="text-gray-500">{currentUser.is_admin ? "Platform Admin" : "Client Operator"}</p>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-2 text-gray-500 hover:text-red-500 transition-colors font-medium ml-2">
            <LogOut size={18} /> Logout
          </button>
        </div>
      </header>
  

      {/* Navigation Tabs */}
      <div className="flex gap-4 mb-8 border-b border-gray-200 pb-2">
        <button 
          onClick={() => setActiveTab('jobs')}
          className={`font-semibold pb-2 px-2 ${activeTab === 'jobs' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          Training Jobs
        </button>
        
        {currentUser.is_admin && (
          <>
            <button 
              onClick={() => setActiveTab('orgs')}
              className={`font-semibold pb-2 px-2 ${activeTab === 'orgs' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Manage Organizations
            </button>
            <button 
              onClick={() => setActiveTab('clients')}
              className={`font-semibold pb-2 px-2 ${activeTab === 'clients' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Manage Clients
            </button>
          </>
        )}

        {/* Only Clients get the dedicated Audit Tab */}
        {!currentUser.is_admin && (
          <button 
            onClick={() => setActiveTab('audit')}
            className={`font-semibold pb-2 px-2 ${activeTab === 'audit' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
          >
            My Upload History
          </button>
        )}
      </div>

      <main className="max-w-6xl mx-auto relative">
        {error && <div className="p-4 bg-red-100 text-red-700 rounded-lg mb-6">{error}</div>}

        {/* --- TAB 1: TRAINING JOBS --- */}
        {activeTab === 'jobs' && (
          <>
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Active Training Jobs</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {jobs.map((job) => (
                <div key={job.id} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                  
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">{job.name}</h3>
                      <p className="text-sm text-gray-500 font-mono">ID: {job.id}</p>
                    </div>
                    
                    <div className="flex gap-2">
                      {currentUser.is_admin && (
                        <button 
                          onClick={() => handleDeleteJob(job.id, job.name)}
                          className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete Job"
                        >
                          <Trash2 size={18} />
                        </button>
                      )}
                      <div className="p-2 bg-blue-50 text-blue-600 rounded-lg"><Box size={20} /></div>
                    </div>
                  </div>

                  <div className="space-y-2 mb-6 text-sm text-gray-600">
                    <p><span className="font-semibold text-gray-800">Architecture:</span> {job.model_template}</p>
                    <p><span className="font-semibold text-gray-800">Total Rounds:</span> {job.total_rounds}</p>
                  </div>

                  <div className="flex gap-3">
                    {currentUser.is_admin ? (
                      <button onClick={() => startJob(job.id)} className="flex-1 flex items-center justify-center gap-2 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
                        <Play size={16} fill="currentColor" /> Start Aggregation
                      </button>
                    ) : (
                      <div className="flex-1 flex items-center justify-center py-2 bg-gray-50 text-sm font-medium text-gray-500 rounded-lg border border-gray-200">
                        Waiting for Admin
                      </div>
                    )}
                    
                    <button onClick={() => setActiveChartJob(activeChartJob === job.id ? null : job.id)} className="flex-1 flex items-center justify-center gap-2 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors">
                      <Activity size={16} /> {activeChartJob === job.id ? 'Hide Metrics' : 'Live Metrics'}
                    </button>
                  </div>

                  {activeChartJob === job.id && <LiveTelemetry jobId={job.id} />}
                </div>
              ))}
              
              {jobs.length === 0 && !error && (
                <div className="col-span-full text-center py-12 text-gray-500 bg-white rounded-xl border border-gray-200 border-dashed">
                  No training jobs found.
                </div>
              )}
            </div>
          </>
        )}

        {/* --- TAB 2: ORGANIZATIONS (ADMIN ONLY) --- */}
        {activeTab === 'orgs' && currentUser.is_admin && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="md:col-span-1">
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                <div className="flex items-center gap-2 mb-4 text-gray-900">
                  <Building2 size={20} />
                  <h3 className="text-lg font-bold">Register Organization</h3>
                </div>
                <form onSubmit={handleCreateOrg} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name</label>
                    <input 
                      type="text" 
                      required 
                      value={newOrgName}
                      onChange={(e) => setNewOrgName(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      placeholder="e.g. NYU Medical"
                    />
                  </div>
                  <button type="submit" className="w-full flex items-center justify-center gap-2 py-2 bg-gray-900 hover:bg-black text-white rounded-lg font-medium transition-colors">
                    <PlusCircle size={18} /> Provision Tenant
                  </button>
                </form>
              </div>
            </div>

            <div className="md:col-span-2">
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                <h3 className="text-lg font-bold text-gray-900 mb-4">Provisioned Tenants</h3>
                <div className="space-y-3">
                  {organisations.map((org) => (
                    <div key={org.id} className="flex justify-between items-center p-4 bg-gray-50 rounded-lg border border-gray-100 group hover:bg-gray-100 transition-colors">
                      <div>
                        <span className="font-medium text-gray-800">{org.name}</span>
                        <span className="ml-3 text-xs font-mono bg-white px-2 py-1 rounded border border-gray-200 text-gray-500">ID: {org.id}</span>
                      </div>
                      <button 
                        onClick={() => handleDeleteOrg(org.id, org.name)}
                        className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all"
                        title="Delete Organization"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  ))}
                  {organisations.length === 0 && (
                    <div className="text-center py-4 text-gray-500">No organizations registered yet.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* --- TAB 3: MANAGE CLIENTS (ADMIN ONLY) --- */}
        {activeTab === 'clients' && currentUser.is_admin && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex items-center gap-2">
              <Users size={20} className="text-gray-700" />
              <h3 className="text-lg font-bold text-gray-900">Registered Edge Nodes</h3>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-sm text-gray-600">
                    <th className="p-4 font-semibold">Node ID</th>
                    <th className="p-4 font-semibold">Email Account</th>
                    <th className="p-4 font-semibold">Organization</th>
                    <th className="p-4 font-semibold">Role</th>
                    <th className="p-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => {
                    const userOrg = organisations.find(o => o.id === user.organisation_id);
                    
                    return (
                      <tr key={user.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                        <td className="p-4 text-sm font-mono text-gray-500">#{user.id}</td>
                        <td className="p-4 text-sm font-medium text-gray-900">{user.email}</td>
                        <td className="p-4 text-sm text-gray-600 font-medium">
                          {user.is_admin ? (
                            <span className="text-gray-400 italic">Platform / HQ</span>
                          ) : (
                            userOrg ? userOrg.name : 'Unknown Org'
                          )}
                        </td>
                        <td className="p-4 text-sm">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${user.is_admin ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>
                            {user.is_admin ? 'Admin' : 'Client'}
                          </span>
                        </td>
                        <td className="p-4 text-right">
                          {!user.is_admin && (
                            <div className="flex justify-end gap-2">
                              <button 
                                onClick={() => setViewingHistoryFor(user)}
                                className="p-2 text-blue-500 hover:bg-blue-50 rounded transition-colors"
                                title="View Training History"
                              >
                                <History size={18} />
                              </button>
                              <button 
                                onClick={() => handleDeleteUser(user.id, user.email)}
                                className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                title="Delete Client"
                              >
                                <Trash2 size={18} />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {users.length === 0 && (
              <div className="p-8 text-center text-gray-500">No clients registered yet.</div>
            )}
          </div>
        )}

        {/* --- TAB 4: CLIENT UPLOAD HISTORY (CLIENTS ONLY) --- */}
        {activeTab === 'audit' && !currentUser.is_admin && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex items-center gap-2">
              <ClipboardList size={20} className="text-gray-700" />
              <h3 className="text-lg font-bold text-gray-900">Your Training Contributions</h3>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-sm text-gray-600">
                    <th className="p-4 font-semibold">Timestamp (UTC)</th>
                    <th className="p-4 font-semibold">Target Job</th>
                    <th className="p-4 font-semibold">Round</th>
                    <th className="p-4 font-semibold text-blue-600">Loss (Weight Quality)</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="p-4 text-sm text-gray-600">{log.timestamp}</td>
                      <td className="p-4 text-sm font-medium text-gray-900">{log.job_name}</td>
                      <td className="p-4 text-sm text-gray-600">Round {log.round_number}</td>
                      <td className="p-4 text-sm font-mono text-blue-600 font-semibold">{parseFloat(log.loss).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {auditLogs.length === 0 && (
              <div className="p-8 text-center text-gray-500">No training data has been uploaded yet.</div>
            )}
          </div>
        )}

        {/* --- ADMIN POPUP MODAL: SPECIFIC CLIENT HISTORY --- */}
        {viewingHistoryFor && currentUser.is_admin && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl flex flex-col max-h-[80vh]">
              
              <div className="p-5 border-b border-gray-100 flex justify-between items-center bg-gray-50 rounded-t-xl">
                <div>
                  <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                    <History size={20} className="text-blue-600"/>
                    Weight Upload Ledger
                  </h3>
                  <p className="text-sm text-gray-500 mt-1 font-mono">{viewingHistoryFor.email}</p>
                </div>
                <button 
                  onClick={() => setViewingHistoryFor(null)} 
                  className="p-2 text-gray-400 hover:text-gray-800 hover:bg-gray-200 rounded-full transition-colors"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="overflow-y-auto p-0">
                <table className="w-full text-left border-collapse">
                  <thead className="sticky top-0 bg-white shadow-sm ring-1 ring-gray-100">
                    <tr className="text-sm text-gray-600">
                      <th className="p-4 font-semibold">Timestamp (UTC)</th>
                      <th className="p-4 font-semibold">Target Job</th>
                      <th className="p-4 font-semibold">Round</th>
                      <th className="p-4 font-semibold text-blue-600">Reported Loss</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.filter(log => log.uploader === viewingHistoryFor.email).map((log) => (
                      <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                        <td className="p-4 text-sm text-gray-600">{log.timestamp}</td>
                        <td className="p-4 text-sm font-medium text-gray-900">{log.job_name}</td>
                        <td className="p-4 text-sm text-gray-600">Round {log.round_number}</td>
                        <td className="p-4 text-sm font-mono text-blue-600 font-semibold">{parseFloat(log.loss).toFixed(4)}</td>
                      </tr>
                    ))}
                    {auditLogs.filter(log => log.uploader === viewingHistoryFor.email).length === 0 && (
                      <tr>
                        <td colSpan="4" className="p-12 text-center text-gray-500">
                          This client has not uploaded any weights yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;