// src/pages/StudentPages/StudentLayout.jsx
import StudentSidebar from "../../components/StudentSidebar";
import { Outlet } from "react-router-dom";

export default function StudentLayout() {
  return (
    <StudentSidebar>
      <Outlet />
    </StudentSidebar>
  );
}
