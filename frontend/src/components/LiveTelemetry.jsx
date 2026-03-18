import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity } from 'lucide-react';
import axios from 'axios';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-gray-200 shadow-lg rounded-lg">
        <p className="font-bold text-gray-800">{label}</p>
        <p className="text-blue-600 font-semibold mt-1">Loss: {payload[0].value}</p>
        <p className="text-xs text-gray-500 mt-2">Uploader: {payload[0].payload.client_email}</p>
      </div>
    );
  }
  return null;
};

const LiveTelemetry = ({ jobId }) => {
  const [data, setData] = useState([]);
  const [status, setStatus] = useState('Connecting...');

useEffect(() => {
    // 1. Fetch historical data first!
    const fetchHistory = async () => {
      try {
        const token = localStorage.getItem('hub_jwt');
        const response = await axios.get(`http://127.0.0.1:8000/training-jobs/${jobId}/telemetry`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        // Populate the chart with past data
        if (response.data.length > 0) {
          setData(response.data);
        }
      } catch (err) {
        console.error("Failed to fetch telemetry history", err);
      }
    };

    fetchHistory();

    // 2. Open the WebSocket connection for new, live data
    const ws = new WebSocket(`ws://localhost:8000/ws/telemetry/${jobId}`);

    ws.onopen = () => {
      setStatus('Listening for Edge Node metrics...');
    };

    ws.onmessage = (event) => {
      const rawMessage = JSON.parse(event.data);
      
      if (rawMessage.loss) {
        setData((prevData) => {
          // Prevent duplicate rounds if history and live stream overlap slightly
          const roundName = `Round ${rawMessage.round}`;
          if (prevData.some(d => d.round === roundName)) return prevData;
          
          return [...prevData, { round: roundName, loss: parseFloat(rawMessage.loss).toFixed(4) }];
        });
      }

      if (rawMessage.status === 'completed') {
        setStatus('Aggregation Complete! Global Model Updated.');
        ws.close();
      }
    };

    ws.onerror = () => {
      setStatus('Connection Error.');
    };

    return () => {
      if (ws.readyState === 1) ws.close();
    };
  }, [jobId]);

  return (
    <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center gap-2 mb-4 text-blue-600">
        <Activity size={18} className="animate-pulse" />
        <span className="text-sm font-semibold text-gray-700">{status}</span>
      </div>
      
      {/* The Recharts Animated Graph */}
      <div className="h-64 w-full bg-white p-2 rounded border border-gray-100 shadow-inner">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
            <XAxis dataKey="round" tick={{ fontSize: 12, fill: '#6b7280' }} />
            <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} domain={['auto', 'auto']} />
            
            {/* --- THIS IS THE FIX: Using your Custom Tooltip! --- */}
            <Tooltip content={<CustomTooltip />} />
            
            <Line 
              type="monotone" 
              dataKey="loss" 
              stroke="#2563eb" 
              strokeWidth={3} 
              dot={{ r: 4, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }} 
              activeDot={{ r: 6 }}
              isAnimationActive={true}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default LiveTelemetry;