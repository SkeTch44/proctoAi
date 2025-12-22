import { Navigate } from "react-router-dom";
import { getUser, getToken } from "../utils/authStorage";

export default function StudentRoute({ children }) {
  const token = getToken();
  const user = getUser();

  if (!token) return <Navigate to="/login" replace />;

  if (user?.role !== "student") return <Navigate to="/login" replace />;

  return children;
}
