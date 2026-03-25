import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import { getMySubmissions, getAssignment, getCourse } from "../../../services/api";

/* ── Submission state → display status mapping ───────────────────────── */
function submissionStatus(state, hasFinalGrade) {
  if (hasFinalGrade) return "Published";
  switch (state) {
    case "submitted":  return "Pending Review";
    case "processing": return "Processing";
    case "graded":     return "AI Graded";
    case "failed":     return "Failed";
    default:           return "Pending";
  }
}

/* ── Shared lookup caches to avoid duplicate requests ────────────────── */
const assignmentCache = {};
const courseCache = {};

async function fetchAssignment(id) {
  if (!assignmentCache[id]) {
    assignmentCache[id] = getAssignment(id).then((r) => r.data);
  }
  return assignmentCache[id];
}

async function fetchCourse(id) {
  if (!courseCache[id]) {
    courseCache[id] = getCourse(id).then((r) => r.data);
  }
  return courseCache[id];
}

/* ── UI helpers ──────────────────────────────────────────────────────── */
const STATUS_LIGHT = {
  Published:       "bg-emerald-50 text-emerald-700 border border-emerald-200",
  "Pending Review":"bg-amber-50 text-amber-700 border border-amber-200",
  Processing:      "bg-blue-50 text-blue-700 border border-blue-200",
  "AI Graded":     "bg-indigo-50 text-indigo-700 border border-indigo-200",
  Failed:          "bg-red-50 text-red-700 border border-red-200",
  Pending:         "bg-slate-100 text-slate-500 border border-slate-200",
};
const STATUS_DARK = {
  Published:       "dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800",
  "Pending Review":"dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  Processing:      "dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  "AI Graded":     "dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
  Failed:          "dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
  Pending:         "dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600",
};
const STATUS_DOT = {
  Published: "bg-emerald-500", "Pending Review": "bg-amber-500",
  Processing: "bg-blue-500", "AI Graded": "bg-indigo-500",
  Failed: "bg-red-500", Pending: "bg-slate-400",
};

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_LIGHT[status] || STATUS_LIGHT.Pending} ${STATUS_DARK[status] || STATUS_DARK.Pending}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status] || "bg-slate-400"} ${status === "Processing" ? "animate-pulse" : ""}`} />
      {status}
    </span>
  );
}

function GradeBar({ grade, max }) {
  const pct = Math.round((grade / max) * 100);
  const color = pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-blue-500" : "bg-amber-500";
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{grade}/{max}</span>
      <div className="w-16 h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle, icon, iconBg }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-200 group">
      <div className="flex items-start justify-between mb-5">
        <div className={`w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-200`}>
          {icon}
        </div>
      </div>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">{title}</p>
      <p className="text-3xl font-extrabold text-slate-900 dark:text-white mb-1 tracking-tight">{value}</p>
      <p className="text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>
    </div>
  );
}

const STATUSES = ["All Statuses", "Published", "AI Graded", "Pending Review", "Processing", "Failed"];
const selectCls = "text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm";

export default function StudentHome() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Student";

  const [rows, setRows]           = useState([]);
  const [loading, setLoading]     = useState(true);
  const [statusFilter, setStatus] = useState("All Statuses");
  const [courseFilter, setCourse] = useState("All Courses");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getMySubmissions()
      .then(async (res) => {
        const subs = res.data;
        const enriched = await Promise.all(
          subs.map(async (sub) => {
            try {
              const assignment = await fetchAssignment(sub.assignment_id);
              const course     = await fetchCourse(assignment.course_id);
              const status     = submissionStatus(sub.state, false);
              return {
                id:          sub.id,
                name:        assignment.title,
                course:      course.name,
                dueDate:     assignment.due_date
                  ? new Date(assignment.due_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
                  : "—",
                status,
                grade:    null,
                maxGrade: 100,
              };
            } catch {
              return null;
            }
          })
        );
        if (!cancelled) setRows(enriched.filter(Boolean));
      })
      .catch(() => { if (!cancelled) setRows([]); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const graded    = rows.filter((r) => r.grade !== null);
  const avgGrade  = graded.length > 0
    ? (graded.reduce((s, r) => s + Math.round((r.grade / r.maxGrade) * 100), 0) / graded.length).toFixed(1)
    : "—";

  const allCourses = ["All Courses", ...new Set(rows.map((r) => r.course))];

  const filtered = rows.filter((r) => {
    const matchCourse = courseFilter === "All Courses" || r.course === courseFilter;
    const matchStatus = statusFilter === "All Statuses" || r.status === statusFilter;
    return matchCourse && matchStatus;
  });

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Welcome back, {displayName}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            Track your exam submissions and grades
          </p>
        </div>
        <button
          onClick={() => navigate("/dashboard/upload")}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-sm font-semibold px-4 py-2.5 rounded-xl shadow-sm transition-all duration-150"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Submit Exam
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <StatCard
          title="Total Submissions" value={loading ? "…" : rows.length}
          subtitle="Across all assignments"
          iconBg="bg-blue-100 dark:bg-blue-900/30"
          icon={<svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
        />
        <StatCard
          title="Pending Review"
          value={loading ? "…" : rows.filter((r) => r.status === "Pending Review" || r.status === "Processing").length}
          subtitle="Awaiting results"
          iconBg="bg-orange-100 dark:bg-orange-900/30"
          icon={<svg className="w-6 h-6 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard
          title="Average Grade" value={loading ? "…" : avgGrade !== "—" ? `${avgGrade}%` : "—"}
          subtitle={`From ${graded.length} graded exam${graded.length !== 1 ? "s" : ""}`}
          iconBg="bg-emerald-100 dark:bg-emerald-900/30"
          icon={<svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
        />
      </div>

      {/* Assignments Section */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">My Submissions</h2>
        </div>

        {/* Filters */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-100 dark:border-slate-700 flex flex-wrap gap-4">
          <div className="flex flex-col gap-1 min-w-[180px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Course</label>
            <select value={courseFilter} onChange={(e) => setCourse(e.target.value)} className={selectCls}>
              {allCourses.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Status</label>
            <select value={statusFilter} onChange={(e) => setStatus(e.target.value)} className={selectCls}>
              {STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                {["Assignment Name", "Course", "Due Date", "Status", "Grade", "Action"].map((h, i) => (
                  <th key={h} className={`text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider py-3 ${i === 5 ? "text-right px-6" : i === 0 ? "text-left px-6" : "text-left px-4"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-slate-700/50">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <svg className="w-6 h-6 animate-spin text-slate-400 mx-auto" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">
                    {rows.length === 0 ? "No submissions yet. Submit your first exam!" : "No submissions match your filters."}
                  </td>
                </tr>
              ) : filtered.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors duration-100 group">
                  <td className="px-6 py-4">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{a.name}</p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded-md inline-block">{a.course}</p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-600 dark:text-slate-300 font-medium">{a.dueDate}</p>
                  </td>
                  <td className="px-4 py-4"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-4">
                    {a.grade !== null
                      ? <GradeBar grade={a.grade} max={a.maxGrade} />
                      : <span className="text-slate-300 dark:text-slate-600 text-sm font-medium">—</span>}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => navigate("/dashboard/submissions")}
                      className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-700">
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Showing {filtered.length} of {rows.length} submissions
          </p>
        </div>
      </div>
    </div>
  );
}
