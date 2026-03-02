import { useState } from "react";
import { useAuth } from "../../../context/AuthContext";

const ASSIGNMENTS = [
  { id: 1, name: "Midterm Exam - OOP Concepts", course: "CS201", courseFull: "Object Oriented Programming", dueDate: "Dec 1, 2024", status: "Published", grade: 87, maxGrade: 100, action: "View" },
  { id: 2, name: "Lab Assignment 3 - Inheritance", course: "CS201", courseFull: "Object Oriented Programming", dueDate: "Dec 5, 2024", status: "Pending Review", grade: null, maxGrade: 100, action: "View" },
  { id: 3, name: "Quiz 2 - Exception Handling", course: "CS201", courseFull: "Object Oriented Programming", dueDate: "Dec 8, 2024", status: "Processing", grade: null, maxGrade: 50, action: "View" },
  { id: 4, name: "Final Project - Banking System", course: "CS201", courseFull: "Object Oriented Programming", dueDate: "Dec 15, 2024", status: "Pending", grade: null, maxGrade: 100, action: "Submit" },
  { id: 5, name: "Assignment 2 - Data Structures", course: "CS301", courseFull: "Algorithms", dueDate: "Dec 10, 2024", status: "Published", grade: 92, maxGrade: 100, action: "View" },
  { id: 6, name: "Practical Exam 1", course: "CS150", courseFull: "Introduction to Programming", dueDate: "Nov 28, 2024", status: "Published", grade: 78, maxGrade: 100, action: "View" },
];

const STATUS_LIGHT = {
  Published:      "bg-emerald-50 text-emerald-700 border border-emerald-200",
  "Pending Review":"bg-amber-50 text-amber-700 border border-amber-200",
  Processing:     "bg-blue-50 text-blue-700 border border-blue-200",
  Pending:        "bg-slate-100 text-slate-500 border border-slate-200",
};
const STATUS_DARK = {
  Published:      "dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800",
  "Pending Review":"dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  Processing:     "dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  Pending:        "dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600",
};
const STATUS_DOT = {
  Published: "bg-emerald-500", "Pending Review": "bg-amber-500",
  Processing: "bg-blue-500",  Pending: "bg-slate-400",
};

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_LIGHT[status] || STATUS_LIGHT.Pending} ${STATUS_DARK[status] || STATUS_DARK.Pending}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status]}`} />
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

function StatCard({ title, value, subtitle, icon, iconBg, trend }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-200 group">
      <div className="flex items-start justify-between mb-5">
        <div className={`w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-200`}>
          {icon}
        </div>
        {trend && (
          <div className="flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-1 rounded-lg">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
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

const COURSES  = ["All Courses", "CS201 - Object Oriented Programming", "CS301 - Algorithms", "CS150 - Introduction to Programming"];
const STATUSES = ["All Statuses", "Published", "Pending Review", "Processing", "Pending"];
const SEMESTERS = ["Current Semester", "Spring 2024", "Fall 2023"];

const selectCls = "text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm";

export default function StudentHome() {
  const { user } = useAuth();
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Student";

  const [courseFilter,    setCourseFilter]    = useState("All Courses");
  const [statusFilter,    setStatusFilter]    = useState("All Statuses");
  const [semesterFilter,  setSemesterFilter]  = useState("Current Semester");

  const graded   = ASSIGNMENTS.filter((a) => a.grade !== null);
  const avgGrade = graded.length > 0
    ? (graded.reduce((s, a) => s + Math.round((a.grade / a.maxGrade) * 100), 0) / graded.length).toFixed(1)
    : "—";

  const upcoming  = ASSIGNMENTS.filter((a) => a.status === "Pending").length;
  const submitted = ASSIGNMENTS.filter((a) => a.status !== "Pending").length;

  const filtered = ASSIGNMENTS.filter((a) => {
    const matchCourse  = courseFilter  === "All Courses"  || a.courseFull === courseFilter.split(" - ")[1];
    const matchStatus  = statusFilter  === "All Statuses" || a.status === statusFilter;
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
        <button className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-sm font-semibold px-4 py-2.5 rounded-xl shadow-sm transition-all duration-150">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Submit Exam
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <StatCard title="Upcoming Exams" value={upcoming} subtitle="Not yet submitted" iconBg="bg-orange-100 dark:bg-orange-900/30"
          icon={<svg className="w-6 h-6 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard title="Submitted Exams" value={submitted} subtitle="Awaiting results" iconBg="bg-blue-100 dark:bg-blue-900/30"
          icon={<svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
        />
        <StatCard title="Average Grade" value={avgGrade !== "—" ? `${avgGrade}%` : "—"}
          subtitle={`From ${graded.length} graded exam${graded.length !== 1 ? "s" : ""}`}
          iconBg="bg-emerald-100 dark:bg-emerald-900/30" trend={avgGrade !== "—" ? "+2.4%" : undefined}
          icon={<svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
        />
      </div>

      {/* Assignments Section */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">

        {/* Section Header */}
        <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">All Assignments</h2>
        </div>

        {/* Filters */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-100 dark:border-slate-700 flex flex-wrap gap-4">
          <div className="flex flex-col gap-1 min-w-[180px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Course</label>
            <select value={courseFilter} onChange={(e) => setCourseFilter(e.target.value)} className={selectCls}>
              {COURSES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Status</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className={selectCls}>
              {STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1 min-w-[160px]">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Semester</label>
            <select value={semesterFilter} onChange={(e) => setSemesterFilter(e.target.value)} className={selectCls}>
              {SEMESTERS.map((s) => <option key={s}>{s}</option>)}
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
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">
                    No assignments match your filters.
                  </td>
                </tr>
              ) : filtered.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors duration-100 group">
                  <td className="px-6 py-4">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{a.name}</p>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded-md">{a.course}</span>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{a.courseFull}</p>
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
                    {a.action === "Submit"
                      ? <button className="text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg transition-colors active:scale-95">Submit</button>
                      : <button className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 px-3 py-1.5 rounded-lg transition-colors">View</button>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between flex-wrap gap-2">
          <p className="text-xs text-slate-400 dark:text-slate-500">Showing {filtered.length} of {ASSIGNMENTS.length} assignments</p>
          <div className="flex items-center gap-2 flex-wrap">
            {Object.keys(STATUS_LIGHT).map((s) => (
              <span key={s} className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${STATUS_LIGHT[s]} ${STATUS_DARK[s]}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[s]}`} />
                {s}
              </span>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
