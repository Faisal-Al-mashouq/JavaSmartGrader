import { useAuth } from "../../../context/AuthContext";
import { Link } from "react-router-dom";

const RECENT_SUBMISSIONS = [
  { id: 1, student: "Ahmed Al-Rashid",    sid: "443001", assignment: "Midterm Exam - OOP Concepts",   course: "CS201", submitted: "Nov 30, 2024", status: "Graded",         grade: 87  },
  { id: 2, student: "Sara Al-Otaibi",     sid: "443002", assignment: "Lab Assignment 3 - Inheritance", course: "CS201", submitted: "Dec 4, 2024",  status: "Pending Review", grade: null },
  { id: 3, student: "Mohammed Al-Ghamdi", sid: "443003", assignment: "Quiz 2 - Exception Handling",   course: "CS201", submitted: "Dec 7, 2024",  status: "Processing",     grade: null },
  { id: 4, student: "Fatima Al-Zahraa",   sid: "443004", assignment: "Assignment 2 - Data Structures", course: "CS301", submitted: "Dec 9, 2024",  status: "Graded",         grade: 92  },
  { id: 5, student: "Khalid Al-Anazi",    sid: "443005", assignment: "Practical Exam 1",              course: "CS150", submitted: "Nov 27, 2024", status: "Graded",         grade: 78  },
];

const STATUS_CLS = {
  Graded:          "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800",
  "Pending Review":"bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  Processing:      "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
};
const STATUS_DOT = { Graded: "bg-emerald-500", "Pending Review": "bg-amber-500", Processing: "bg-blue-500" };

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_CLS[status] || "bg-slate-100 text-slate-500 border border-slate-200"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status] || "bg-slate-400"}`} />
      {status}
    </span>
  );
}

function StatCard({ title, value, subtitle, icon, iconBg, trend, trendUp }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-200 group">
      <div className="flex items-start justify-between mb-5">
        <div className={`w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-200`}>
          {icon}
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg ${trendUp ? "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30" : "text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/30"}`}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={trendUp ? "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" : "M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"} />
            </svg>
            {trend}
          </div>
        )}
      </div>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">{title}</p>
      <p className="text-3xl font-extrabold text-slate-900 dark:text-white mb-1 tracking-tight">{value}</p>
      <p className="text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>
    </div>
  );
}

export default function InstructorHome() {
  const { user } = useAuth();
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Instructor";

  const pending = RECENT_SUBMISSIONS.filter((s) => s.status === "Pending Review").length;
  const graded  = RECENT_SUBMISSIONS.filter((s) => s.status === "Graded");
  const avg = graded.length > 0
    ? (graded.reduce((sum, s) => sum + s.grade, 0) / graded.length).toFixed(1)
    : "—";

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
        <div className="flex gap-2">
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
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Total Students" value="48" subtitle="Across 3 courses"
          iconBg="bg-blue-100 dark:bg-blue-900/30" trend="+3 this week" trendUp
          icon={<svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>}
        />
        <StatCard
          title="Pending Grading" value={pending} subtitle="Awaiting your review"
          iconBg="bg-amber-100 dark:bg-amber-900/30"
          icon={<svg className="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard
          title="Graded" value={graded.length} subtitle="This semester"
          iconBg="bg-emerald-100 dark:bg-emerald-900/30" trend="+5 today" trendUp
          icon={<svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard
          title="Class Average" value={avg !== "—" ? `${avg}%` : "—"} subtitle="Across graded exams"
          iconBg="bg-indigo-100 dark:bg-indigo-900/30" trend="+1.2%" trendUp
          icon={<svg className="w-6 h-6 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
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
                {["Student", "Assignment", "Course", "Submitted", "Status", "Grade", "Action"].map((h, i) => (
                  <th key={h} className={`text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider py-3 ${i === 6 ? "text-right px-6" : i === 0 ? "text-left px-6" : "text-left px-4"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-slate-700/50">
              {RECENT_SUBMISSIONS.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors group">
                  <td className="px-6 py-4">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{s.student}</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">ID: {s.sid}</p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-700 dark:text-slate-300 font-medium max-w-[180px] truncate">{s.assignment}</p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-1 rounded-md">{s.course}</span>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-slate-500 dark:text-slate-400">{s.submitted}</p>
                  </td>
                  <td className="px-4 py-4"><StatusBadge status={s.status} /></td>
                  <td className="px-4 py-4">
                    {s.grade !== null
                      ? <span className="text-sm font-bold text-slate-800 dark:text-slate-200">{s.grade}<span className="text-xs font-normal text-slate-400 dark:text-slate-500">/100</span></span>
                      : <span className="text-slate-300 dark:text-slate-600">—</span>}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link to="/instructor/grading" className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 px-3 py-1.5 rounded-lg transition-colors">
                      {s.status === "Pending Review" ? "Grade" : "View"}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Course Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        {[
          { code: "CS201", name: "Object Oriented Programming", students: 32, submissions: 28, pending: 4, color: "indigo" },
          { code: "CS301", name: "Algorithms", students: 25, submissions: 22, pending: 1, color: "blue" },
          { code: "CS150", name: "Introduction to Programming", students: 40, submissions: 38, pending: 0, color: "emerald" },
        ].map((c) => (
          <div key={c.code} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-5 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <span className={`text-xs font-bold px-2 py-1 rounded-md bg-${c.color}-50 dark:bg-${c.color}-900/30 text-${c.color}-600 dark:text-${c.color}-400`}>{c.code}</span>
              {c.pending > 0 && (
                <span className="text-xs font-semibold bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full">{c.pending} pending</span>
              )}
            </div>
            <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-3">{c.name}</p>
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400 dark:text-slate-500">Submissions</span>
                <span className="font-semibold text-slate-700 dark:text-slate-300">{c.submissions}/{c.students}</span>
              </div>
              <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full bg-${c.color}-500`}
                  style={{ width: `${Math.round((c.submissions / c.students) * 100)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
