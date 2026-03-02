import { useState } from "react";
import { useSubmissions } from "../../../context/SubmissionsContext";

/* ── Static pending (manual review) ───────────────────────────────── */
const MANUAL_PENDING = [
  { id: "m1", student: "Sara Al-Otaibi",   sid: "443002", assignment: "Lab Assignment 3 - Inheritance",  course: "CS201", submitted: "Dec 4, 2024",  maxGrade: 100 },
  { id: "m2", student: "Nora Al-Shehri",   sid: "443006", assignment: "Midterm Exam - OOP Concepts",    course: "CS201", submitted: "Dec 1, 2024",  maxGrade: 100 },
  { id: "m3", student: "Omar Al-Dosari",   sid: "443007", assignment: "Final Project - Banking System", course: "CS201", submitted: "Dec 15, 2024", maxGrade: 100 },
];

/* ── Rubric bar ────────────────────────────────────────────────────── */
function RubricRow({ criterion, desc, score, max }) {
  const pct = Math.round((score / max) * 100);
  const bar = pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-blue-500" : "bg-amber-500";
  const txt = pct >= 85 ? "text-emerald-600 dark:text-emerald-400" : pct >= 70 ? "text-blue-600 dark:text-blue-400" : "text-amber-600 dark:text-amber-400";
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{criterion}</span>
          <span className="text-xs text-slate-400 dark:text-slate-500 ml-2 hidden sm:inline">{desc}</span>
        </div>
        <span className={`text-sm font-bold ${txt}`}>{score}<span className="text-xs font-normal text-slate-400 dark:text-slate-500">/{max}</span></span>
      </div>
      <div className="w-full h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${bar} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/* ── Score ring ────────────────────────────────────────────────────── */
function ScoreRing({ score, max, verdict }) {
  const pct = Math.round((score / max) * 100);
  const ringColor = pct >= 85 ? "border-emerald-400 dark:border-emerald-500" : pct >= 70 ? "border-blue-400 dark:border-blue-500" : "border-amber-400 dark:border-amber-500";
  const txtColor  = pct >= 85 ? "text-emerald-600 dark:text-emerald-400" : pct >= 70 ? "text-blue-600 dark:text-blue-400" : "text-amber-600 dark:text-amber-400";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`w-24 h-24 rounded-full border-4 ${ringColor} flex flex-col items-center justify-center`}>
        <span className={`text-2xl font-extrabold leading-none ${txtColor}`}>{score}</span>
        <span className="text-xs text-slate-400 dark:text-slate-500">/ {max}</span>
      </div>
      <span className={`text-xs font-bold ${txtColor}`}>{verdict}</span>
    </div>
  );
}

