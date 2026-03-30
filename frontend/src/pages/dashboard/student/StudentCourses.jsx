import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getMyCourses } from "../../../services/courseService";

function CourseCard({ course, onOpen }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-2">
            Course
          </p>
          <h3 className="text-lg font-extrabold text-slate-900 dark:text-white leading-tight truncate">
            {course.name}
          </h3>
          {course.description ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 whitespace-pre-wrap">
              {course.description}
            </p>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
              No description.
            </p>
          )}
        </div>
      </div>

      <div className="mt-4">
        <button
          type="button"
          onClick={() => onOpen(course.id)}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm transition-all active:scale-[0.98]"
        >
          View assignments
        </button>
      </div>
    </div>
  );
}

export default function StudentCourses() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setErrorMsg("");
        const res = await getMyCourses();
        if (!cancelled) setCourses(res.data ?? []);
      } catch (e) {
        console.error("StudentCourses load error:", e);
        if (!cancelled) setErrorMsg("Could not load courses.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return courses;
    return courses.filter((c) => c.name.toLowerCase().includes(q));
  }, [courses, query]);

  const openAssignments = (courseId) => {
    navigate(`/dashboard/assignments?course=${courseId}`);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Courses
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm max-w-2xl">
          Select a course to view its assignments and questions.
        </p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-4 sm:p-5">
        <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-2">
          Search
        </label>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by course name…"
          className="w-full px-3 py-2 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">
          Loading courses…
        </div>
      ) : errorMsg ? (
        <div className="rounded-2xl border border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-900/10 p-6 text-sm text-red-700 dark:text-red-400">
          {errorMsg}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-12 text-center">
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            {courses.length === 0
              ? "No courses found. Ask your instructor to enroll you."
              : "No courses match your search."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {filtered.map((course) => (
            <CourseCard
              key={course.id}
              course={course}
              onOpen={openAssignments}
            />
          ))}
        </div>
      )}
    </div>
  );
}
