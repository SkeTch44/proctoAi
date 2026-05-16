import React, { useState, useEffect } from 'react';
import { getToken } from '../../utils/authStorage';

const ProctoringLogs = () => {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filters, setFilters] = useState({
    exam_id: '',
    session_id: '',
    severity: ''
  });

  useEffect(() => {
    fetchEvents();
  }, [filters]);

  const fetchEvents = async () => {
    setIsLoading(true);
    const token = getToken();
    
    try {
      const params = new URLSearchParams();
      if (filters.exam_id) params.append('exam_id', filters.exam_id);
      if (filters.session_id) params.append('session_id', filters.session_id);
      if (filters.severity) params.append('severity', filters.severity);

      const res = await fetch(`http://127.0.0.1:5000/api/admin/proctoring-events?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const data = await res.json();
      if (res.ok && data.events) {
        setEvents(data.events);
      } else {
        alert('Failed to fetch proctoring events');
      }
    } catch (err) {
      console.error('Error fetching events:', err);
      alert('Error fetching proctoring events');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Proctoring Logs</h1>
          <p className="text-gray-600 mt-2">Review all proctoring events and violations</p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Filters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Exam ID
              </label>
              <input
                type="text"
                name="exam_id"
                value={filters.exam_id}
                onChange={handleFilterChange}
                placeholder="Leave empty for all"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Session ID
              </label>
              <input
                type="text"
                name="session_id"
                value={filters.session_id}
                onChange={handleFilterChange}
                placeholder="Leave empty for all"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Severity
              </label>
              <select
                name="severity"
                value={filters.severity}
                onChange={handleFilterChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Severities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </div>

        {/* Events Table */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">
              Loading proctoring events...
            </div>
          ) : events.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No proctoring events found
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100 border-b border-gray-300">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Timestamp</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Student</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Event Type</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Severity</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Session ID</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event, idx) => (
                    <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {new Date(event.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {event.student_name}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        <span className="font-medium">{event.event_type}</span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`inline-block px-3 py-1 rounded text-xs font-semibold border ${getSeverityColor(event.severity)}`}>
                          {event.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {event.session_id}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {event.details ? event.details.substring(0, 50) + '...' : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProctoringLogs;
