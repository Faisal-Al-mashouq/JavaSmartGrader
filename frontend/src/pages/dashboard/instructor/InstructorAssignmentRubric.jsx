import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";

/* ─── constants ─────────────────────────────────────────────── */

const BASE_RUBRICS = [
  {
    id: "correctness",
    name: "Correctness",
    description: "Does the solution produce the expected outputs?",
    weight: 40,
  },
  {
    id: "efficiency",
    name: "Efficiency",
    description: "Time and space complexity; avoids unnecessary operations.",
    weight: 25,
  },
  {
    id: "edge_cases",
    name: "Edge Cases",
    description: "Handles boundary conditions, empty inputs, and exceptions.",
    weight: 20,
  },
  {
    id: "code_quality",
    name: "Code Quality",
    description: "Readability, naming, structure, and style.",
    weight: 15,
  },
];

const MAX_EXTRA = 2;
const STORAGE_KEY = (aid) => `jsg_rubric_assignment_${aid}`;

/* ─── helpers ───────────────────────────────────────────────── */

function clamp(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.min(100, Math.max(0, Math.round(n)));
}

function newExtra() {
  return { id: `extra_${Date.now()}`, name: "", description: "", weight: 0, isExtra: true };
}

/* ─── sub-components ─────────────────────────────────────────── */

function WeightSlider({ value, onChange, disabled }) {
  return (
    <input
      type="range"
      min={0}
      max={100}
      step={1}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full h-1.5 rounded-full accent-indigo-600 cursor-pointer disabled:cursor-not-allowed"
    />
  );
}

