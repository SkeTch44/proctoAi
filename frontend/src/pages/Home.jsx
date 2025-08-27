import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div>
      <h1>Welcome to Home Page</h1>
      <button onClick={() => navigate("/admin")}>Go to Admin Panel</button>
      <button onClick={() => navigate("/student")}>Go to Student Panel</button>
    </div>
  );
}
