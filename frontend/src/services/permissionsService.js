import { getToken } from '../utils/authStorage';

export async function submitPermissions(sessionId, permissions) {
  const token = getToken();
  const res = await fetch('http://localhost:5000/api/submit_permissions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify({ session_id: sessionId, permissions })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || 'Failed to submit permissions');
  return data;
}
