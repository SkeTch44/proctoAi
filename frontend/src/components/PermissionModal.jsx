import React, { useEffect, useState, useRef } from 'react';
import { submitPermissions } from '../services/permissionsService';
import { getSocket } from '../services/socket';

export default function PermissionModal({ open, onClose, sessionId }) {
  const [status, setStatus] = useState({
    camera: false,
    mic: false,
    screen: false,
    fullscreen: false,
    visibility: document.visibilityState,
    remoteDesktop: false,
    keyboardEvents: 0,
  });

  const videoRef = useRef(null);
  const socket = useRef(null);

  useEffect(() => {
    if (!open) return;

    socket.current = getSocket();

    const onVisibility = () => setStatus(s => ({ ...s, visibility: document.visibilityState }));
    document.addEventListener('visibilitychange', onVisibility);

    const onKey = () => setStatus(s => ({ ...s, keyboardEvents: s.keyboardEvents + 1 }));
    window.addEventListener('keydown', onKey);

    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const requestCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setStatus(s => ({ ...s, camera: true, mic: true }));
      if (videoRef.current) videoRef.current.srcObject = stream;

      // send periodic snapshots if socket connected
      if (socket.current && sessionId) {
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play().catch(()=>{});
        const canvas = document.createElement('canvas');
        const sendSnapshot = () => {
          try {
            canvas.width = video.videoWidth || 320;
            canvas.height = video.videoHeight || 240;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const data = canvas.toDataURL('image/jpeg', 0.4);
            socket.current.emit('proctoring_data', { session_id: sessionId, frame_data: data });
          } catch (e) {}
        };
        const iv = setInterval(sendSnapshot, 5000);
        // stop interval when modal closed
        video.onended = () => clearInterval(iv);
      }
    } catch (err) {
      console.error('camera err', err);
    }
  };

  const requestScreen = async () => {
    try {
      const s = await navigator.mediaDevices.getDisplayMedia({ video: true });
      setStatus(st => ({ ...st, screen: true }));
    } catch (err) {
      console.error('screen err', err);
    }
  };

  const requestFullscreen = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
      setStatus(s => ({ ...s, fullscreen: document.fullscreenElement !== null }));
    } catch (err) {
      console.error('fullscreen err', err);
    }
  };

  const detectRemoteDesktop = () => {
    // heuristic checks
    const ua = navigator.userAgent || '';
    const remote = /remote|rdp|teamviewer|anydesk|vnc|chromeremote/i.test(ua);
    setStatus(s => ({ ...s, remoteDesktop: remote }));
    return remote;
  };

  const handleAccept = async () => {
    const permissionsPayload = { ...status, detectedAt: new Date().toISOString() };
    try {
      await submitPermissions(sessionId, permissionsPayload);
    } catch (e) {
      console.error('submit permissions failed', e);
    }
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-2xl bg-white dark:bg-[#0b1220] rounded-xl p-6 shadow-lg">
        <h3 className="text-xl font-semibold mb-2 text-gray-800 dark:text-gray-100">Exam Permissions & Instructions</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">We require a few permissions for proctoring and integrity checks. Camera is mandatory and will be monitored in real-time. You can preview your camera below.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="mb-2 font-medium">Camera & Microphone</div>
            <video ref={videoRef} autoPlay muted playsInline className="w-full h-48 bg-black rounded" />
            <div className="flex gap-2 mt-2">
              <button onClick={requestCamera} className="px-3 py-2 rounded bg-blue-600 text-white">Allow Camera & Mic</button>
            </div>
          </div>

          <div>
            <div className="mb-2 font-medium">Screen & Fullscreen</div>
            <div className="h-48 bg-gray-100 dark:bg-[#07111a] rounded flex items-center justify-center text-sm text-gray-500">Screen preview will appear here after allow</div>
            <div className="flex gap-2 mt-2">
              <button onClick={requestScreen} className="px-3 py-2 rounded bg-indigo-600 text-white">Share Screen (optional)</button>
              <button onClick={requestFullscreen} className="px-3 py-2 rounded bg-green-600 text-white">Enter Fullscreen</button>
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-600 dark:text-gray-300">
            <div>Visibility: {status.visibility}</div>
            <div>Keyboard events detected: {status.keyboardEvents}</div>
            <div>Remote desktop heuristic: {status.remoteDesktop ? 'Detected' : 'Not detected'}</div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { detectRemoteDesktop(); }} className="px-3 py-2 rounded bg-yellow-500 text-white">Check Remote Desktop</button>
            <button onClick={handleAccept} className="px-4 py-2 rounded bg-primary text-white">Accept & Continue</button>
          </div>
        </div>
      </div>
    </div>
  );
}