/* ── AI Grading Panel ─────────────────────────────────────────────── */
function AIGradingPanel({ sub, onAccept, onOverride }) {
  const r = sub.aiResult;
  const [overrideMode, setOverrideMode] = useState(false);
  const [manualScore,  setManualScore]  = useState("");
  const [manualFb,     setManualFb]     = useState("");
  const [overrideErr,  setOverrideErr]  = useState("");
  const [showCode,     setShowCode]     = useState(false);

  const handleOverride = () => {
    const g = Number(manualScore);
    if (!manualScore || isNaN(g) || g < 0 || g > r.max) {
      setOverrideErr(`Enter a valid grade between 0 and ${r.max}.`);
      return;
    }
    onOverride(sub.id, g, manualFb);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-indigo-200 dark:border-indigo-800 shadow-md overflow-hidden">

      {/* Header */}
      <div className="px-6 py-4 bg-indigo-50 dark:bg-indigo-900/30 border-b border-indigo-100 dark:border-indigo-800 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636-6.364l.707.707M12 21v-1M6.343 17.657l-.707-.707M17.657 17.657l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-bold text-indigo-700 dark:text-indigo-300">AI Grading Results</p>
          <p className="text-xs text-indigo-500 dark:text-indigo-400">
            {sub.studentName} · {sub.assignment} · {sub.course}
          </p>
        </div>
        <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${r.overridden ? "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800" : "bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-900/50 dark:text-indigo-300 dark:border-indigo-700"}`}>
          {r.overridden ? "Manually Overridden" : "AI Graded"}
        </span>
      </div>

      <div className="p-6 space-y-6">

        {/* Submitted image + score side-by-side */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

          {/* Exam image */}
          <div className="space-y-2">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Submitted Exam Image</p>
            {sub.fileUrl ? (
              <img src={sub.fileUrl} alt="Student submission" className="w-full max-h-52 object-contain rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900" />
            ) : (
              <div className="w-full h-40 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center border border-dashed border-slate-300 dark:border-slate-600">
                <p className="text-xs text-slate-400 dark:text-slate-500">No image preview</p>
              </div>
            )}
          </div>

          {/* Overall score + verdict */}
          <div className="space-y-3">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Overall Score</p>
            <div className="flex justify-center py-2">
              <ScoreRing score={r.total} max={r.max} verdict={r.verdict} />
            </div>

            {/* Extracted code toggle */}
            <button
              onClick={() => setShowCode((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors text-sm font-semibold text-slate-700 dark:text-slate-200"
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                View Extracted Code
              </span>
              <svg className={`w-4 h-4 transition-transform ${showCode ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Extracted code */}
        {showCode && (
          <div>
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Extracted Code (OCR)</p>
            <pre className="bg-slate-900 dark:bg-slate-950 text-emerald-400 text-xs rounded-xl p-4 overflow-x-auto leading-relaxed font-mono border border-slate-700">
              {r.extractedCode}
            </pre>
          </div>
        )}

        {/* Rubric breakdown */}
        <div>
          <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-3">Rubric Breakdown</p>
          <div className="space-y-3">
            {r.rubric.map((row) => (
              <RubricRow key={row.criterion} {...row} />
            ))}
          </div>
        </div>

        {/* AI Feedback */}
        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl px-4 py-4 border border-slate-200 dark:border-slate-700">
          <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">AI Feedback</p>
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{r.feedback}</p>
        </div>

        {/* Accept / Override buttons */}
        {!r.overridden && (
          <>
            {!overrideMode ? (
              <div className="flex gap-3">
                <button
                  onClick={() => onAccept(sub.id)}
                  className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Accept &amp; Publish AI Grade ({r.total}/{r.max})
                </button>
                <button
                  onClick={() => setOverrideMode(true)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                  Override Grade
                </button>
              </div>
            ) : (
              <div className="space-y-3 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
                <p className="text-sm font-bold text-slate-700 dark:text-slate-200">Manual Override</p>
                <div className="flex items-center gap-3">
                  <input
                    type="number" min={0} max={r.max}
                    value={manualScore}
                    onChange={(e) => { setManualScore(e.target.value); setOverrideErr(""); }}
                    placeholder={`0 – ${r.max}`}
                    className="w-28 px-3 py-2 text-sm font-bold text-slate-900 dark:text-white bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-slate-400 dark:text-slate-500">/ {r.max}</span>
                </div>
                <textarea
                  rows={3} value={manualFb}
                  onChange={(e) => setManualFb(e.target.value)}
                  placeholder="Optional: add your feedback to the student..."
                  className="w-full px-3 py-2 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
                {overrideErr && <p className="text-xs text-red-500 dark:text-red-400">{overrideErr}</p>}
                <div className="flex gap-2">
                  <button onClick={handleOverride} className="flex-1 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition-colors active:scale-95">Publish Override</button>
                  <button onClick={() => { setOverrideMode(false); setOverrideErr(""); }} className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">Cancel</button>
                </div>
              </div>
            )}
          </>
        )}

        {r.overridden && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-sm font-semibold">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Grade published ({r.total}/{r.max}) — student has been notified.
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Manual grading form ──────────────────────────────────────────── */
function ManualGradeForm({ item, onSubmit }) {
  const [grade,    setGrade]    = useState("");
  const [feedback, setFeedback] = useState("");
  const [error,    setError]    = useState("");

  const submit = () => {
    const g = Number(grade);
    if (!grade || isNaN(g) || g < 0 || g > item.maxGrade) {
      setError(`Enter a grade between 0 and ${item.maxGrade}.`);
      return;
    }
    onSubmit(item.id, g, feedback);
  };

  const pct = grade !== "" && !isNaN(Number(grade)) ? Math.round((Number(grade) / item.maxGrade) * 100) : null;
  const bar = pct === null ? "" : pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-blue-500" : "bg-amber-500";

  return (
    <div className="pt-4 border-t border-slate-100 dark:border-slate-700 space-y-4">
      <div className="w-full h-32 rounded-xl bg-slate-100 dark:bg-slate-700 flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-200 dark:border-slate-600">
        <svg className="w-8 h-8 text-slate-300 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <p className="text-xs text-slate-400 dark:text-slate-500">Exam image preview</p>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Grade <span className="normal-case font-normal">(out of {item.maxGrade})</span></label>
        <div className="flex items-center gap-3">
          <input type="number" min={0} max={item.maxGrade} value={grade} onChange={(e) => { setGrade(e.target.value); setError(""); }} placeholder={`0 – ${item.maxGrade}`}
            className="w-28 px-3 py-2 text-sm font-bold text-slate-900 dark:text-white bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
          />
          {pct !== null && (
            <div className="flex items-center gap-2 flex-1">
              <div className="flex-1 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all ${bar}`} style={{ width: `${pct}%` }} />
              </div>
              <span className="text-sm font-bold text-slate-700 dark:text-slate-200">{pct}%</span>
            </div>
          )}
        </div>
        {error && <p className="text-xs text-red-500 dark:text-red-400">{error}</p>}
      </div>
      <textarea rows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Write feedback for the student..."
        className="w-full px-3 py-2 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
      />
      <button onClick={submit} className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white text-sm font-bold rounded-xl shadow-sm transition-all flex items-center justify-center gap-2">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        Submit Grade
      </button>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────────────── */
export default function InstructorGrading() {
  const { submissions, publishGrade, overrideGrade, clearAll } = useSubmissions();
  const [expanded,  setExpanded]  = useState(null);
  const [manualDone, setManualDone] = useState([]);

  const aiGraded   = submissions.filter((s) => s.status === "AI Graded");
  const published  = submissions.filter((s) => s.status === "Published");
  const manualLeft = MANUAL_PENDING.filter((p) => !manualDone.find((d) => d.id === p.id));

  const handleAccept   = (id) => { publishGrade(id); };
  const handleOverride = (id, score, fb) => { overrideGrade(id, score, fb); };
  const handleManual   = (id, grade, fb) => {
    setManualDone((prev) => [...prev, { id, grade, feedback: fb }]);
    setExpanded(null);
  };

  const totalDone = published.length + manualDone.length;
  const totalAll  = submissions.length + MANUAL_PENDING.length;

  return (
    <div className="space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">Grading Panel</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review AI-graded submissions and manually grade pending ones</p>
        </div>
        <div className="flex items-center gap-2">
          {totalDone > 0 && (
            <div className="inline-flex items-center gap-2 bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-sm font-semibold px-4 py-2 rounded-xl">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              {totalDone} published this session
            </div>
          )}
          {submissions.length > 0 && (
            <button
              onClick={clearAll}
              title="Clear all demo submissions"
              className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {totalAll > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Session Progress</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{totalDone} / {totalAll}</p>
          </div>
          <div className="w-full h-2.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-indigo-600 transition-all duration-500" style={{ width: `${Math.round((totalDone / totalAll) * 100)}%` }} />
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1.5">{totalAll - totalDone} remaining</p>
        </div>
      )}

      {/* ── AI Graded submissions ─────────────────────────────────── */}
      {aiGraded.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block" />
            AI-Graded — Awaiting Your Review ({aiGraded.length})
          </h2>
          {aiGraded.map((sub) => (
            <AIGradingPanel
              key={sub.id}
              sub={sub}
              onAccept={handleAccept}
              onOverride={handleOverride}
            />
          ))}
        </div>
      )}

      {/* ── Processing (still grading) ───────────────────────────── */}
      {submissions.filter((s) => s.status === "Processing").map((sub) => (
        <div key={sub.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-blue-200 dark:border-blue-800 shadow-sm px-6 py-5 flex items-center gap-4">
          <svg className="w-6 h-6 text-blue-500 animate-spin shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <div>
            <p className="text-sm font-bold text-slate-900 dark:text-white">AI is grading: {sub.assignment}</p>
            <p className="text-xs text-slate-400 dark:text-slate-500">Submitted by {sub.studentName} · {sub.filename}</p>
          </div>
          <span className="ml-auto text-xs font-semibold bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-2.5 py-1 rounded-full border border-blue-200 dark:border-blue-800">Processing…</span>
        </div>
      ))}

      {/* ── Manual pending ───────────────────────────────────────── */}
      {manualLeft.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
            Pending Manual Review ({manualLeft.length})
          </h2>
          {manualLeft.map((item) => (
            <div key={item.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm hover:shadow-md transition-all overflow-hidden">
              <div className="px-6 py-4 flex items-center gap-4">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shrink-0">
                  <span className="text-sm font-bold text-white">{item.student.split(" ").map((n) => n[0]).join("").slice(0, 2)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{item.student}</p>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-2 py-0.5 rounded-md">{item.course}</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400 truncate">{item.assignment}</span>
                  </div>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Submitted {item.submitted}</p>
                </div>
                <button
                  onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                  className={`shrink-0 flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-xl transition-all active:scale-95 ${expanded === item.id ? "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300" : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm"}`}
                >
                  {expanded === item.id ? "Close" : "Grade"}
                  <svg className={`w-4 h-4 transition-transform ${expanded === item.id ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
              {expanded === item.id && (
                <div className="px-6 pb-5">
                  <ManualGradeForm item={item} onSubmit={handleManual} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Published this session ───────────────────────────────── */}
      {(published.length > 0 || manualDone.length > 0) && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            Published This Session
          </h2>
          {published.map((sub) => (
            <div key={sub.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm px-6 py-4 flex items-center gap-4">
              <div className="w-11 h-11 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shrink-0">
                <span className="text-sm font-bold text-white">{sub.studentName.slice(0, 2).toUpperCase()}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{sub.studentName}</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 truncate">{sub.assignment} · {sub.filename}</p>
              </div>
              <div className="text-right shrink-0">
                <p className={`text-lg font-extrabold ${sub.aiResult?.total >= 70 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                  {sub.aiResult?.total}<span className="text-xs font-normal text-slate-400 dark:text-slate-500">/{sub.aiResult?.max}</span>
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500">{sub.aiResult?.overridden ? "Override" : "AI grade"}</p>
              </div>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800 shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />Published
              </span>
            </div>
          ))}
          {manualDone.map(({ id, grade, feedback }) => {
            const item = MANUAL_PENDING.find((p) => p.id === id);
            return (
              <div key={id} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm px-6 py-4 flex items-center gap-4">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shrink-0">
                  <span className="text-sm font-bold text-white">{item.student.split(" ").map((n) => n[0]).join("").slice(0, 2)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{item.student}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 truncate">{item.assignment}</p>
                  {feedback && <p className="text-xs italic text-slate-500 dark:text-slate-400 truncate mt-0.5">"{feedback}"</p>}
                </div>
                <div className="text-right shrink-0">
                  <p className={`text-lg font-extrabold ${grade / item.maxGrade >= 0.7 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                    {grade}<span className="text-xs font-normal text-slate-400 dark:text-slate-500">/{item.maxGrade}</span>
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />Published
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty state */}
      {aiGraded.length === 0 && submissions.filter((s) => s.status === "Processing").length === 0 && manualLeft.length === 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm py-16 flex flex-col items-center gap-3">
          <div className="w-16 h-16 bg-emerald-50 dark:bg-emerald-900/30 rounded-2xl flex items-center justify-center">
            <svg className="w-8 h-8 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-base font-bold text-slate-900 dark:text-white">All caught up!</p>
          <p className="text-sm text-slate-400 dark:text-slate-500">No pending submissions to grade right now.</p>
        </div>
      )}
    </div>
  );
}