function RubricCard({ rubric, onWeightChange, onNameChange, onDescChange, onRemove, total, isBase }) {
  const over = total > 100;

  return (
    <div
      className={`rounded-2xl border bg-white dark:bg-slate-800 p-5 shadow-sm space-y-4 transition-colors
        ${isBase
          ? "border-indigo-100 dark:border-indigo-900/60"
          : "border-amber-100 dark:border-amber-900/40"
        }`}
    >
      {/* header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0 space-y-1">
          {isBase ? (
            <>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-800">
                  Base
                </span>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  {rubric.name}
                </h3>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                {rubric.description}
              </p>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-100 dark:border-amber-800">
                  Custom
                </span>
                <input
                  type="text"
                  value={rubric.name}
                  onChange={(e) => onNameChange(e.target.value)}
                  placeholder="Rubric name"
                  maxLength={40}
                  className="flex-1 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2.5 py-1 text-sm font-semibold text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-amber-400 focus:border-transparent outline-none"
                />
              </div>
              <input
                type="text"
                value={rubric.description}
                onChange={(e) => onDescChange(e.target.value)}
                placeholder="Short description (optional)"
                maxLength={120}
                className="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2.5 py-1.5 text-xs text-slate-700 dark:text-slate-300 placeholder-slate-400 focus:ring-2 focus:ring-amber-400 focus:border-transparent outline-none"
              />
            </>
          )}
        </div>

        {!isBase && (
          <button
            type="button"
            onClick={onRemove}
            title="Remove rubric"
            className="mt-0.5 shrink-0 rounded-lg p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        )}
      </div>

      {/* weight controls */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 w-14 shrink-0">
            Weight
          </label>
          <div className="flex-1">
            <WeightSlider value={rubric.weight} onChange={onWeightChange} />
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <input
              type="number"
              min={0}
              max={100}
              step={1}
              value={rubric.weight}
              onChange={(e) => onWeightChange(clamp(e.target.value))}
              className={`w-16 rounded-lg border px-2 py-1 text-sm font-bold text-center outline-none focus:ring-2
                ${over
                  ? "border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 focus:ring-red-400"
                  : "border-slate-200 dark:border-slate-600 text-slate-900 dark:text-white focus:ring-indigo-500"
                }
                bg-white dark:bg-slate-900`}
            />
            <span className="text-xs text-slate-500 dark:text-slate-400">%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── main component ─────────────────────────────────────────── */

export default function InstructorAssignmentRubric() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);

  const [baseRubrics, setBaseRubrics] = useState(
    BASE_RUBRICS.map((r) => ({ ...r }))
  );
  const [extraRubrics, setExtraRubrics] = useState([]);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState("");

  /* load persisted rubric */
  useEffect(() => {
    if (!Number.isFinite(aid)) return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY(aid));
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed.base) setBaseRubrics(parsed.base);
      if (parsed.extra) setExtraRubrics(parsed.extra);
    } catch {
      /* ignore corrupt data */
    }
  }, [aid]);

  const total = [...baseRubrics, ...extraRubrics].reduce(
    (sum, r) => sum + (r.weight || 0),
    0
  );

  const remaining = 100 - total;
  const isValid =
    total === 100 &&
    extraRubrics.every((r) => r.name.trim().length > 0);

  /* base weight change */
  const setBaseWeight = useCallback((id, val) => {
    setSaved(false);
    setBaseRubrics((prev) =>
      prev.map((r) => (r.id === id ? { ...r, weight: clamp(val) } : r))
    );
  }, []);

  /* extra CRUD */
  const setExtraWeight = useCallback((id, val) => {
    setSaved(false);
    setExtraRubrics((prev) =>
      prev.map((r) => (r.id === id ? { ...r, weight: clamp(val) } : r))
    );
  }, []);

  const setExtraName = useCallback((id, val) => {
    setSaved(false);
    setExtraRubrics((prev) =>
      prev.map((r) => (r.id === id ? { ...r, name: val } : r))
    );
  }, []);

  const setExtraDesc = useCallback((id, val) => {
    setSaved(false);
    setExtraRubrics((prev) =>
      prev.map((r) => (r.id === id ? { ...r, description: val } : r))
    );
  }, []);

  const addExtra = () => {
    if (extraRubrics.length >= MAX_EXTRA) return;
    setSaved(false);
    setExtraRubrics((prev) => [...prev, newExtra()]);
  };

  const removeExtra = (id) => {
    setSaved(false);
    setExtraRubrics((prev) => prev.filter((r) => r.id !== id));
  };

  /* save */
  const handleSave = () => {
    setSaveError("");
    if (!isValid) {
      if (total !== 100)
        setSaveError(`Weights must add up to 100. Currently at ${total}.`);
      else setSaveError("All custom rubrics must have a name.");
      return;
    }
    try {
      localStorage.setItem(
        STORAGE_KEY(aid),
        JSON.stringify({ base: baseRubrics, extra: extraRubrics })
      );
      setSaved(true);
    } catch {
      setSaveError("Could not save. Please try again.");
    }
  };

  /* reset to defaults */
  const handleReset = () => {
    setBaseRubrics(BASE_RUBRICS.map((r) => ({ ...r })));
    setExtraRubrics([]);
    setSaved(false);
    setSaveError("");
  };

  if (!Number.isFinite(cid) || !Number.isFinite(aid)) {
    return <p className="text-red-600 text-sm">Invalid link.</p>;
  }

  /* colour coding for the total badge */
  const totalColour =
    total === 100
      ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
      : total > 100
      ? "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800"
      : "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800";

  return (
    <div className="max-w-2xl space-y-6">

      {/* page header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Grading Rubric
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
          Set the weight for each criterion. Weights must total exactly 100%.
        </p>
      </div>

      <InstructorNavButton
        to={`/instructor/courses/${cid}/assignments/${aid}`}
        variant="primary"
      >
        ← Assignment
      </InstructorNavButton>

      {/* total indicator */}
      <div className="flex items-center gap-3">
        <div
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border font-semibold text-sm ${totalColour}`}
        >
          <span>Total:</span>
          <span className="text-lg font-extrabold">{total}%</span>
          {total !== 100 && (
            <span className="text-xs font-normal opacity-80">
              ({remaining > 0 ? `${remaining} remaining` : `${-remaining} over`})
            </span>
          )}
          {total === 100 && (
            <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>

        {/* progress bar */}
        <div className="flex-1 h-2.5 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300
              ${total > 100 ? "bg-red-500" : total === 100 ? "bg-emerald-500" : "bg-indigo-500"}`}
            style={{ width: `${Math.min(total, 100)}%` }}
          />
        </div>
      </div>

      {/* base rubrics */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
          Base Criteria
        </h2>
        {baseRubrics.map((r) => (
          <RubricCard
            key={r.id}
            rubric={r}
            isBase
            total={total}
            onWeightChange={(v) => setBaseWeight(r.id, v)}
          />
        ))}
      </section>

      {/* extra rubrics */}
      {extraRubrics.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
            Custom Criteria
          </h2>
          {extraRubrics.map((r) => (
            <RubricCard
              key={r.id}
              rubric={r}
              isBase={false}
              total={total}
              onWeightChange={(v) => setExtraWeight(r.id, v)}
              onNameChange={(v) => setExtraName(r.id, v)}
              onDescChange={(v) => setExtraDesc(r.id, v)}
              onRemove={() => removeExtra(r.id)}
            />
          ))}
        </section>
      )}

      {/* add extra rubric */}
      {extraRubrics.length < MAX_EXTRA && (
        <button
          type="button"
          onClick={addExtra}
          className="w-full rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-700 py-4 text-sm font-semibold text-slate-500 dark:text-slate-400 hover:border-indigo-300 dark:hover:border-indigo-700 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
          </svg>
          Add custom rubric
          <span className="text-xs font-normal opacity-60">
            ({MAX_EXTRA - extraRubrics.length} remaining)
          </span>
        </button>
      )}

      {/* errors / success */}
      {saveError && (
        <p className="text-sm text-red-600 dark:text-red-400">{saveError}</p>
      )}
      {saved && (
        <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 font-semibold">
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
              clipRule="evenodd"
            />
          </svg>
          Rubric saved successfully.
        </div>
      )}

      {/* action buttons */}
      <div className="flex flex-wrap gap-3 pt-1 pb-8">
        <button
          type="button"
          onClick={handleSave}
          disabled={!isValid}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors"
        >
          Save rubric
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/80 text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors"
        >
          Reset to defaults
        </button>
      </div>
    </div>
  );
}
