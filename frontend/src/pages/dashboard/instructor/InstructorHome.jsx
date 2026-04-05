import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { useAuth } from "../../../context/AuthContext";
import { getMyCourses, getCourseAssignments } from "../../../services/courseService";
import { getAssignmentSubmissions } from "../../../services/submissionService";

/* ── status styling ───────────────────────────────────────────── */
const STATUS_CLS = {
  submitted:  "bg-blue-500/15 text-blue-300 border border-blue-500/25",
  processing: "bg-blue-500/15 text-blue-300 border border-blue-500/25",
  graded:     "bg-indigo-500/15 text-indigo-300 border border-indigo-500/25",
  failed:     "bg-red-500/15 text-red-300 border border-red-500/25",
};
const STATUS_DOT = {
  submitted:  "bg-blue-400",
  processing: "bg-blue-400 animate-pulse",
  graded:     "bg-indigo-400",
  failed:     "bg-red-400",
};
const STATE_LABEL = { submitted: "Processing", processing: "Processing", graded: "AI Graded", failed: "Failed" };

function StatusBadge({ state }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_CLS[state] ?? "bg-slate-700 text-slate-400"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[state] ?? "bg-slate-500"}`} />
      {STATE_LABEL[state] ?? state}
    </span>
  );
}

/* ── stat card ─────────────────────────────────────────────────── */
const CARD_ACCENTS = [
  "from-blue-500 to-cyan-500",
  "from-amber-500 to-orange-500",
  "from-indigo-500 to-violet-500",
  "from-emerald-500 to-teal-500",
];

function StatCard({ title, value, subtitle, icon, accentIdx, trend, trendUp }) {
  const accent = CARD_ACCENTS[accentIdx % CARD_ACCENTS.length];
  return (
    <div className="relative bg-slate-900/70 backdrop-blur-sm rounded-2xl p-6 border border-white/[0.08] hover:border-white/[0.15] shadow-lg hover:shadow-xl transition-all duration-300 group overflow-hidden">
      {/* gradient glow top-right */}
      <div className={`absolute -top-8 -right-8 w-28 h-28 rounded-full bg-gradient-to-br ${accent} opacity-[0.12] blur-2xl group-hover:opacity-[0.2] transition-opacity duration-300`} />

      <div className="relative flex items-start justify-between mb-5">
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${accent} flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-300`}>
          {icon}
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg ${trendUp ? "text-emerald-400 bg-emerald-500/15" : "text-red-400 bg-red-500/15"}`}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d={trendUp ? "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" : "M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"} />
            </svg>
            {trend}
          </div>
        )}
      </div>

      <p className="relative text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{title}</p>
      <p className={`relative text-3xl font-extrabold tracking-tight bg-gradient-to-r ${accent} bg-clip-text text-transparent mb-1`}>
        {value}
      </p>
      <p className="relative text-xs text-slate-600">{subtitle}</p>
    </div>
  );
}

/* ── main ──────────────────────────────────────────────────────── */
export default function InstructorHome() {
  const { user } = useAuth();
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Instructor";

  const [courses, setCourses]     = useState([]);
  const [allSubs, setAllSubs]     = useState([]);
  const [recentSubs, setRecentSubs] = useState([]);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const coursesRes = await getMyCourses();
        const courses = coursesRes.data;
        const assignmentsByCoursePairs = await Promise.all(
          courses.map((c) =>
            getCourseAssignments(c.id)
              .then((r) => r.data.map((a) => ({ ...a, course: c })))
              .catch(() => []),
          ),
        );
        const allAssignments = assignmentsByCoursePairs.flat();
        const subsByAssignmentPairs = await Promise.all(
          allAssignments.map((a) =>
            getAssignmentSubmissions(a.id)
              .then((r) => r.data.map((s) => ({ ...s, assignment: a, course: a.course })))
              .catch(() => []),
          ),
        );
        const allSubmissions = subsByAssignmentPairs.flat();
        allSubmissions.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
        if (!cancelled) {
          setCourses(courses);
          setAllSubs(allSubmissions);
          setRecentSubs(allSubmissions.slice(0, 5));
          setLoading(false);
        }
      } catch (e) {
        console.error("InstructorHome fetch error:", e);
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  const pending   = allSubs.filter((s) => s.state === "submitted" || s.state === "processing").length;
  const aiGraded  = allSubs.filter((s) => s.state === "graded").length;

  return (
    <div className="space-y-8">

      {/* ── Welcome ── */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs font-semibold text-indigo-400 uppercase tracking-widest mb-1">Dashboard</p>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Welcome back, <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">{displayName}</span>
          </h1>
          <p className="text-slate-500 mt-1 text-sm">Manage and grade your students' exam submissions</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <InstructorNavButton to="/instructor/courses" variant="primary">Courses</InstructorNavButton>
          <InstructorNavButton to="/instructor/submissions">Submissions</InstructorNavButton>
          <InstructorNavButton to="/instructor/grading">Grading</InstructorNavButton>
        </div>
      </div>

      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Link to="/instructor/courses" className="block focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-2xl">
          <StatCard accentIdx={0} title="Courses" value={courses.length} subtitle="Manage courses & enrollments"
            icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>}
          />
        </Link>
        <StatCard accentIdx={1} title="Processing" value={loading ? "…" : pending} subtitle="Being graded by AI"
          icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard accentIdx={2} title="AI Graded" value={loading ? "…" : aiGraded} subtitle="Ready to review"
          icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636-6.364l.707.707M12 21v-1M6.343 17.657l-.707-.707M17.657 17.657l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" /></svg>}
        />
        <StatCard accentIdx={3} title="Total Submissions" value={loading ? "…" : allSubs.length} subtitle="Across all courses"
          icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
      </div>

      {/* ── Recent Submissions ── */}
      <div className="bg-slate-900/70 backdrop-blur-sm rounded-2xl border border-white/[0.08] shadow-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.07] flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Recent Submissions</h2>
            <p className="text-xs text-slate-600 mt-0.5">Latest activity across all courses</p>
          </div>
          <InstructorNavButton to="/instructor/submissions">View all</InstructorNavButton>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.06]">
                {["Student ID","Assignment","Course","Submitted","Status","Action"].map((h, i) => (
                  <th key={h}
                    className={`text-[11px] font-bold text-slate-600 uppercase tracking-widest py-3
                      ${i === 5 ? "text-right px-6" : i === 0 ? "text-left px-6" : "text-left px-4"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {loading ? (
                <tr><td colSpan={6} className="text-center py-14 text-slate-600 text-sm">Loading…</td></tr>
              ) : recentSubs.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-14 text-slate-600 text-sm">No submissions yet.</td></tr>
              ) : (
                recentSubs.map((s) => (
                  <tr key={s.id} className="hover:bg-white/[0.03] transition-colors group">
                    <td className="px-6 py-4">
                      <p className="text-sm font-semibold text-slate-200 font-mono">Student #{s.student_id}</p>
                      <p className="text-xs text-slate-600">Sub #{s.id}</p>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm text-slate-300 font-medium max-w-[180px] truncate">
                        {s.assignment?.title ?? `#${s.assignment_id}`}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <span className="text-xs font-bold text-indigo-400 bg-indigo-500/15 border border-indigo-500/20 px-2.5 py-1 rounded-lg">
                        {s.course?.name ?? `Course #${s.assignment?.course_id}`}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm text-slate-500">
                        {new Date(s.submitted_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </p>
                    </td>
                    <td className="px-4 py-4"><StatusBadge state={s.state} /></td>
                    <td className="px-6 py-4 text-right">
                      <InstructorNavButton to="/instructor/grading" variant="primary">
                        {s.state === "graded" ? "Review" : "View"}
                      </InstructorNavButton>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Course Overview ── */}
      {courses.length > 0 && (
        <div>
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">Your Courses</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {courses.map((c, idx) => {
              const courseSubs    = allSubs.filter((s) => s.course?.id === c.id);
              const processingCnt = courseSubs.filter((s) => s.state === "submitted" || s.state === "processing").length;
              const gradedCnt     = courseSubs.filter((s) => s.state === "graded").length;
              const accent        = CARD_ACCENTS[idx % CARD_ACCENTS.length];
              return (
                <Link key={c.id} to={`/instructor/courses/${c.id}`}
                  className="group block relative bg-slate-900/70 backdrop-blur-sm rounded-2xl border border-white/[0.08] hover:border-white/[0.18] shadow-lg p-5 transition-all duration-300 overflow-hidden focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  {/* gradient glow */}
                  <div className={`absolute -top-6 -right-6 w-24 h-24 rounded-full bg-gradient-to-br ${accent} opacity-[0.1] blur-2xl group-hover:opacity-[0.18] transition-opacity duration-300`} />

                  <div className="relative flex items-start justify-between mb-3">
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-lg bg-gradient-to-r ${accent} bg-clip-text text-transparent border border-white/[0.1]`}>
                      #{c.id}
                    </span>
                    {processingCnt > 0 && (
                      <span className="text-xs font-semibold bg-amber-500/15 border border-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">
                        {processingCnt} processing
                      </span>
                    )}
                  </div>
                  <p className="relative text-sm font-bold text-white mb-4 group-hover:text-indigo-300 transition-colors">
                    {c.name}
                  </p>
                  <div className="relative space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-600">Total Submissions</span>
                      <span className="font-bold text-slate-300">{courseSubs.length}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-600">AI Graded</span>
                      <span className="font-bold text-slate-300">{gradedCnt}</span>
                    </div>
                    {/* mini progress bar */}
                    {courseSubs.length > 0 && (
                      <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden mt-1">
                        <div className={`h-full rounded-full bg-gradient-to-r ${accent} transition-all duration-500`}
                          style={{ width: `${Math.round((gradedCnt / courseSubs.length) * 100)}%` }} />
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
