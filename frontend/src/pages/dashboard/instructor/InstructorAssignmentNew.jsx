import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { createAssignment } from "../../../services/courseService";

export default function InstructorAssignmentNew() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueLocal, setDueLocal] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(false);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError("");
    try {
      let dueIso = null;
      if (dueLocal) {
        const d = new Date(dueLocal);
        if (!Number.isNaN(d.getTime())) dueIso = d.toISOString();
      }
      const { data } = await createAssignment(
        id,
        title.trim(),
        description.trim() || undefined,
        dueIso,
        undefined,
      );
      navigate(`/instructor/courses/${id}/assignments/${data.id}/questions`, {
        replace: true,
      });
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not create assignment.");
    } finally {
      setSaving(false);
    }
  };

  if (!Number.isFinite(id)) {
    return <p className="text-red-600 text-sm">Invalid course.</p>;
  }

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          New assignment
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          You can add questions and tests after you save.
        </p>
      </div>

      <InstructorNavButton
        to={`/instructor/courses/${id}/assignments`}
        variant="primary"
      >
        ← Assignments
      </InstructorNavButton>

      {loading ? (
        <p className="text-slate-500 text-sm">Loading…</p>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm space-y-4"
        >
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
              Title
            </label>
            <input
              className="w-full rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              placeholder="Lab 1 — Loops"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
              Description (optional)
            </label>
            <textarea
              className="w-full rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 min-h-[88px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
              Due date (optional)
            </label>
            <input
              type="datetime-local"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
              value={dueLocal}
              onChange={(e) => setDueLocal(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold px-5 py-2.5 rounded-xl"
            >
              {saving ? "Saving…" : "Create and go to questions"}
            </button>
            <InstructorNavButton to={`/instructor/courses/${id}/assignments`}>
              Cancel
            </InstructorNavButton>
          </div>
        </form>
      )}
    </div>
  );
}
