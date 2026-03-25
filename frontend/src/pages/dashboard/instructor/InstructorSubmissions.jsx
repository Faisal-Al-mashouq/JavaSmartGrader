import { useState, useEffect } from "react";
import { getMyCourses, getCourseAssignments, getAssignmentSubmissions } from "../../../services/api";

/* ── Status mapping ──────────────────────────────────────────────────── */
function submissionStatus(state) {
  switch (state) {
    case "submitted":  return "Pending Review";
    case "processing": return "Processing";
    case "graded":     return "AI Graded";
    case "failed":     return "Failed";
    default:           return state;
  }
}

const STATUS_CLS = {
  "AI Graded":     "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
  "Pending Review":"bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  Processing:      "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  Graded:          "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800",
  Failed:          "bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
};
const STATUS_DOT = {
  "AI Graded": "bg-indigo-500", "Pending Review": "bg-amber-500",
  Processing: "bg-blue-500", Graded: "bg-emerald-500", Failed: "bg-red-500",
};

function StatusBadge({ status }) {
  const cls = STATUS_CLS[status] ?? "bg-slate-100 text-slate-500 border border-slate-200";
  const dot = STATUS_DOT[status] ?? "bg-slate-400";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot} ${status === "Processing" ? "animate-pulse" : ""}`} />
      {status}
    </span>
  );
}

const STATUSES = ["All Statuses", "AI Graded", "Pending Review", "Processing", "Graded", "Failed"];
const selectCls = "text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm";

export default function InstructorSubmissions() {
  const [all,     setAll]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [courseFilter, setCourseFilter] = useState("All Courses");
  const [statusFilter, setStatusFilter] = useState("All Statuses");
  const [search,       setSearch]       = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getMyCourses()
      .then(async (res) => {
        const courses = res.data;
        const rows = [];

        await Promise.all(
          courses.map(async (course) => {
            try {
              const assignRes = await getCourseAssignments(course.id);
              await Promise.all(
                assignRes.data.map(async (assignment) => {
                  try {
                    const subRes = await getAssignmentSubmissions(assignment.id);
                    subRes.data.forEach((sub) => {
                      rows.push({
                        id:             sub.id,
                        studentId:      sub.student_id,
                        assignmentTitle: assignment.title,
                        courseName:     course.name,
                        submittedAt:    new Date(sub.submitted_at).toLocaleDateString("en-US", {
                          month: "short", day: "numeric", year: "numeric",
                        }),
                        status:   submissionStatus(sub.state),
                        imageUrl: sub.image_url,
                        rawState: sub.state,
                      });
                    });
                  } catch { /* skip */ }
                })
              );
            } catch { /* skip */ }
          })
        );

        if (!cancelled) setAll(rows);
      })
      .catch(() => { if (!cancelled) setAll([]); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const allCourses = ["All Courses", ...new Set(all.map((s) => s.courseName))];

  const filtered = all.filter((s) => {
    const matchCourse = courseFilter === "All Courses" || s.courseName === courseFilter;
    const matchStatus = statusFilter === "All Statuses" || s.status === statusFilter;
    const matchSearch = search === "" ||
      String(s.studentId).includes(search) ||
      s.assignmentTitle.toLowerCase().includes(search.toLowerCase());
    return matchCourse && matchStatus && matchSearch;
  });

  const pending  = all.filter((s) => s.status === "Pending Review").length;
  const aiGraded = all.filter((s) => s.status === "AI Graded").length;
  const graded   = all.filter((s) => s.status === "Graded").length;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">All Submissions</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review and manage all student exam submissions</p>
        </div>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Total",          value: loading ? "…" : all.length,     iconCls: "text-indigo-600 dark:text-indigo-400",  bg: "bg-indigo-50 dark:bg-indigo-900/30",  path: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
          { label: "Pending Review", value: loading ? "…" : pending,         iconCls: "text-amber-600 dark:text-amber-400",    bg: "bg-amber-50 dark:bg-amber-900/30",    path: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" },
          { label: "AI Graded",      value: loading ? "…" : aiGraded,        iconCls: "text-indigo-600 dark:text-indigo-400",  bg: "bg-indigo-50 dark:bg-indigo-900/30",  path: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636-6.364l.707.707M12 21v-1M6.343 17.657l-.707-.707M17.657 17.657l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" },
          { label: "Graded",         value: loading ? "…" : graded,          iconCls: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-900/30", path: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
        ].map(({ label, value, iconCls, bg, path }) => (
          <div key={label} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm px-5 py-4 flex items-center gap-3 hover:shadow-md transition-shadow">
            <div className={`w-9 h-9 rounded-xl ${bg} flex items-center justify-center shrink-0`}>
              <svg className={`w-5 h-5 ${iconCls}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={path} />
              </svg>
            </div>
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500 font-medium">{label}</p>
              <p className="text-lg font-extrabold text-slate-900 dark:text-white">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Table card */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
        {/* Filters */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-100 dark:border-slate-700 flex flex-wrap items-end gap-4">
          <div className="flex flex-col gap-1 flex-1 min-w-[180px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Search</label>
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input type="text" placeholder="Student ID or assignment..." value={search} onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
              />
            </div>
          </div>
          <div className="flex flex-col gap-1 min-w-[200px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Course</label>
            <select value={courseFilter} onChange={(e) => setCourseFilter(e.target.value)} className={selectCls}>
              {allCourses.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
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
                {["Student", "Assignment", "Course", "Submitted", "Status", "Action"].map((h, i) => (
                  <th key={h} className={`text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider py-3 ${i === 5 ? "text-right px-6" : i === 0 ? "text-left px-6" : "text-left px-4"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-slate-700/50">
              {loading ? (
                <tr><td colSpan={6} className="text-center py-12">
                  <svg className="w-6 h-6 animate-spin text-slate-400 mx-auto" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                </td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">No submissions match your filters.</td></tr>
              ) : filtered.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors group">
                  <td className="px-6 py-4">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Student #{s.studentId}</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">ID: {s.studentId}</p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-700 dark:text-slate-300 font-medium max-w-[180px] truncate">{s.assignmentTitle}</p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-1 rounded-md">{s.courseName}</span>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-500 dark:text-slate-400">{s.submittedAt}</p>
                  </td>
                  <td className="px-4 py-4"><StatusBadge status={s.status} /></td>
                  <td className="px-6 py-4 text-right">
                    {(s.status === "Pending Review" || s.status === "AI Graded")
                      ? <a href={`/instructor/grading?submission=${s.id}`} className="text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg transition-colors active:scale-95 inline-block">
                          {s.status === "AI Graded" ? "Review AI" : "Grade"}
                        </a>
                      : <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 px-3 py-1.5">—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-3 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-700">
          <p className="text-xs text-slate-400 dark:text-slate-500">
            Showing {filtered.length} of {all.length} submissions
          </p>
        </div>
      </div>
    </div>
  );
}
