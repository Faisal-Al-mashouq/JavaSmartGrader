import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const blobKeyframes = `
  @keyframes iblob1 {
    0%,100%{ transform:translate(0,0) scale(1); }
    33%    { transform:translate(60px,-40px) scale(1.08); }
    66%    { transform:translate(-30px,30px) scale(0.95); }
  }
  @keyframes iblob2 {
    0%,100%{ transform:translate(0,0) scale(1); }
    40%    { transform:translate(-50px,35px) scale(1.06); }
    70%    { transform:translate(35px,-25px) scale(0.97); }
  }
  @keyframes iblob3 {
    0%,100%{ transform:translate(0,0) scale(1); }
    50%    { transform:translate(25px,40px) scale(1.05); }
  }
`;

const NavLink = ({ to, end, children }) => {
  const location = useLocation();
  const isActive = end
    ? location.pathname === to
    : location.pathname === to || location.pathname.startsWith(`${to}/`);
  return (
    <Link
      to={to}
      className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 ${
        isActive
          ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-900/40"
          : "text-slate-400 hover:text-white hover:bg-white/8"
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
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  );
}

export default function InstructorLayout() {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();

  const initials    = user?.username ? user.username.slice(0, 2).toUpperCase() : "IN";
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Instructor";

  return (
    <>
      <style>{blobKeyframes}</style>

      <div className="min-h-screen bg-slate-950 transition-colors duration-300 relative overflow-x-hidden">

        {/* ── background blobs ── */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div style={{ animation: "iblob1 35s ease-in-out infinite" }}
            className="absolute -top-60 -left-40 w-[600px] h-[600px] rounded-full bg-indigo-700 opacity-[0.07] blur-[130px]" />
          <div style={{ animation: "iblob2 42s ease-in-out infinite 5s" }}
            className="absolute top-1/2 -right-60 w-[550px] h-[550px] rounded-full bg-violet-700 opacity-[0.07] blur-[130px]" />
          <div style={{ animation: "iblob3 28s ease-in-out infinite 10s" }}
            className="absolute -bottom-40 left-1/3 w-[450px] h-[450px] rounded-full bg-blue-700 opacity-[0.06] blur-[110px]" />
        </div>

        {/* ── Navbar ── */}
        <nav className="sticky top-0 z-50 bg-slate-900/75 backdrop-blur-xl border-b border-white/[0.08] shadow-xl shadow-black/20">
          <div className="max-w-7xl mx-auto px-6">
            <div className="flex items-center justify-between h-16">

              {/* Logo */}
              <div className="flex items-center gap-3 min-w-[200px]">
                <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-900/50">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-bold text-white leading-tight">Java Smart Grader</p>
                  <p className="text-[11px] font-semibold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
                    Instructor Panel
                  </p>
                </div>
              </div>

              {/* Nav Links */}
              <div className="flex items-center gap-1">
                <NavLink to="/instructor" end>Overview</NavLink>
                <NavLink to="/instructor/courses">Courses</NavLink>
                <NavLink to="/instructor/submissions" end>Submissions</NavLink>
                <NavLink to="/instructor/grading" end>Grading</NavLink>
              </div>

              {/* Right */}
              <div className="flex items-center gap-2 min-w-[200px] justify-end">
                <button onClick={toggle} title={dark ? "Light mode" : "Dark mode"}
                  className="p-2 rounded-lg text-slate-500 hover:text-amber-400 hover:bg-white/8 transition-colors">
                  {dark ? <SunIcon /> : <MoonIcon />}
                </button>

                <button className="relative p-2 text-slate-500 hover:text-slate-300 hover:bg-white/8 rounded-lg transition-colors">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-slate-900" />
                </button>

                <div className="w-px h-6 bg-white/10 mx-1" />

                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-full flex items-center justify-center shadow-md ring-2 ring-indigo-500/30">
                    <span className="text-xs font-bold text-white">{initials}</span>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white leading-tight">{displayName}</p>
                    <p className="text-[11px] text-slate-500">Instructor</p>
                  </div>
                </div>

                <button onClick={logout} title="Logout"
                  className="ml-1 p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </nav>

        {/* Page Content */}
        <main className="max-w-7xl mx-auto px-6 py-8 relative">
          <Outlet />
        </main>
      </div>
    </>
  );
}
