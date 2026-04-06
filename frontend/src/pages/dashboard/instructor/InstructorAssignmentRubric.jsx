import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";

const DEFAULT_CRITERIA = [
  { key: "correctness",  label: "Correctness",  weight: 40 },
  { key: "efficiency",   label: "Efficiency",   weight: 25 },
  { key: "edge_cases",   label: "Edge Cases",   weight: 20 },
  { key: "code_quality", label: "Code Quality", weight: 15 },
];

const STORAGE_KEY = (aid) => `jsg_rubric_assignment_${aid}`;

export default function InstructorAssignmentRubric() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);

  const [criteria, setCriteria] = useState(
    DEFAULT_CRITERIA.map((c) => ({ ...c }))
  );
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(aid)) return;
    const stored = localStorage.getItem(STORAGE_KEY(aid));
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed.criteria) && parsed.criteria.length > 0) {
        setCriteria(parsed.criteria);
      }
    } catch {
      // ignore
    }
  }, [aid]);

  const total = criteria.reduce((sum, c) => sum + c.weight, 0);

  const updateWeight = (key, val) => {
    const n = Math.min(100, Math.max(0, Number(val) || 0));
    setCriteria((prev) => prev.map((c) => (c.key === key ? { ...c, weight: n } : c)));
    setSaved(false);
  };

  const updateLabel = (key, val) => {
    setCriteria((prev) => prev.map((c) => (c.key === key ? { ...c, label: val } : c)));
    setSaved(false);
  };

  const addCriterion = () => {
    setCriteria((prev) => [
      ...prev,
      { key: `custom_${Date.now()}`, label: "", weight: 0 },
    ]);
    setSaved(false);
  };

  const removeCriterion = (key) => {
    if (criteria.length <= 1) return;
    setCriteria((prev) => prev.filter((c) => c.key !== key));
    setSaved(false);
  };

  const canSave = total === 100 && criteria.every((c) => c.label.trim() !== "");

  const handleSave = () => {
    if (!canSave) return;
    localStorage.setItem(STORAGE_KEY(aid), JSON.stringify({ criteria }));
    setSaved(true);
  };

  const totalColor =
    total === 100
      ? "text-emerald-500 dark:text-emerald-400"
      : total > 100
      ? "text-red-500 dark:text-red-400"
      : "text-amber-500 dark:text-amber-400";

  const barGradient =
    total === 100
      ? "from-emerald-500 to-teal-500"
      : total > 100
      ? "from-red-500 to-rose-500"
      : "from-amber-400 to-orange-400";

  if (!Number.isFinite(cid) || !Number.isFinite(aid)) {
    return <p className="text-red-600 text-sm">Invalid link.</p>;
  }

  return (
    <div className="max-w-2xl space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">Rubric</p>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Grading Rubric
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            Set the weight for each criterion. Total must equal 100%.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <InstructorNavButton to={`/instructor/courses/${cid}/assignments/${aid}`} variant="primary">
            ← Assignment
          </InstructorNavButton>
          <InstructorNavButton to={`/instructor/courses/${cid}/assignments/${aid}/questions`}>
            Questions
          </InstructorNavButton>
        </div>
      </div>

      {/* Criteria card */}
      <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl overflow-hidden">

        {/* Card header */}
        <div className="px-6 py-4 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between gap-3">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">Criteria</h2>
          <span className={`text-sm font-extrabold tabular-nums ${totalColor}`}>
            {total}% / 100%
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1.5 bg-slate-100 dark:bg-white/[0.05]">
          <div
            className={`h-full bg-gradient-to-r ${barGradient} transition-all duration-300`}
            style={{ width: `${Math.min(total, 100)}%` }}
          />
        </div>

        {/* Criteria rows */}
        <ul className="divide-y divide-slate-100 dark:divide-white/[0.05]">
          {criteria.map((c) => (
            <li key={c.key} className="px-6 py-4 flex items-center gap-4 group/row">
              <input
                type="text"
                value={c.label}
                onChange={(e) => updateLabel(c.key, e.target.value)}
                placeholder="Criterion name"
                className="flex-1 min-w-0 bg-transparent text-sm font-semibold text-slate-900 dark:text-slate-100 placeholder-slate-400 border-b border-transparent hover:border-slate-300 dark:hover:border-white/[0.15] focus:border-indigo-500 dark:focus:border-indigo-400 focus:outline-none transition-colors py-0.5"
              />
              <input
                type="range"
                min={0}
                max={100}
                value={c.weight}
                onChange={(e) => updateWeight(c.key, e.target.value)}
                className="w-28 accent-indigo-500 shrink-0"
              />
              <div className="flex items-center gap-1 shrink-0">
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={c.weight}
                  onChange={(e) => updateWeight(c.key, e.target.value)}
                  className="w-14 rounded-lg border border-slate-200 dark:border-white/[0.1] bg-white dark:bg-white/[0.05] px-2 py-1 text-xs text-center font-bold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <span className="text-xs text-slate-400">%</span>
              </div>
              <button
                type="button"
                onClick={() => removeCriterion(c.key)}
                disabled={criteria.length <= 1}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 disabled:opacity-20 disabled:cursor-not-allowed transition-colors shrink-0"
                title="Remove criterion"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </li>
          ))}
        </ul>

        {/* Footer actions */}
        <div className="px-6 py-4 border-t border-slate-100 dark:border-white/[0.06] bg-slate-50 dark:bg-white/[0.02] flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={addCriterion}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-white/[0.1] text-slate-700 dark:text-slate-200 bg-white dark:bg-white/[0.05] hover:bg-slate-50 dark:hover:bg-white/[0.08] transition-colors"
          >
            + Add criterion
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            className="text-xs font-bold px-4 py-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-600 hover:to-violet-600 text-white shadow-sm disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            Save rubric
          </button>
          {saved && (
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Saved
            </span>
          )}
          {!canSave && total !== 100 && (
            <span className="text-xs text-slate-400">Weights must sum to 100%</span>
          )}
          {!canSave && total === 100 && (
            <span className="text-xs text-slate-400">Fill in all criterion names</span>
          )}
        </div>
      </div>
    </div>
  );
}
