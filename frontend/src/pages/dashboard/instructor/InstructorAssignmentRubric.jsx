import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";

const BASE_RUBRICS = [
  { key: "correctness", label: "Correctness", weight: 40 },
  { key: "efficiency", label: "Efficiency", weight: 25 },
  { key: "edge_cases", label: "Edge Cases", weight: 20 },
  { key: "code_quality", label: "Code Quality", weight: 15 },
];

const STORAGE_KEY = (aid) => `jsg_rubric_assignment_${aid}`;

export default function InstructorAssignmentRubric() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);

  const [rubrics, setRubrics] = useState(
    BASE_RUBRICS.map((r) => ({ ...r, fixed: true }))
  );
  const [custom, setCustom] = useState([]);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!Number.isFinite(aid)) return;
    const stored = localStorage.getItem(STORAGE_KEY(aid));
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored);
      if (parsed.rubrics) setRubrics(parsed.rubrics);
      if (parsed.custom) setCustom(parsed.custom);
    } catch {
      // ignore
    }
  }, [aid]);

  const total = [
    ...rubrics.map((r) => r.weight),
    ...custom.map((c) => c.weight),
  ].reduce((a, b) => a + b, 0);

  const updateWeight = (key, val) => {
    const n = Math.min(100, Math.max(0, Number(val) || 0));
    setRubrics((prev) =>
      prev.map((r) => (r.key === key ? { ...r, weight: n } : r))
    );
    setSaved(false);
  };

  const updateCustomWeight = (i, val) => {
    const n = Math.min(100, Math.max(0, Number(val) || 0));
    setCustom((prev) => prev.map((c, idx) => (idx === i ? { ...c, weight: n } : c)));
    setSaved(false);
  };

  const updateCustomLabel = (i, val) => {
    setCustom((prev) => prev.map((c, idx) => (idx === i ? { ...c, label: val } : c)));
    setSaved(false);
  };

  const addCustom = () => {
    if (custom.length >= 2) return;
    setCustom((prev) => [...prev, { key: `custom_${Date.now()}`, label: "", weight: 0 }]);
    setSaved(false);
  };

  const removeCustom = (i) => {
    setCustom((prev) => prev.filter((_, idx) => idx !== i));
    setSaved(false);
  };

  const canSave =
    total === 100 && custom.every((c) => c.label.trim() !== "");

  const handleSave = () => {
    if (!canSave) return;
    setError("");
    localStorage.setItem(STORAGE_KEY(aid), JSON.stringify({ rubrics, custom }));
    setSaved(true);
  };

  const totalColor =
    total === 100
      ? "text-emerald-600 dark:text-emerald-400"
      : total > 100
      ? "text-red-600 dark:text-red-400"
      : "text-amber-600 dark:text-amber-400";

  const barColor =
    total === 100
      ? "bg-emerald-500"
      : total > 100
      ? "bg-red-500"
      : "bg-amber-400";

  if (!Number.isFinite(cid) || !Number.isFinite(aid)) {
    return <p className="text-red-600 text-sm">Invalid link.</p>;
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Grading Rubric
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          Set the weight for each criterion. Total must equal 100%.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <InstructorNavButton
          to={`/instructor/courses/${cid}/assignments/${aid}`}
          variant="primary"
        >
          ← Assignment
        </InstructorNavButton>
        <InstructorNavButton
          to={`/instructor/courses/${cid}/assignments/${aid}/questions`}
        >
          Questions
        </InstructorNavButton>
      </div>

      <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between gap-3">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">
            Criteria
          </h2>
          <span className={`text-sm font-bold tabular-nums ${totalColor}`}>
            {total}% / 100%
          </span>
        </div>

        <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-700">
          <div
            className={`h-full transition-all ${barColor}`}
            style={{ width: `${Math.min(total, 100)}%` }}
          />
        </div>

        <ul className="divide-y divide-slate-100 dark:divide-slate-700">
          {rubrics.map((r) => (
            <li key={r.key} className="px-5 py-4 flex items-center gap-4">
              <span className="flex-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                {r.label}
                <span className="ml-2 text-[11px] text-slate-400 font-normal">
                  base
                </span>
              </span>
              <input
                type="range"
                min={0}
                max={100}
                value={r.weight}
                onChange={(e) => updateWeight(r.key, e.target.value)}
                className="w-32 accent-indigo-600"
              />
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={r.weight}
                  onChange={(e) => updateWeight(r.key, e.target.value)}
                  className="w-14 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1 text-xs text-center text-slate-900 dark:text-white"
                />
                <span className="text-xs text-slate-400">%</span>
              </div>
            </li>
          ))}

          {custom.map((c, i) => (
            <li key={c.key} className="px-5 py-4 flex items-center gap-4">
              <input
                className="flex-1 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1 text-sm text-slate-900 dark:text-white"
                value={c.label}
                onChange={(e) => updateCustomLabel(i, e.target.value)}
                placeholder="Custom criterion name"
              />
              <input
                type="range"
                min={0}
                max={100}
                value={c.weight}
                onChange={(e) => updateCustomWeight(i, e.target.value)}
                className="w-32 accent-indigo-600"
              />
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={c.weight}
                  onChange={(e) => updateCustomWeight(i, e.target.value)}
                  className="w-14 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1 text-xs text-center text-slate-900 dark:text-white"
                />
                <span className="text-xs text-slate-400">%</span>
              </div>
              <button
                type="button"
                onClick={() => removeCustom(i)}
                className="text-xs text-red-500 hover:text-red-700 dark:text-red-400 shrink-0"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>

        <div className="px-5 py-4 border-t border-slate-100 dark:border-slate-700 flex flex-wrap items-center gap-3">
          {custom.length < 2 && (
            <button
              type="button"
              onClick={addCustom}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/80 transition-colors"
            >
              + Add custom criterion
            </button>
          )}
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            className="text-xs font-semibold px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Save rubric
          </button>
          {saved && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400">
              Saved
            </span>
          )}
          {error && (
            <span className="text-xs text-red-600 dark:text-red-400">
              {error}
            </span>
          )}
          {!canSave && total !== 100 && (
            <span className="text-xs text-slate-400">
              Adjust weights so total equals 100%
            </span>
          )}
          {!canSave && total === 100 && (
            <span className="text-xs text-slate-400">
              Fill in all custom criterion names
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
