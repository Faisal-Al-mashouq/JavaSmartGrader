import { Outlet, Link } from "react-router-dom";

export default function InstructorLayout() {
  return (
    <div className="flex min-h-screen bg-slate-900 text-white">
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 p-6">
        <h2 className="text-xl font-bold mb-8">Instructor Panel</h2>

        <nav className="flex flex-col space-y-4">
          <Link to="/instructor" className="hover:text-blue-400">
            Dashboard
          </Link>

          <Link to="/instructor/submissions" className="hover:text-blue-400">
            Submissions
          </Link>

          <Link to="/instructor/grading" className="hover:text-blue-400">
            Grading
          </Link>
        </nav>
      </div>

      {/* Main content */}
      <div className="flex-1 p-8">
        <Outlet />
      </div>
    </div>
  );
}
