import React, { useEffect, useState } from 'react';
import { getSocket } from '../services/socket';

export default function StatusDoodle({ sessionId }) {
  const [updates, setUpdates] = useState([]);

  useEffect(() => {
    const socket = getSocket();
    const onPerm = (data) => {
      if (!sessionId || data.session_id == sessionId) {
        setUpdates(u => [data, ...u].slice(0,5));
      }
    };
    socket.on('permission_update', onPerm);

    return () => {
      socket.off('permission_update', onPerm);
    };
  }, [sessionId]);

  return (
    <div className="fixed right-4 bottom-4 z-50">
      <div className="w-64 p-3 bg-white/90 dark:bg-[#07111a]/90 rounded-lg shadow-lg border border-gray-200">
        <div className="text-xs font-semibold mb-2">Monitoring Status</div>
        <div className="text-xs text-gray-600 dark:text-gray-300 max-h-40 overflow-auto">
          {updates.length === 0 ? (
            <div className="text-xs text-gray-400">No updates yet</div>
          ) : updates.map((u, i) => (
            <div key={i} className="mb-2">
              <div className="text-[10px] text-gray-700 dark:text-gray-200">{new Date(u.timestamp).toLocaleTimeString()}</div>
              <div className="text-[11px]">Permissions recorded</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
