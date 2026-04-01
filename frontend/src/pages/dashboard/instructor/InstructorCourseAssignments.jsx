import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import {
  getCourse,
  getCourseAssignments,
} from "../../../services/courseService";

export default function InstructorCourseAssignments() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const [course, setCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    let cancelled = false;
    (async () => {
      try {
        const [cRes, aRes] = await Promise.all([
          getCourse(id),
          getCourseAssignments(id),
        ]);
        if (cancelled) return;
        setCourse(cRes.data);
        setAssignments(aRes.data);
      } catch (e) {
        if (!cancelled) {
          setError(e.response?.data?.detail ?? "Could not load assignments.");
          setCourse(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (!Number.isFinite(id)) {
    return <p className="text-red-600 text-sm">Invalid course.</p>;
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">
      <div className="flex-1 min-w-0 space-y-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Assignments
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            {course?.name ? `Course: ${course.name}` : "Course"}
          </p>
        </header>

        <InstructorNavButton to={`/instructor/courses/${id}`} variant="primary">
          ← Course
        </InstructorNavButton>

        {error && (
          <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        )}

        {loading ? (
          <p className="text-slate-500 text-sm">Loading…</p>
        ) : (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden">
            {assignments.length === 0 ? (
              <p className="p-10 text-center text-slate-500 dark:text-slate-400 text-sm">
                No assignments yet. Use{" "}
                <strong className="font-medium text-slate-600 dark:text-slate-300">
                  + New assignment
                </strong>{" "}
                on the right.
              </p>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-slate-700">
                {assignments.map((a) => (
                  <li key={a.id}>
                    <Link
                      to={`/instructor/courses/${id}/assignments/${a.id}`}
                      className="block px-6 py-5 hover:bg-slate-50 dark:hover:bg-slate-700/35 transition-colors group"
                    >
                      <p className="text-lg font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                        {a.title}
                      </p>
                      {a.description && (
                        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1.5 leading-relaxed line-clamp-2">
                          {a.description}
                        </p>
                      )}
                      {a.due_date && (
                        <p className="text-xs text-slate-400 mt-2">
                          Due {new Date(a.due_date).toLocaleString()}
                        </p>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <aside className="lg:w-52 shrink-0 flex flex-col gap-3 lg:sticky lg:top-24">
        <InstructorNavButton
          to={`/instructor/courses/${id}/assignments/new`}
          className="lg:w-full"
        >
          + New assignment
        </InstructorNavButton>
      </aside>
    </div>
  );
}
