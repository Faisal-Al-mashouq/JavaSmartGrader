import { Outlet, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function DashboardLayout() {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen flex bg-gray-900 text-white">

      {/* Sidebar */}
      <aside className="w-64 bg-gray-800 p-6 space-y-6">
        <h2 className="text-xl font-bold">JavaSmartGrader</h2>

        <nav className="flex flex-col space-y-3">
          <Link to="/dashboard" className="hover:text-blue-400">
            Dashboard
          </Link>

          <Link to="/dashboard/submissions" className="hover:text-blue-400">
            Submissions
          </Link>

          <Link to="/dashboard/upload" className="hover:text-blue-400">
            Upload
          </Link>
        </nav>

        <button
          onClick={logout}
          className="mt-6 bg-red-600 px-3 py-1 rounded"
        >
          Logout
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-10">
        <Outlet />
      </main>
    </div>
  );
}