import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { getCourse, getCourseAssignments } from "../../../services/courseService";

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
        const [cRes, aRes] = await Promise.all([getCourse(id), getCourseAssignments(id)]);
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
    return () => { cancelled = true; };
  }, [id]);

  if (!Number.isFinite(id)) {
    return <p className="text-red-600 text-sm">Invalid course.</p>;
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">
      <div className="flex-1 min-w-0 space-y-6">

        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">
              {course?.name ?? "Course"}
            </p>
            <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Assignments
            </h1>
          </div>
          <InstructorNavButton to={`/instructor/courses/${id}`} variant="primary">
            ← Course
          </InstructorNavButton>
        </div>

        {error && <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>}

        {loading ? (
          <p className="text-slate-500 text-sm">Loading…</p>
        ) : (
          <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl overflow-hidden">
            {assignments.length === 0 ? (
              <div className="py-16 flex flex-col items-center gap-3">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg">
                  <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </div>
                <p className="text-sm font-bold text-slate-900 dark:text-white">No assignments yet</p>
                <p className="text-xs text-slate-400">Use <strong className="text-slate-500 dark:text-slate-300">+ New assignment</strong> to get started.</p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100 dark:divide-white/[0.05]">
                {assignments.map((a, idx) => {
                  const accents = [
                    "from-blue-500 to-cyan-500",
                    "from-indigo-500 to-violet-500",
                    "from-emerald-500 to-teal-500",
                    "from-amber-500 to-orange-500",
                  ];
                  const accent = accents[idx % accents.length];
                  return (
                    <li key={a.id}>
                      <Link
                        to={`/instructor/courses/${id}/assignments/${a.id}`}
                        className="flex items-center gap-4 px-6 py-5 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors group"
                      >
                        <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${accent} flex items-center justify-center shrink-0 shadow-sm group-hover:scale-110 transition-transform duration-200`}>
                          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">
                            {a.title}
                          </p>
                          {a.description && (
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                              {a.description}
                            </p>
                          )}
                        </div>
                        {a.due_date && (
                          <span className="text-xs text-slate-400 shrink-0">
                            Due {new Date(a.due_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                          </span>
                        )}
                        <svg className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>

      <aside className="lg:w-52 shrink-0 flex flex-col gap-3 lg:sticky lg:top-24">
        <InstructorNavButton to={`/instructor/courses/${id}/assignments/new`} className="lg:w-full">
          + New assignment
        </InstructorNavButton>
      </aside>
    </div>
  );
}
