import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { useAuth } from "../../../context/AuthContext";
import {
  getMyCourses,
  getCourseAssignments,
} from "../../../services/courseService";
import { getAssignmentSubmissions } from "../../../services/submissionService";

/* ── helpers ─────────────────────────────────────────────────────── */
const STATUS_CLS = {
  submitted:
    "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  processing:
    "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  graded:
    "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
  failed:
    "bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
};
const STATUS_DOT = {
  submitted: "bg-blue-500",
  processing: "bg-blue-500 animate-pulse",
  graded: "bg-indigo-500",
  failed: "bg-red-500",
};
const STATE_LABEL = {
  submitted: "Processing",
  processing: "Processing",
  graded: "AI Graded",
  failed: "Failed",
};

function StatusBadge({ state }) {
  const label = STATE_LABEL[state] ?? state;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_CLS[state] ?? "bg-slate-100 text-slate-500 border border-slate-200"}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[state] ?? "bg-slate-400"}`}
      />
      {label}
    </span>
  );
}

function StatCard({ title, value, subtitle, icon, iconBg, trend, trendUp }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-200 group">
      <div className="flex items-start justify-between mb-5">
        <div
          className={`w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-200`}
        >
          {icon}
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg ${trendUp ? "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30" : "text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/30"}`}
          >
            <svg
              className="w-3 h-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={
                  trendUp
                    ? "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    : "M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
                }
              />
            </svg>
            {trend}
          </div>
        )}
      </div>
      <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
        {title}
      </p>
      <p className="text-3xl font-extrabold text-slate-900 dark:text-white mb-1 tracking-tight">
        {value}
      </p>
      <p className="text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>
    </div>
  );
}

