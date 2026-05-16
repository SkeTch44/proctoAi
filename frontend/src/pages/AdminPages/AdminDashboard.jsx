import React, { useState, useEffect } from "react";
import { getUser, logout, getToken } from "../../utils/authStorage";
import { useNavigate } from "react-router-dom";
import { io } from "socket.io-client";

const API_BASE = "http://127.0.0.1:5000";

export default function AdminDashboard() {
  const user = getUser();
  const navigate = useNavigate();
  const [socket, setSocket] = useState(null);
  const [waitingExams, setWaitingExams] = useState({}); // { exam_id: { title: "", students: [] } }
  const [activeExamsCount, setActiveExamsCount] = useState(0);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const s = io(API_BASE, {
      auth: { token: getToken() },
      transports: ["websocket", "polling"]
    });

    setSocket(s);

    s.on("connect", () => {
      console.log("Connected to Admin Socket");
      s.emit("join_admin");
    });

    s.on("student_joined", (data) => {
      console.log("Student joined:", data);
      setWaitingExams(prev => {
        const examId = data.exam_id;
        const currentExam = prev[examId] || { title: data.exam_title, students: [] };
        
        // Avoid duplicates
        if (currentExam.students.find(s => s.id === data.student_id)) {
            return prev;
        }

        return {
          ...prev,
          [examId]: {
            ...currentExam,
            students: [...currentExam.students, { id: data.student_id, name: data.student_name, time: data.timestamp }]
          }
        };
      });
    });

    s.on("proctoring_alert", (alert) => {
        setRecentAlerts(prev => [alert, ...prev].slice(0, 10));
    });

    // Fetch initial state
    fetchInitialState();

    return () => s.disconnect();
  }, []);

  const fetchInitialState = async () => {
    setIsLoading(true);
    try {
      // Fetch waiting rooms
      const waitRes = await fetch(`${API_BASE}/api/admin/waiting_room`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      const waitData = await waitRes.json();
      
      if (waitData.exams) {
        const waitingObj = {};
        waitData.exams.forEach(exam => {
          if (exam.status === 'waiting') {
            waitingObj[exam.id] = {
              title: exam.title,
              students: exam.students
            };
          }
        });
        setWaitingExams(waitingObj);
      }

      // Fetch general stats (active sessions)
      const statsRes = await fetch(`${API_BASE}/api/admin/dashboard`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      const statsData = await statsRes.json();
      setActiveExamsCount(statsData.active_sessions?.length || 0);
      setRecentAlerts(statsData.recent_alerts?.slice(0, 10) || []);
      
    } catch (err) {
      console.error("Failed to fetch dashboard state", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartExam = (examId) => {
    if (socket) {
      console.log("Starting exam:", examId);
      socket.emit("admin_start_exam", { exam_id: examId });
      
      // Update local state immediately for snappy feel
      setWaitingExams(prev => {
        const newWaiting = { ...prev };
        delete newWaiting[examId];
        return newWaiting;
      });
      setActiveExamsCount(prev => prev + 1);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/home');
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <div className="max-w-7xl mx-auto p-4 md:p-8 lg:p-12 space-y-10">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-5xl font-black text-gray-900 dark:text-white tracking-tighter leading-none">
              Control <span className="text-blue-600">Center</span>
            </h1>
            <p className="text-xl text-gray-500 dark:text-gray-400 font-medium">
              Real-time proctoring and exam orchestration
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="hidden lg:block text-right mr-4 border-r border-gray-200 dark:border-gray-700 pr-6">
              <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">System Status</p>
              <div className="flex items-center gap-2 text-green-500 font-bold text-sm">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                ACTIVE MONITORING
              </div>
            </div>
            <button 
              onClick={() => navigate('/admin/dashboard/test-creator')}
              className="px-6 py-3 rounded-2xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition shadow-xl shadow-blue-600/20 active:scale-95"
            >
              + Create Exam
            </button>
            <button 
              onClick={handleLogout}
              className="p-3 rounded-2xl bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
            </button>
          </div>
        </header>

        {/* Dynamic Stats Section */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <StatCard 
            title="Awaiting Approval" 
            value={Object.values(waitingExams).reduce((acc, curr) => acc + curr.students.length, 0)} 
            icon={<path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />}
            color="amber"
          />
          <StatCard 
            title="Live Sessions" 
            value={activeExamsCount} 
            icon={<path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />} 
            color="blue"
          />
          <StatCard 
            title="Recent Incidents" 
            value={recentAlerts.length} 
            icon={<path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />} 
            color="rose"
          />
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-10">
          
          {/* Main Waiting Room Area */}
          <div className="xl:col-span-2 space-y-8">
            <div className="bg-white dark:bg-gray-800 rounded-[2.5rem] p-10 border border-gray-100 dark:border-gray-700 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8">
                 <button onClick={fetchInitialState} className="text-gray-400 hover:text-blue-500 transition">
                   <svg className={`w-6 h-6 ${isLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                 </button>
              </div>

              <h2 className="text-3xl font-black text-gray-900 dark:text-white mb-8 flex items-center gap-4">
                <span className="w-1.5 h-10 bg-blue-600 rounded-full"></span>
                Waiting Rooms
              </h2>
              
              {Object.keys(waitingExams).length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 bg-gray-50/50 dark:bg-gray-900/30 rounded-[2rem] border-2 border-dashed border-gray-200 dark:border-gray-800">
                  <div className="text-6xl mb-4">💤</div>
                  <p className="text-gray-400 dark:text-gray-500 text-lg font-semibold">No students currently in queue.</p>
                </div>
              ) : (
                <div className="grid gap-8">
                  {Object.entries(waitingExams).map(([examId, exam]) => (
                    <div key={examId} className="bg-gray-50 dark:bg-gray-900/50 rounded-3xl border border-gray-200 dark:border-gray-700 p-8 group transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl hover:border-blue-500/20">
                      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                        <div className="space-y-1">
                          <h4 className="text-2xl font-black text-gray-900 dark:text-white leading-tight uppercase tracking-tight">{exam.title}</h4>
                          <div className="flex items-center gap-3">
                            <span className="text-xs font-bold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-3 py-1 rounded-full">
                              EXAM {examId}
                            </span>
                            <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">
                              {exam.students.length} Student{exam.students.length !== 1 ? 's' : ''}
                            </span>
                          </div>
                        </div>
                        <button 
                          onClick={() => handleStartExam(examId)}
                          className="w-full md:w-auto px-8 py-4 bg-green-600 hover:bg-green-700 text-white rounded-2xl font-black shadow-lg shadow-green-600/20 transition transform active:scale-95 group-hover:scale-105"
                        >
                          ALLOW ACCESS
                        </button>
                      </div>
                      
                      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {exam.students.map((student) => (
                          <div key={student.id} className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700">
                            <div className="flex items-center gap-4">
                              <div className="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 font-black text-lg">
                                {student.name[0]?.toUpperCase()}
                              </div>
                              <div>
                                <p className="text-sm font-bold text-gray-900 dark:text-white leading-none mb-1">{student.name}</p>
                                <p className="text-[10px] text-gray-400 font-medium">JOINED {new Date(student.time).toLocaleTimeString()}</p>
                              </div>
                            </div>
                            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar Area */}
          <div className="space-y-10">
            {/* Real-time Alerts */}
            <div className="bg-white dark:bg-gray-800 rounded-[2.5rem] p-10 border border-gray-100 dark:border-gray-700 shadow-xl">
              <h2 className="text-2xl font-black text-gray-900 dark:text-white mb-8">Violation Feed</h2>
              <div className="space-y-6">
                {recentAlerts.length === 0 ? (
                  <p className="text-gray-400 dark:text-gray-500 italic text-center py-10 border-2 border-dashed border-gray-100 dark:border-gray-800 rounded-3xl">
                    No active violations detected.
                  </p>
                ) : (
                    recentAlerts.map((alert, i) => (
                        <div key={i} className="relative pl-6 border-l-2 border-rose-500 group">
                           <div className="absolute -left-[5px] top-0 w-2 h-2 rounded-full bg-rose-500"></div>
                           <p className="text-sm font-black text-gray-900 dark:text-white uppercase leading-none mb-1">{alert.alert_type || alert.event_type}</p>
                           <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">Session: {alert.session_id?.slice(0,8)}...</p>
                           <p className="text-[10px] text-rose-500 font-bold mt-2">{new Date(alert.timestamp).toLocaleTimeString()}</p>
                        </div>
                    ))
                )}
              </div>
            </div>

            {/* Quick Tips */}
            <div className="bg-blue-600 rounded-[2.5rem] p-10 text-white shadow-2xl shadow-blue-600/30">
              <h3 className="text-2xl font-black mb-4 tracking-tight">Proctoring Guide</h3>
              <p className="text-blue-100 text-sm mb-8 leading-relaxed font-medium">
                Once you click <span className="font-bold underline">Allow Access</span>, students will transition into the secure exam environment where AI monitoring will begin immediately.
              </p>
              <div className="space-y-4">
                <div className="flex items-center gap-4 bg-white/10 p-4 rounded-3xl">
                  <div className="w-8 h-8 rounded-full bg-white text-blue-600 flex items-center justify-center font-black">!</div>
                  <p className="text-xs font-bold">Monitor the red pulses in the waiting room for ready status.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }) {
  const colors = {
    blue: "text-blue-600 bg-blue-50 dark:bg-blue-900/20 shadow-blue-500/10",
    amber: "text-amber-600 bg-amber-50 dark:bg-amber-900/20 shadow-amber-500/10",
    rose: "text-rose-600 bg-rose-50 dark:bg-rose-900/20 shadow-rose-500/10",
  };
  
  return (
    <div className="p-8 bg-white dark:bg-gray-800 rounded-[2rem] border border-gray-100 dark:border-gray-700 shadow-lg hover:shadow-2xl transition-all duration-300">
      <div className={`w-14 h-14 ${colors[color]} rounded-2xl flex items-center justify-center mb-6 shadow-xl`}>
        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">{icon}</svg>
      </div>
      <h3 className="text-gray-400 dark:text-gray-500 font-black text-sm uppercase tracking-widest">{title}</h3>
      <p className="text-5xl font-black text-gray-900 dark:text-white mt-2 tracking-tighter">{value}</p>
    </div>
  );
}
