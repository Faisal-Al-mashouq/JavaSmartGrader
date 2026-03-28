import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import { getMySubmissions } from "../../../services/submissionService";
import { getAssignment } from "../../../services/courseService";
import { getAIFeedback } from "../../../services/gradingService";

/* ── backend state → display status ─────────────────────────────── */
const stateToStatus = (state) => ({
  submitted:  "Processing",
  processing: "Processing",
  graded:     "AI Graded",
  failed:     "Failed",
}[state] ?? state);

/* ── visual helpers ─────────────────────────────────────────────── */
const STATUS_LIGHT = {
  "AI Graded":  "bg-indigo-50 text-indigo-700 border border-indigo-200",
  Processing:   "bg-blue-50 text-blue-700 border border-blue-200",
  Failed:       "bg-red-50 text-red-700 border border-red-200",
};
const STATUS_DARK = {
  "AI Graded":  "dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
  Processing:   "dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  Failed:       "dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
};
const STATUS_DOT = {
  "AI Graded": "bg-indigo-500",
  Processing:  "bg-blue-500",
  Failed:      "bg-red-500",
};

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
      ${STATUS_LIGHT[status] ?? "bg-slate-100 text-slate-500 border border-slate-200"}
      ${STATUS_DARK[status]  ?? "dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status] ?? "bg-slate-400"} ${status === "Processing" ? "animate-pulse" : ""}`} />
      {status}
    </span>
  );
}

function GradeBar({ grade, max }) {
  const pct   = Math.round((grade / max) * 100);
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

const selectCls = "text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm";

export default function StudentHome() {
  const { user }    = useAuth();
  const navigate    = useNavigate();
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Student";

  const [rows,         setRows]         = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [statusFilter, setStatusFilter] = useState("All Statuses");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        // 1. Fetch student's submissions
        const subsRes = await getMySubmissions();
        const subs    = subsRes.data; // SubmissionBase[]

        // 2. Fetch assignment details for each unique assignment_id (parallel)
        const uniqueAIds = [...new Set(subs.map((s) => s.assignment_id))];
        const asgResults = await Promise.all(
          uniqueAIds.map((id) => getAssignment(id).catch(() => null))
        );
        const asgMap = {};
        uniqueAIds.forEach((id, i) => {
          if (asgResults[i]) asgMap[id] = asgResults[i].data;
        });

        // 3. Fetch AI feedback for graded submissions (parallel)
        const gradedSubs = subs.filter((s) => s.state === "graded");
        const fbResults  = await Promise.all(
          gradedSubs.map((s) => getAIFeedback(s.id).catch(() => null))
        );
        const fbMap = {};
        gradedSubs.forEach((s, i) => {
          if (fbResults[i]) fbMap[s.id] = fbResults[i].data;
        });

        if (cancelled) return;

        const built = subs.map((s) => {
          const asgn  = asgMap[s.assignment_id];
          const fb    = fbMap[s.id];
          const grade = fb?.suggested_grade ?? null;
          return {
            id:        s.id,
            name:      asgn?.title ?? `Assignment #${s.assignment_id}`,
            courseId:  asgn?.course_id ?? "—",
            dueDate:   asgn?.due_date
              ? new Date(asgn.due_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
              : "—",
            status:    stateToStatus(s.state),
            grade:     grade !== null ? Math.round(grade) : null,
            maxGrade:  100,
          };
        });

        setRows(built);
      } catch (e) {
        console.error("StudentHome fetch error:", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  const STATUSES = ["All Statuses", "Processing", "AI Graded", "Failed"];

  const filtered = rows.filter((r) =>
    statusFilter === "All Statuses" || r.status === statusFilter
  );

  const graded     = rows.filter((r) => r.grade !== null);
  const processing = rows.filter((r) => r.status === "Processing").length;
  const avgGrade   = graded.length > 0
    ? (graded.reduce((s, r) => s + Math.round((r.grade / r.maxGrade) * 100), 0) / graded.length).toFixed(1)
    : "—";

  return (
    <div className="space-y-8">

      {/* Welcome */}
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
          title="Processing" value={processing} subtitle="Being graded by AI"
          iconBg="bg-blue-100 dark:bg-blue-900/30"
          icon={<svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard
          title="Total Submissions" value={rows.length} subtitle="Submitted this semester"
          iconBg="bg-indigo-100 dark:bg-indigo-900/30"
          icon={<svg className="w-6 h-6 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
        />
        <StatCard
          title="Average Grade" value={avgGrade !== "—" ? `${avgGrade}%` : "—"}
          subtitle={`From ${graded.length} graded exam${graded.length !== 1 ? "s" : ""}`}
          iconBg="bg-emerald-100 dark:bg-emerald-900/30"
          icon={<svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
        />
      </div>

      {/* Submissions Table */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">

        <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">My Submissions</h2>
        </div>

        {/* Filters */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-100 dark:border-slate-700 flex flex-wrap gap-4">
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Status</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className={selectCls}>
              {STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                {["#", "Assignment", "Course", "Due Date", "Status", "Grade"].map((h, i) => (
                  <th key={h} className={`text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider py-3 ${i === 0 ? "text-left px-6" : "text-left px-4"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-slate-700/50">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">
                    Loading submissions…
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">
                    {rows.length === 0 ? "No submissions yet. Submit your first exam!" : "No submissions match your filter."}
                  </td>
                </tr>
              ) : filtered.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors duration-100">
                  <td className="px-6 py-4 text-xs text-slate-400 dark:text-slate-500 font-mono">{r.id}</td>
                  <td className="px-4 py-4">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{r.name}</p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded-md">
                      Course {r.courseId}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-600 dark:text-slate-300 font-medium">{r.dueDate}</td>
                  <td className="px-4 py-4"><StatusBadge status={r.status} /></td>
                  <td className="px-4 py-4">
                    {r.grade !== null
                      ? <GradeBar grade={r.grade} max={r.maxGrade} />
                      : <span className="text-slate-300 dark:text-slate-600 text-sm font-medium">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-3 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-700">
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Showing {filtered.length} of {rows.length} submissions
          </p>
        </div>
      </div>
    </div>
  );
}
