import { Navigate } from "react-router-dom";
import { getUser, getToken } from "../utils/authStorage";

export default function AdminRoute({ children }) {
  const token = getToken();
  const user = getUser();

  // Not logged in
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Logged in but not admin
  if (user?.role !== "admin") {
    return <Navigate to="/login" replace />;
  }

  return children;
}
