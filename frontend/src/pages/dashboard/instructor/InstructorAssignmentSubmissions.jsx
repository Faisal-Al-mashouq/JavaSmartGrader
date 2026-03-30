import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { getAssignment } from "../../../services/courseService";
import { getAssignmentSubmissions } from "../../../services/submissionService";

const STATE_LABEL = {
  submitted: "Processing",
  processing: "Processing",
  graded: "AI Graded",
  failed: "Failed",
};

function StatusBadge({ state }) {
  const label = STATE_LABEL[state] ?? state;
  const cls =
    state === "graded"
      ? "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800"
      : state === "failed"
        ? "bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800"
        : "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800";
  return (
    <span
      className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}
    >
      {label}
    </span>
  );
}

export default function InstructorAssignmentSubmissions() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);
  const [assignment, setAssignment] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!Number.isFinite(cid) || !Number.isFinite(aid)) return;
    let cancelled = false;
    (async () => {
      try {
        const [aRes, sRes] = await Promise.all([
          getAssignment(aid),
          getAssignmentSubmissions(aid),
        ]);
        if (cancelled) return;
        if (aRes.data.course_id !== cid) {
          setError("Assignment does not match this course.");
          return;
        }
        setAssignment(aRes.data);
        const list = sRes.data.sort(
          (a, b) => new Date(b.submitted_at) - new Date(a.submitted_at),
        );
        setRows(list);
      } catch (e) {
        if (!cancelled)
          setError(e.response?.data?.detail ?? "Could not load submissions.");
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
      <div className="flex-1 min-w-0 space-y-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Submissions
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            {assignment?.title
              ? `Student work for “${assignment.title}”.`
              : "Student work for this assignment."}
          </p>
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <InstructorNavButton
            to={`/instructor/courses/${cid}/assignments/${aid}`}
            variant="primary"
          >
            ← Assignments
          </InstructorNavButton>
        </div>

        {error && (
          <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        )}

        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700">
                  {["Student", "Submitted", "Status", ""].map((h, i) => (
                    <th
                      key={h || `col-${i}`}
                      className={`text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider py-3 px-6 ${
                        i === 3 ? "text-right" : "text-left"
                      }`}
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
                      colSpan={4}
                      className="text-center py-12 text-slate-400 text-sm"
                    >
                      Loading…
                    </td>
                  </tr>
                ) : rows.length === 0 ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="text-center py-12 text-slate-400 text-sm"
                    >
                      No submissions for this assignment yet.
                    </td>
                  </tr>
                ) : (
                  rows.map((s) => (
                    <tr
                      key={s.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-700/40"
                    >
                      <td className="px-6 py-4">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 font-mono">
                          #{s.student_id}
                        </p>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400 whitespace-nowrap">
                        {new Date(s.submitted_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge state={s.state} />
                      </td>
                      <td className="px-6 py-4 text-right">
                        <InstructorNavButton
                          to="/instructor/grading"
                          variant="primary"
                        >
                          Grading
                        </InstructorNavButton>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <aside className="lg:w-52 shrink-0 lg:sticky lg:top-24">
        <InstructorNavButton
          to="/instructor/grading"
          className="lg:w-full"
          variant="primary"
        >
          Grading workspace
        </InstructorNavButton>
      </aside>
    </div>
  );
}
