import { Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function MainLayout() {
  const { user, logout } = useAuth();

  return (
    <>
      <nav className="bg-black text-white p-4 flex justify-between">
        <span>JavaSmartGrader</span>

        {user && (
          <button
            onClick={logout}
            className="bg-red-600 px-3 py-1 rounded"
          >
            Logout
          </button>
        )}
      </nav>

      <Outlet />
    </>
  );
}