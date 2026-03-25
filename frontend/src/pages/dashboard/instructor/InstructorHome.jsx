import { useState, useEffect } from "react";
import { useAuth } from "../../../context/AuthContext";
import { Link } from "react-router-dom";
import { getMyCourses, getCourseAssignments, getAssignmentSubmissions } from "../../../services/api";

/* ── Status mapping from backend SubmissionState ─────────────────────── */
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
};
const STATUS_DOT = {
  "AI Graded": "bg-indigo-500", "Pending Review": "bg-amber-500",
  Processing: "bg-blue-500", Graded: "bg-emerald-500",
};

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_CLS[status] || "bg-slate-100 text-slate-500 border border-slate-200"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status] || "bg-slate-400"}`} />
      {status}
    </span>
  );
}

function StatCard({ title, value, subtitle, icon, iconBg, loading }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-200 group">
      <div className="flex items-start justify-between mb-5">
        <div className={`w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-200`}>
          {icon}
        </div>
      </div>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">{title}</p>
      <p className="text-3xl font-extrabold text-slate-900 dark:text-white mb-1 tracking-tight">{loading ? "…" : value}</p>
      <p className="text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>
    </div>
  );
}

export default function InstructorHome() {
  const { user } = useAuth();
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Instructor";

  const [courses,     setCourses]     = useState([]);
  const [submissions, setSubmissions] = useState([]);  // flat list across all assignments
  const [loading,     setLoading]     = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getMyCourses()
      .then(async (res) => {
        const fetchedCourses = res.data;
        if (cancelled) return;
        setCourses(fetchedCourses);

        // For each course, get assignments, then for each assignment get submissions
        const allSubs = [];
        await Promise.all(
          fetchedCourses.map(async (course) => {
            try {
              const assignRes = await getCourseAssignments(course.id);
              await Promise.all(
                assignRes.data.map(async (assignment) => {
                  try {
                    const subRes = await getAssignmentSubmissions(assignment.id);
                    subRes.data.forEach((sub) => {
                      allSubs.push({
                        id:         sub.id,
                        assignmentTitle: assignment.title,
                        courseCode: course.name,
                        submittedAt: new Date(sub.submitted_at).toLocaleDateString("en-US", {
                          month: "short", day: "numeric", year: "numeric",
                        }),
                        status: submissionStatus(sub.state),
                        studentId: sub.student_id,
                      });
                    });
                  } catch { /* skip */ }
                })
              );
            } catch { /* skip */ }
          })
        );

        if (!cancelled) setSubmissions(allSubs);
      })
      .catch(() => { if (!cancelled) { setCourses([]); setSubmissions([]); } })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const pending  = submissions.filter((s) => s.status === "Pending Review").length;
  const aiGraded = submissions.filter((s) => s.status === "AI Graded").length;
  const recent   = submissions.slice(0, 5);

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Welcome back, {displayName}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            Manage and grade your students' exam submissions
          </p>
        </div>
        <Link
          to="/instructor/grading"
          className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white text-sm font-semibold px-4 py-2.5 rounded-xl shadow-sm transition-all duration-150"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Grade Submissions
        </Link>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard loading={loading}
          title="My Courses" value={courses.length} subtitle="Active courses"
          iconBg="bg-blue-100 dark:bg-blue-900/30"
          icon={<svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>}
        />
        <StatCard loading={loading}
          title="Total Submissions" value={submissions.length} subtitle="Across all courses"
          iconBg="bg-slate-100 dark:bg-slate-700"
          icon={<svg className="w-6 h-6 text-slate-600 dark:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
        />
        <StatCard loading={loading}
          title="Pending Review" value={pending} subtitle="Awaiting your review"
          iconBg="bg-amber-100 dark:bg-amber-900/30"
          icon={<svg className="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard loading={loading}
          title="AI Graded" value={aiGraded} subtitle="Ready for review"
          iconBg="bg-indigo-100 dark:bg-indigo-900/30"
          icon={<svg className="w-6 h-6 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636-6.364l.707.707M12 21v-1M6.343 17.657l-.707-.707M17.657 17.657l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" /></svg>}
        />
      </div>

      {/* Recent Submissions */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Recent Submissions</h2>
          <Link to="/instructor/submissions" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors">
            View all →
          </Link>
        </div>

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
              ) : recent.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">No submissions yet.</td></tr>
              ) : recent.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors group">
                  <td className="px-6 py-4">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Student #{s.studentId}</p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-700 dark:text-slate-300 font-medium max-w-[180px] truncate">{s.assignmentTitle}</p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-1 rounded-md">{s.courseCode}</span>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-500 dark:text-slate-400">{s.submittedAt}</p>
                  </td>
                  <td className="px-4 py-4"><StatusBadge status={s.status} /></td>
                  <td className="px-6 py-4 text-right">
                    <Link to="/instructor/grading" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 px-3 py-1.5 rounded-lg transition-colors">
                      {s.status === "Pending Review" || s.status === "AI Graded" ? "Grade" : "View"}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Course Overview */}
      {!loading && courses.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {courses.map((c) => {
            const courseSubs = submissions.filter((s) => s.courseCode === c.name);
            const coursePending = courseSubs.filter((s) => s.status === "Pending Review").length;
            return (
              <div key={c.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <span className="text-xs font-bold px-2 py-1 rounded-md bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">{c.name.slice(0, 8)}</span>
                  {coursePending > 0 && (
                    <span className="text-xs font-semibold bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full">{coursePending} pending</span>
                  )}
                </div>
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1 truncate">{c.name}</p>
                {c.description && <p className="text-xs text-slate-400 dark:text-slate-500 truncate">{c.description}</p>}
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">{courseSubs.length} submission{courseSubs.length !== 1 ? "s" : ""}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
