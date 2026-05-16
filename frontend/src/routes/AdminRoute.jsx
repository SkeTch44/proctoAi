import { Navigate } from "react-router-dom";
import { getToken } from "../utils/authStorage";

export default function AdminRoute({ children }) {
  const token = getToken();

  // Logged in check (role check removed per user request)
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
