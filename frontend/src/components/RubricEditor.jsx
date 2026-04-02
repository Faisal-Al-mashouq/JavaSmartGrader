import { useState } from "react";
import { STANDARD_CRITERIA_KEYS } from "../services/courseService";

/**
 * RubricEditor
 * Props:
 *   rubric   – current rubric object { criteria: { key: { label, weight, description, is_standard } } }
 *   onChange – called with the new rubric object whenever anything changes
 *   readOnly – if true, renders a read-only view (no inputs)
 */
export default function RubricEditor({ rubric, onChange, readOnly = false }) {
  const criteria = rubric?.criteria ?? {};

  const standardEntries = STANDARD_CRITERIA_KEYS.map((k) => [k, criteria[k]]).filter(
    ([, v]) => v != null
  );
  const customEntries = Object.entries(criteria).filter(
    ([k]) => !STANDARD_CRITERIA_KEYS.includes(k)
  );

  const total = Object.values(criteria).reduce((s, c) => s + (c.weight ?? 0), 0);
  const totalOk = Math.abs(total - 100) < 0.01;

  const [newCustomKey, setNewCustomKey] = useState("");

  function updateCriterion(key, field, value) {
    onChange({
      ...rubric,
      criteria: {
        ...criteria,
        [key]: { ...criteria[key], [field]: value },
      },
    });
  }

  function addCustom() {
    const rawKey = newCustomKey.trim().toLowerCase().replace(/\s+/g, "_");
    if (!rawKey || criteria[rawKey]) return;
    onChange({
      ...rubric,
      criteria: {
        ...criteria,
        [rawKey]: {
          label: newCustomKey.trim(),
          weight: 0,
          description: "",
          is_standard: false,
        },
      },
    });
    setNewCustomKey("");
  }

  function removeCustom(key) {
    const next = { ...criteria };
    delete next[key];
    onChange({ ...rubric, criteria: next });
  }

  const inputCls =
    "w-full rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500";

  function CriterionRow({ keyName, criterion, isCustom }) {
    return (
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 space-y-2">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 min-w-0">
            {!isCustom && (
              <span className="inline-block text-xs font-semibold bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded-full px-2 py-0.5">
                Standard
              </span>
            )}
            {isCustom && (
              <span className="inline-block text-xs font-semibold bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded-full px-2 py-0.5">
                Custom
              </span>
            )}
            {readOnly || !isCustom ? (
              <span className="font-semibold text-slate-800 dark:text-white text-sm">
                {criterion.label}
              </span>
            ) : (
              <input
                className="rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1 text-sm font-semibold text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 w-40"
                value={criterion.label}
                onChange={(e) => updateCriterion(keyName, "label", e.target.value)}
                placeholder="Criterion name"
              />
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-slate-500 dark:text-slate-400">Weight</span>
            {readOnly ? (
              <span className="font-bold text-slate-800 dark:text-white text-sm w-14 text-right">
                {criterion.weight}%
              </span>
            ) : (
              <input
                type="number"
                min={0}
                max={100}
                className="w-20 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 text-right"
                value={criterion.weight}
                onChange={(e) =>
                  updateCriterion(keyName, "weight", parseFloat(e.target.value) || 0)
                }
              />
            )}
            <span className="text-sm text-slate-500">%</span>
            {isCustom && !readOnly && (
              <button
                type="button"
                onClick={() => removeCustom(keyName)}
                className="ml-1 text-red-500 hover:text-red-700 text-xs font-semibold"
              >
                Remove
              </button>
            )}
          </div>
        </div>

        {readOnly ? (
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            {criterion.description}
          </p>
        ) : (
          <input
            className={inputCls}
            value={criterion.description}
            onChange={(e) => updateCriterion(keyName, "description", e.target.value)}
            placeholder="Description (optional)"
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Standard criteria */}
      {standardEntries.map(([k, v]) => (
        <CriterionRow key={k} keyName={k} criterion={v} isCustom={false} />
      ))}

      {/* Custom criteria */}
      {customEntries.map(([k, v]) => (
        <CriterionRow key={k} keyName={k} criterion={v} isCustom={true} />
      ))}

      {/* Add custom button */}
      {!readOnly && customEntries.length < 2 && (
        <div className="flex gap-2 items-center pt-1">
          <input
            className="flex-1 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500"
            value={newCustomKey}
            onChange={(e) => setNewCustomKey(e.target.value)}
            placeholder="Custom criterion name (e.g. Efficiency)"
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addCustom())}
          />
          <button
            type="button"
            onClick={addCustom}
            disabled={!newCustomKey.trim()}
            className="shrink-0 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 text-slate-700 dark:text-slate-200 text-sm font-semibold px-4 py-2 rounded-xl"
          >
            + Add
          </button>
        </div>
      )}

      {!readOnly && customEntries.length >= 2 && (
        <p className="text-xs text-slate-400 dark:text-slate-500 italic">
          Maximum 2 custom criteria reached.
        </p>
      )}

      {/* Total weight indicator */}
      <div
        className={`flex items-center justify-between rounded-xl px-4 py-2.5 text-sm font-semibold ${
          totalOk
            ? "bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400"
            : "bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400"
        }`}
      >
        <span>Total weight</span>
        <span>{total.toFixed(0)}% {totalOk ? "✓" : `— must equal 100%`}</span>
      </div>
    </div>
  );
}
