import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Network, UserPlus } from 'lucide-react';

const Register = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgId, setOrgId] = useState(''); 
  const [organisations, setOrganisations] = useState([]); // State to hold the fetched orgs
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  const navigate = useNavigate();

  // Fetch the list of organizations when the page loads
  useEffect(() => {
    const fetchOrgs = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8000/organisations/');
        setOrganisations(response.data);
        
        // If there are orgs, set the default selection to the first one
        if (response.data.length > 0) {
          setOrgId(response.data[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch organizations", err);
        setError("Could not load organization list. Is the Hub running?");
      }
    };
    fetchOrgs();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      const payload = {
        email: email,
        password: password,
        role: "Client Operator",
        organisation_id: parseInt(orgId)
      };

      await axios.post('http://127.0.0.1:8000/users/', payload);
      
      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 2000);

    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to register account.');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-lg border border-gray-100">
        
        <div className="flex flex-col items-center mb-8">
          <div className="p-3 bg-green-50 text-green-600 rounded-full mb-4">
            <UserPlus size={32} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Join the ML Hub</h2>
          <p className="text-gray-500 mt-1">Register a new edge node account</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-50 border-l-4 border-green-500 text-green-700 text-sm">
            Registration successful! Redirecting to login...
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
            <input 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition-all"
              placeholder="node@hospital.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition-all"
              placeholder="••••••••"
            />
          </div>

          {/* THE NEW DYNAMIC DROPDOWN */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Organization</label>
            <select 
              required
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none transition-all bg-white"
            >
              {organisations.length === 0 ? (
                <option disabled>Loading organizations...</option>
              ) : (
                organisations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))
              )}
            </select>
          </div>

          <button 
            type="submit" 
            className="w-full py-2.5 px-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-sm transition-colors"
          >
            Create Account
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-500">
          Already have an account? <Link to="/login" className="text-blue-600 hover:underline font-medium">Sign in here</Link>
        </div>
        
      </div>
    </div>
  );
};

export default Register;