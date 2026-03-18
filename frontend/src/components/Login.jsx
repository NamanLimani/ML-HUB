import { useState } from 'react';
import { useNavigate , Link } from 'react-router-dom';
import axios from 'axios';
import { Network } from 'lucide-react';

const Login = () => {
  // React State to hold the user's input
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  
  // Hook to redirect the user after a successful login
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault(); // Prevents the page from reloading on submit
    setError('');

    try {
      // FastAPI's OAuth2 expects "Form Data" (URL Encoded), NOT a JSON object!
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      // Make the POST request to your Hub
      const response = await axios.post('https://numerous-coyote-naman-limani-8961fadf.koyeb.app/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      // If successful, save the JWT to the browser and jump to the dashboard
      const token = response.data.access_token;
      localStorage.setItem('hub_jwt', token);
      navigate('/dashboard');

    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to connect to Hub.');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-lg border border-gray-100">
        
        {/* Logo and Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-full mb-4">
            <Network size={32} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Decentralized ML Hub</h2>
          <p className="text-gray-500 mt-1">Sign in to orchestrate edge nodes</p>
        </div>

        {/* Error Message Display */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
            <input 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="admin@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="••••••••"
            />
          </div>

          <button 
            type="submit" 
            className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm transition-colors"
          >
            Authenticate
          </button>
        </form>

        {/* --- NEW LINK ADDED HERE --- */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Need to connect a new edge node? <Link to="/register" className="text-blue-600 hover:underline font-medium">Register here</Link>
        </div>
        
      </div>
    </div>
  );
};

export default Login;