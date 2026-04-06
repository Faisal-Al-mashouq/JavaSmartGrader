import { useState, useEffect } from "react";
import { getMyCourses, getCourseAssignments } from "../../../services/courseService";
import { getAssignmentSubmissions } from "../../../services/submissionService";
import InstructorNavButton from "../../../components/InstructorNavButton";

/* ── helpers ─────────────────────────────────────────────────────── */
const STATE_LABEL = { submitted: "Processing", processing: "Processing", graded: "AI Graded", failed: "Failed" };
const STATUS_CLS  = {
  submitted:  "bg-blue-50 text-blue-600 border border-blue-200 dark:bg-blue-500/15 dark:text-blue-300 dark:border-blue-500/25",
  processing: "bg-blue-50 text-blue-600 border border-blue-200 dark:bg-blue-500/15 dark:text-blue-300 dark:border-blue-500/25",
  graded:     "bg-indigo-50 text-indigo-600 border border-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/25",
  failed:     "bg-red-50 text-red-600 border border-red-200 dark:bg-red-500/15 dark:text-red-300 dark:border-red-500/25",
};
const STATUS_DOT = { submitted: "bg-blue-500", processing: "bg-blue-500 animate-pulse", graded: "bg-indigo-500", failed: "bg-red-500" };

function StatusBadge({ state }) {
  const label = STATE_LABEL[state] ?? state;
  const cls   = STATUS_CLS[state]  ?? "bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-700 dark:text-slate-400";
  const dot   = STATUS_DOT[state]  ?? "bg-slate-400";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

const CARD_ACCENTS = [
  "from-blue-500 to-cyan-500",
  "from-amber-500 to-orange-500",
  "from-indigo-500 to-violet-500",
  "from-red-500 to-rose-500",
];

function StatCard({ title, value, subtitle, icon, accentIdx }) {
  const accent = CARD_ACCENTS[accentIdx % CARD_ACCENTS.length];
  return (
    <div className="relative bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-white/[0.08] hover:border-slate-300 dark:hover:border-white/[0.15] shadow-sm hover:shadow-md dark:shadow-lg transition-all duration-300 group overflow-hidden">
      <div className={`absolute -top-8 -right-8 w-28 h-28 rounded-full bg-gradient-to-br ${accent} opacity-[0.08] dark:opacity-[0.12] blur-2xl group-hover:opacity-[0.14] dark:group-hover:opacity-[0.2] transition-opacity duration-300`} />
      <div className="relative flex items-start justify-between mb-5">
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${accent} flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-300`}>
          {icon}
        </div>
      </div>
      <p className="relative text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{title}</p>
      <p className={`relative text-3xl font-extrabold tracking-tight bg-gradient-to-r ${accent} bg-clip-text text-transparent mb-1`}>
        {value}
      </p>
      <p className="relative text-xs text-slate-400 dark:text-slate-600">{subtitle}</p>
    </div>
  );
}

const selectCls = "text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900/70 border border-slate-200 dark:border-white/[0.1] rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm";

export default function InstructorSubmissions() {
  const [all,          setAll]          = useState([]);
  const [courses,      setCourses]      = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [courseFilter, setCourseFilter] = useState("All Courses");
  const [stateFilter,  setStateFilter]  = useState("All Statuses");
  const [search,       setSearch]       = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const coursesRes  = await getMyCourses();
        const courses     = coursesRes.data;

        const assignmentsByCoursePairs = await Promise.all(
          courses.map((c) =>
            getCourseAssignments(c.id)
              .then((r) => r.data.map((a) => ({ ...a, course: c })))
              .catch(() => [])
          )
        );
        const allAssignments = assignmentsByCoursePairs.flat();

        const subsByAssignmentPairs = await Promise.all(
          allAssignments.map((a) =>
            getAssignmentSubmissions(a.id)
              .then((r) => r.data.map((s) => ({ ...s, assignment: a, course: a.course })))
              .catch(() => [])
          )
        );
        const allSubs = subsByAssignmentPairs.flat();
        allSubs.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));

        if (!cancelled) {
          setCourses(courses);
          setAll(allSubs);
          setLoading(false);
        }
      } catch (e) {
        console.error("InstructorSubmissions fetch error:", e);
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  const filtered = all.filter((s) => {
    const matchCourse = courseFilter === "All Courses" || s.course?.name === courseFilter;
    const matchState  = stateFilter  === "All Statuses" || STATE_LABEL[s.state] === stateFilter;
    const matchSearch = search === "" ||
      String(s.student_id).includes(search) ||
      (s.assignment?.title ?? "").toLowerCase().includes(search.toLowerCase());
    return matchCourse && matchState && matchSearch;
  });

  const pending  = all.filter((s) => s.state === "submitted" || s.state === "processing").length;
  const aiGraded = all.filter((s) => s.state === "graded").length;
  const failed   = all.filter((s) => s.state === "failed").length;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">Submissions</p>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">All Submissions</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review and manage all student exam submissions</p>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard accentIdx={0} title="Total" value={loading ? "…" : all.length} subtitle="All submissions"
          icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
        />
        <StatCard accentIdx={1} title="Processing" value={loading ? "…" : pending} subtitle="Being graded by AI"
          icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard accentIdx={2} title="AI Graded" value={loading ? "…" : aiGraded} subtitle="Ready to review"
          icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636-6.364l.707.707M12 21v-1M6.343 17.657l-.707-.707M17.657 17.657l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" /></svg>}
        />
        <StatCard accentIdx={3} title="Failed" value={loading ? "…" : failed} subtitle="Needs attention"
          icon={<svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
      </div>

      {/* Table card */}
      <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl shadow-sm dark:shadow-xl border border-slate-200 dark:border-white/[0.08] overflow-hidden">

        {/* Filters */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-white/[0.02] border-b border-slate-100 dark:border-white/[0.06] flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1 flex-1 min-w-[180px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Search</label>
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input type="text" placeholder="Student ID or assignment…" value={search} onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900/70 border border-slate-200 dark:border-white/[0.1] rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
              />
            </div>
          </div>
          <div className="flex flex-col gap-1 min-w-[200px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Course</label>
            <select value={courseFilter} onChange={(e) => setCourseFilter(e.target.value)} className={selectCls}>
              <option>All Courses</option>
              {courses.map((c) => <option key={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Status</label>
            <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value)} className={selectCls}>
              {["All Statuses", "Processing", "AI Graded", "Failed"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 dark:border-white/[0.06]">
                {["Sub #", "Student", "Assignment", "Course", "Submitted", "Status", "Action"].map((h, i) => (
                  <th key={h} className={`text-[11px] font-bold text-slate-400 dark:text-slate-600 uppercase tracking-widest py-3 ${i === 6 ? "text-right px-6" : i === 0 ? "text-left px-6" : "text-left px-4"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-white/[0.04]">
              {loading ? (
                <tr><td colSpan={7} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">Loading submissions…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">No submissions match your filters.</td></tr>
              ) : filtered.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors">
                  <td className="px-6 py-4 text-xs text-slate-400 dark:text-slate-500 font-mono">#{s.id}</td>
                  <td className="px-4 py-4">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Student #{s.student_id}</p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-700 dark:text-slate-300 font-medium max-w-[180px] truncate">
                      {s.assignment?.title ?? `Assignment #${s.assignment_id}`}
                    </p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200 dark:border-indigo-500/20 px-2.5 py-1 rounded-lg">
                      {s.course?.name ?? `Course #${s.assignment?.course_id ?? "?"}`}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      {new Date(s.submitted_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </p>
                  </td>
                  <td className="px-4 py-4"><StatusBadge state={s.state} /></td>
                  <td className="px-6 py-4 text-right">
                    {s.state === "graded"
                      ? <InstructorNavButton to="/instructor/grading" variant="primary">Review AI</InstructorNavButton>
                      : <span className="text-xs font-semibold text-slate-400 dark:text-slate-600 px-3 py-1.5">—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-3 bg-slate-50 dark:bg-white/[0.02] border-t border-slate-100 dark:border-white/[0.06]">
          <p className="text-xs text-slate-400 dark:text-slate-600">Showing {filtered.length} of {all.length} submissions</p>
        </div>
      </div>
    </div>
  );
}