export default function InstructorHome() {
  const { user } = useAuth();
  const displayName = user?.username
    ? user.username.charAt(0).toUpperCase() + user.username.slice(1)
    : "Instructor";

  const [courses, setCourses] = useState([]);
  const [allSubs, setAllSubs] = useState([]); // flattened submissions with metadata
  const [recentSubs, setRecentSubs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        // 1. Fetch instructor's courses
        const coursesRes = await getMyCourses();
        const courses = coursesRes.data;

        // 2. For each course, fetch assignments (parallel)
        const assignmentsByCoursePairs = await Promise.all(
          courses.map((c) =>
            getCourseAssignments(c.id)
              .then((r) => r.data.map((a) => ({ ...a, course: c })))
              .catch(() => []),
          ),
        );
        const allAssignments = assignmentsByCoursePairs.flat();

        // 3. For each assignment, fetch submissions (parallel)
        const subsByAssignmentPairs = await Promise.all(
          allAssignments.map((a) =>
            getAssignmentSubmissions(a.id)
              .then((r) =>
                r.data.map((s) => ({ ...s, assignment: a, course: a.course })),
              )
              .catch(() => []),
          ),
        );
        const allSubmissions = subsByAssignmentPairs.flat();

        // Sort by submitted_at descending for recency
        allSubmissions.sort(
          (a, b) => new Date(b.submitted_at) - new Date(a.submitted_at),
        );

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
    return () => {
      cancelled = true;
    };
  }, []);

  const pending = allSubs.filter(
    (s) => s.state === "submitted" || s.state === "processing",
  ).length;
  const aiGraded = allSubs.filter((s) => s.state === "graded").length;

  return (
    <div className="space-y-8">
      {/* Welcome */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Welcome back, {displayName}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            Manage and grade your students' exam submissions
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <InstructorNavButton to="/instructor/courses" variant="primary">
            Courses
          </InstructorNavButton>
          <InstructorNavButton to="/instructor/submissions">
            Submissions
          </InstructorNavButton>
          <InstructorNavButton to="/instructor/grading">
            Grading
          </InstructorNavButton>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <Link
          to="/instructor/courses"
          className="block rounded-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <StatCard
            title="Courses"
            value={courses.length}
            subtitle="Manage courses & enrollments"
            iconBg="bg-blue-100 dark:bg-blue-900/30"
            icon={
              <svg
                className="w-6 h-6 text-blue-600 dark:text-blue-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            }
          />
        </Link>
        <StatCard
          title="Processing"
          value={loading ? "…" : pending}
          subtitle="Being graded by AI"
          iconBg="bg-amber-100 dark:bg-amber-900/30"
          icon={
            <svg
              className="w-6 h-6 text-amber-600 dark:text-amber-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
        <StatCard
          title="AI Graded"
          value={loading ? "…" : aiGraded}
          subtitle="Ready to review"
          iconBg="bg-indigo-100 dark:bg-indigo-900/30"
          icon={
            <svg
              className="w-6 h-6 text-indigo-600 dark:text-indigo-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636-6.364l.707.707M12 21v-1M6.343 17.657l-.707-.707M17.657 17.657l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z"
              />
            </svg>
          }
        />
        <StatCard
          title="Total Submissions"
          value={loading ? "…" : allSubs.length}
          subtitle="Across all courses"
          iconBg="bg-emerald-100 dark:bg-emerald-900/30"
          icon={
            <svg
              className="w-6 h-6 text-emerald-600 dark:text-emerald-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
        />
      </div>

      {/* Recent Submissions */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 dark:text-white">
            Recent Submissions
          </h2>
          <InstructorNavButton to="/instructor/submissions">
            View all
          </InstructorNavButton>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                {[
                  "Student ID",
                  "Assignment",
                  "Course",
                  "Submitted",
                  "Status",
                  "Action",
                ].map((h, i) => (
                  <th
                    key={h}
                    className={`text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider py-3 ${i === 5 ? "text-right px-6" : i === 0 ? "text-left px-6" : "text-left px-4"}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-slate-700/50">
              {loading ? (
                <tr>
                  <td
                    colSpan={6}
                    className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm"
                  >
                    Loading…
                  </td>
                </tr>
              ) : recentSubs.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm"
                  >
                    No submissions yet.
                  </td>
                </tr>
              ) : (
                recentSubs.map((s) => (
                  <tr
                    key={s.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono">
                        Student #{s.student_id}
                      </p>
                      <p className="text-xs text-slate-400 dark:text-slate-500">
                        Sub #{s.id}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm text-slate-700 dark:text-slate-300 font-medium max-w-[180px] truncate">
                        {s.assignment?.title ?? `#${s.assignment_id}`}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-1 rounded-md">
                        {s.course?.name ?? `Course #${s.assignment?.course_id}`}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {new Date(s.submitted_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </p>
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge state={s.state} />
                    </td>
                    <td className="px-6 py-4 text-right">
                      <InstructorNavButton
                        to="/instructor/grading"
                        variant="primary"
                      >
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

      {/* Course Overview */}
      {courses.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {courses.map((c) => {
            const courseSubs = allSubs.filter((s) => s.course?.id === c.id);
            return (
              <Link
                key={c.id}
                to={`/instructor/courses/${c.id}`}
                className="block bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-5 hover:shadow-md transition-shadow text-left focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="text-xs font-bold px-2 py-1 rounded-md bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">
                    #{c.id}
                  </span>
                  {courseSubs.filter(
                    (s) => s.state === "submitted" || s.state === "processing",
                  ).length > 0 && (
                    <span className="text-xs font-semibold bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full">
                      {
                        courseSubs.filter(
                          (s) =>
                            s.state === "submitted" || s.state === "processing",
                        ).length
                      }{" "}
                      processing
                    </span>
                  )}
                </div>
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-3">
                  {c.name}
                </p>
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400 dark:text-slate-500">
                      Total Submissions
                    </span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                      {courseSubs.length}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400 dark:text-slate-500">
                      AI Graded
                    </span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                      {courseSubs.filter((s) => s.state === "graded").length}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
