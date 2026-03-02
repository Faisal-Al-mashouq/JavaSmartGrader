import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const NavLink = ({ to, exact, children }) => {
  const location = useLocation();
  const isActive = exact ? location.pathname === to : location.pathname === to;

  return (
    <Link
      to={to}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
        isActive
          ? "bg-blue-600 text-white shadow-sm"
          : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white"
      }`}
    >
      {children}
    </Link>
  );
};

function SunIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
      />
    </svg>
  );
}

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();

  const initials = user?.username ? user.username.slice(0, 2).toUpperCase() : "ST";
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Student";

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-300">
      {/* Top Navbar */}
      <nav className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 shadow-sm sticky top-0 z-50 transition-colors duration-300">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between h-16">

            {/* Logo */}
            <div className="flex items-center gap-3 min-w-[200px]">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center shadow-md">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight">Java Smart Grader</p>
                <p className="text-xs text-blue-600 dark:text-blue-400 font-semibold">Student Portal</p>
              </div>
            </div>

            {/* Nav Links */}
            <div className="flex items-center gap-1">
              <NavLink to="/dashboard" exact>Dashboard</NavLink>
              <NavLink to="/dashboard/submissions">Submissions</NavLink>
              <NavLink to="/dashboard/upload">Upload Exam</NavLink>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-2 min-w-[200px] justify-end">

              {/* Dark / Light toggle */}
              <button
                onClick={toggle}
                title={dark ? "Switch to light mode" : "Switch to dark mode"}
                className="p-2 rounded-lg text-slate-400 dark:text-slate-400 hover:text-amber-500 dark:hover:text-amber-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                {dark ? <SunIcon /> : <MoonIcon />}
              </button>

              {/* Notification Bell */}
              <button className="relative p-2 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white dark:ring-slate-800" />
              </button>

              <div className="w-px h-6 bg-slate-200 dark:bg-slate-600 mx-1" />

              {/* User Info */}
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-sm ring-2 ring-blue-100 dark:ring-blue-900">
                  <span className="text-xs font-bold text-white">{initials}</span>
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white leading-tight">{displayName}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">Student</p>
                </div>
              </div>

              {/* Logout */}
              <button
                onClick={logout}
                title="Logout"
                className="ml-1 p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                  />
                </svg>
              </button>

            </div>
          </div>
        </div>
      </nav>

      {/* Page Content — full width */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
