import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { getAssignment } from "../../../services/courseService";

export default function InstructorAssignmentDetail() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!Number.isFinite(cid) || !Number.isFinite(aid)) return;
    let cancelled = false;
    (async () => {
      try {
        const aRes = await getAssignment(aid);
        if (cancelled) return;
        if (aRes.data.course_id !== cid) {
          setError("This assignment does not belong to the selected course.");
          return;
        }
        setAssignment(aRes.data);
      } catch (e) {
        if (!cancelled)
          setError(e.response?.data?.detail ?? "Could not load assignment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cid, aid]);

  if (!Number.isFinite(cid) || !Number.isFinite(aid)) {
    return <p className="text-red-600 text-sm">Invalid link.</p>;
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">
      <div className="flex-1 min-w-0 space-y-6">
        {loading ? (
          <p className="text-slate-500 text-sm">Loading…</p>
        ) : error ? (
          <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        ) : assignment ? (
          <>
            <header className="space-y-2">
              <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                {assignment.title}
              </h1>
              {assignment.description ? (
                <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed max-w-3xl">
                  {assignment.description}
                </p>
              ) : null}
              {assignment.due_date && (
                <p className="text-xs text-slate-500">
                  Due {new Date(assignment.due_date).toLocaleString()}
                </p>
              )}
            </header>

            <InstructorNavButton
              to={`/instructor/courses/${cid}/assignments`}
              variant="primary"
            >
              ← Assignments
            </InstructorNavButton>

            <div className="grid sm:grid-cols-2 gap-4">
              <Link
                to={`/instructor/courses/${cid}/assignments/${aid}/rubric`}
                className="block rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors group text-left"
              >
                <h2 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                  Grading Rubric
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                  Configure criteria weights for Correctness, Efficiency, Edge Cases, and Code Quality.
                </p>
              </Link>
              <Link
                to={`/instructor/courses/${cid}/assignments/${aid}/submissions`}
                className="block rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors group text-left"
              >
                <h2 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                  Submissions
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                  Everything students have handed in for this assignment.
                </p>
              </Link>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
