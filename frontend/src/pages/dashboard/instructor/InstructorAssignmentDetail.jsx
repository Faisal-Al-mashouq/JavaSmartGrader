import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import RubricEditor from "../../../components/RubricEditor";
import {
  getAssignment,
  updateAssignmentRubric,
} from "../../../services/courseService";

export default function InstructorAssignmentDetail() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Rubric editing state
  const [rubricOpen, setRubricOpen] = useState(false);
  const [editedRubric, setEditedRubric] = useState(null);
  const [rubricSaving, setRubricSaving] = useState(false);
  const [rubricError, setRubricError] = useState("");
  const [rubricSaved, setRubricSaved] = useState(false);

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
        setEditedRubric(aRes.data.rubric_json);
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

  const totalWeight = Object.values(editedRubric?.criteria ?? {}).reduce(
    (s, c) => s + (c.weight ?? 0),
    0
  );
  const rubricValid = Math.abs(totalWeight - 100) < 0.01;

  const handleSaveRubric = async () => {
    if (!rubricValid) {
      setRubricError("Weights must sum to 100%.");
      return;
    }
    setRubricSaving(true);
    setRubricError("");
    setRubricSaved(false);
    try {
      const { data } = await updateAssignmentRubric(aid, editedRubric);
      setAssignment(data);
      setEditedRubric(data.rubric_json);
      setRubricSaved(true);
      setTimeout(() => setRubricSaved(false), 3000);
    } catch (e) {
      setRubricError(e.response?.data?.detail ?? "Could not save rubric.");
    } finally {
      setRubricSaving(false);
    }
  };

  const handleCancelRubric = () => {
    setEditedRubric(assignment.rubric_json);
    setRubricError("");
    setRubricOpen(false);
  };

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

            {/* Rubric section */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden">
              <button
                type="button"
                onClick={() => setRubricOpen((o) => !o)}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">
                    Grading Rubric
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {Object.keys(assignment.rubric_json?.criteria ?? {}).length} criteria
                    &nbsp;·&nbsp; weights sum to{" "}
                    {Object.values(assignment.rubric_json?.criteria ?? {})
                      .reduce((s, c) => s + (c.weight ?? 0), 0)
                      .toFixed(0)}
                    %
                  </p>
                </div>
                <span className="text-slate-400 text-sm">{rubricOpen ? "▲" : "▼"}</span>
              </button>

              {rubricOpen && (
                <div className="px-6 pb-6 space-y-4 border-t border-slate-100 dark:border-slate-700 pt-4">
                  {rubricError && (
                    <p className="text-sm text-red-600 dark:text-red-400">{rubricError}</p>
                  )}
                  {rubricSaved && (
                    <p className="text-sm text-emerald-600 dark:text-emerald-400">
                      Rubric saved successfully.
                    </p>
                  )}

                  <RubricEditor
                    rubric={editedRubric}
                    onChange={setEditedRubric}
                    readOnly={false}
                  />

                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={handleSaveRubric}
                      disabled={rubricSaving || !rubricValid}
                      className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold px-5 py-2 rounded-xl"
                    >
                      {rubricSaving ? "Saving…" : "Save Rubric"}
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelRubric}
                      className="bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-sm font-semibold px-5 py-2 rounded-xl"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
