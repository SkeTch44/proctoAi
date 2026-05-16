import React, { useState, useEffect, useRef } from 'react';
import { getToken } from '../../utils/authStorage';
import { getSocket, onConnectionChange } from '../../services/socket';

const LiveMonitoring = () => {
  const [activeExams, setActiveExams] = useState({});
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState({});
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const wsRef = useRef(null);

  // Fetch initial data and set up WebSocket listeners
  useEffect(() => {
    fetchDashboard();
    setupWebSocket();

    return () => {
      // Cleanup listeners
      const socket = getSocket();
      socket.off('student_joined');
      socket.off('proctoring_alert');
    };
  }, []);

  const fetchDashboard = async () => {
    const token = getToken();
    try {
      const res = await fetch('http://127.0.0.1:5000/api/admin/dashboard', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      
      if (data.active_sessions) {
        // Group sessions by exam
        const grouped = {};
        data.active_sessions.forEach(session => {
          if (!grouped[session.exam_title]) {
            grouped[session.exam_title] = [];
          }
          grouped[session.exam_title].push(session);
        });
        setActiveExams(grouped);
      }
      
      if (data.recent_alerts) {
        setRecentAlerts(data.recent_alerts);
      }
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
    }
  };

  const setupWebSocket = () => {
    const socket = getSocket();
    
    // Join admin room
    socket.emit('join_admin');
    wsRef.current = socket;

    // Listen for new student joins
    socket.on('student_joined', (data) => {
      console.log('[LiveMonitoring] Student joined:', data);
      addStudentToExam(data);
      fetchDashboard(); // Refresh dashboard
    });

    // Listen for proctoring alerts
    socket.on('proctoring_alert', (data) => {
      console.log('[LiveMonitoring] Proctoring alert:', data);
      setRecentAlerts(prev => [
        {
          event_type: data.alert_type,
          severity: data.severity,
          timestamp: data.timestamp,
          username: 'Student'
        },
        ...prev
      ].slice(0, 20)); // Keep last 20 alerts
    });

    // Handle connection state changes
    const unsubscribe = onConnectionChange((status) => {
      setConnectionStatus(status);
    });

    return unsubscribe;
  };

  const addStudentToExam = (data) => {
    setActiveExams(prev => {
      const updated = { ...prev };
      if (!updated[data.exam_title]) {
        updated[data.exam_title] = [];
      }
      updated[data.exam_title].push({
        session_id: data.session_id,
        username: data.student_name,
        suspicion_score: 0,
        started_at: new Date().toISOString()
      });
      return updated;
    });
  };

  const handleStartExam = async (examTitle) => {
    setIsLoading(prev => ({ ...prev, [examTitle]: true }));
    const token = getToken();
    
    try {
      // Get exam ID
      const examRes = await fetch('http://127.0.0.1:5000/api/exams', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const examsData = await examRes.json();
      const exam = examsData.exams?.find(e => e.title === examTitle);
      
      if (!exam) {
        alert('Exam not found');
        return;
      }

      // Start the exam (broadcast to all students directly via WebSocket)
      if (wsRef.current) {
         wsRef.current.emit('admin_start_exam', { exam_id: exam.id });
         alert(`Start Exam signal broadcasted for ${examTitle}!`);
      } else {
         alert("Cannot start exam: WebSocket disconnected.");
      }
      
    } catch (err) {
      console.error('Error starting exam:', err);
      alert('Failed to start exam');
    } finally {
      setIsLoading(prev => ({ ...prev, [examTitle]: false }));
    }
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Live Exam Monitoring</h1>
          <div className="mt-2 flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${connectionStatus === 'connected' ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-600">
              {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Active Exams Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {Object.entries(activeExams).map(([examTitle, students]) => (
            <div key={examTitle} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">{examTitle}</h2>
                  <p className="text-sm text-gray-600 mt-1">{students.length} student(s) joined</p>
                </div>
                <button
                  onClick={() => handleStartExam(examTitle)}
                  disabled={isLoading[examTitle]}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors text-sm font-medium"
                >
                  {isLoading[examTitle] ? 'Starting...' : '▶ Start Exam'}
                </button>
              </div>

              {/* Student List */}
              <div className="space-y-3">
                {students.map(student => (
                  <div key={student.session_id} className="flex items-center justify-between bg-gray-50 p-3 rounded">
                    <div>
                      <p className="font-medium text-gray-900">{student.username}</p>
                      <p className="text-xs text-gray-500">Session: {student.session_id}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold text-gray-900">
                        Score: {student.suspicion_score}
                      </div>
                      <div className={`text-xs ${student.suspicion_score > 50 ? 'text-red-600' : 'text-green-600'}`}>
                        {student.suspicion_score > 50 ? 'High suspicion' : 'Normal'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Recent Alerts */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Alerts</h2>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {recentAlerts.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No alerts</p>
            ) : (
              recentAlerts.map((alert, idx) => (
                <div key={idx} className={`p-3 rounded-lg border-l-4 ${
                  alert.severity === 'high' ? 'border-red-500 bg-red-50' 
                  : alert.severity === 'medium' ? 'border-yellow-500 bg-yellow-50'
                  : 'border-blue-500 bg-blue-50'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{alert.event_type}</p>
                      <p className="text-sm text-gray-600">{alert.username}</p>
                    </div>
                    <div className="text-right">
                      <span className={`inline-block px-2 py-1 text-xs font-semibold rounded ${
                        alert.severity === 'high' ? 'bg-red-200 text-red-800'
                        : alert.severity === 'medium' ? 'bg-yellow-200 text-yellow-800'
                        : 'bg-blue-200 text-blue-800'
                      }`}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveMonitoring;
