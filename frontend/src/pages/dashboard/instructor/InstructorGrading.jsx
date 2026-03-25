import { useState, useEffect, useCallback } from "react";
import {
  getMyCourses,
  getCourseAssignments,
  getAssignmentSubmissions,
  getAIFeedback,
  addGrade,
} from "../../../services/api";

/* ── Score ring ──────────────────────────────────────────────────────── */
function ScoreRing({ score, max }) {
  const pct = Math.round((score / max) * 100);
  const ringColor = pct >= 85 ? "border-emerald-400 dark:border-emerald-500"
    : pct >= 70 ? "border-blue-400 dark:border-blue-500"
    : "border-amber-400 dark:border-amber-500";
  const txtColor = pct >= 85 ? "text-emerald-600 dark:text-emerald-400"
    : pct >= 70 ? "text-blue-600 dark:text-blue-400"
    : "text-amber-600 dark:text-amber-400";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`w-24 h-24 rounded-full border-4 ${ringColor} flex flex-col items-center justify-center`}>
        <span className={`text-2xl font-extrabold leading-none ${txtColor}`}>{score}</span>
        <span className="text-xs text-slate-400 dark:text-slate-500">/ {max}</span>
      </div>
    </div>
  );
}

/* ── AI Grading Panel ────────────────────────────────────────────────── */
function AIGradingPanel({ sub, onGrade }) {
  const fb = sub.aiFeedback;
  const [overrideMode, setOverrideMode] = useState(false);
  const [manualScore,  setManualScore]  = useState("");
  const [overrideErr,  setOverrideErr]  = useState("");
  const [submitting,   setSubmitting]   = useState(false);
  const [graded,       setGraded]       = useState(false);
  const [publishedGrade, setPublishedGrade] = useState(null);

  const handleAccept = async () => {
    setSubmitting(true);
    try {
      await addGrade(sub.id, fb.suggested_grade);
      setPublishedGrade(fb.suggested_grade);
      setGraded(true);
      onGrade(sub.id);
    } catch { /* already graded or error */ setGraded(true); onGrade(sub.id); }
    finally { setSubmitting(false); }
  };

  const handleOverride = async () => {
    const g = Number(manualScore);
    if (!manualScore || isNaN(g) || g < 0 || g > 100) {
      setOverrideErr("Enter a valid grade between 0 and 100.");
      return;
    }
    setSubmitting(true);
    try {
      await addGrade(sub.id, g);
      setPublishedGrade(g);
      setGraded(true);
      onGrade(sub.id);
    } catch { setGraded(true); onGrade(sub.id); }
    finally { setSubmitting(false); }
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
            Student #{sub.studentId} · {sub.assignmentTitle} · {sub.courseName}
          </p>
        </div>
        <span className="text-xs font-bold px-2.5 py-1 rounded-full border bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-900/50 dark:text-indigo-300 dark:border-indigo-700">
          AI Graded
        </span>
      </div>

      <div className="p-6 space-y-6">
        {/* Exam image */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div className="space-y-2">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Submitted Exam Image</p>
            {sub.imageUrl ? (
              <img src={sub.imageUrl} alt="Student submission" className="w-full max-h-52 object-contain rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900" />
            ) : (
              <div className="w-full h-40 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center border border-dashed border-slate-300 dark:border-slate-600">
                <p className="text-xs text-slate-400 dark:text-slate-500">No image preview</p>
              </div>
            )}
          </div>
          <div className="space-y-2">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Suggested Score</p>
            <div className="flex justify-center py-4">
              {fb.suggested_grade !== null ? (
                <ScoreRing score={Math.round(fb.suggested_grade)} max={100} />
              ) : (
                <p className="text-sm text-slate-400 dark:text-slate-500 italic">No score available</p>
              )}
            </div>
          </div>
        </div>

        {/* Student feedback */}
        {fb.student_feedback && (
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl px-4 py-4 border border-slate-200 dark:border-slate-700">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">AI Feedback for Student</p>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{fb.student_feedback}</p>
          </div>
        )}

        {/* Instructor guidance */}
        {fb.instructor_guidance && (
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl px-4 py-4 border border-amber-200 dark:border-amber-800">
            <p className="text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wide mb-2">Instructor Guidance</p>
            <p className="text-sm text-amber-700 dark:text-amber-300 leading-relaxed">{fb.instructor_guidance}</p>
          </div>
        )}

        {/* Accept / Override */}
        {!graded ? (
          <>
            {!overrideMode ? (
              <div className="flex gap-3">
                <button
                  onClick={handleAccept}
                  disabled={submitting || fb.suggested_grade === null}
                  className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 active:scale-95 text-white text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-2"
                >
                  {submitting ? (
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  )}
                  Accept AI Grade ({fb.suggested_grade !== null ? Math.round(fb.suggested_grade) : "—"}/100)
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
                    type="number" min={0} max={100}
                    value={manualScore}
                    onChange={(e) => { setManualScore(e.target.value); setOverrideErr(""); }}
                    placeholder="0 – 100"
                    className="w-28 px-3 py-2 text-sm font-bold text-slate-900 dark:text-white bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-slate-400 dark:text-slate-500">/ 100</span>
                </div>
                {overrideErr && <p className="text-xs text-red-500 dark:text-red-400">{overrideErr}</p>}
                <div className="flex gap-2">
                  <button onClick={handleOverride} disabled={submitting} className="flex-1 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-bold transition-colors active:scale-95">
                    {submitting ? "Publishing…" : "Publish Override"}
                  </button>
                  <button onClick={() => { setOverrideMode(false); setOverrideErr(""); }} className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-sm font-semibold">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Grade published ({publishedGrade}/100)
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Manual grading form for non-AI submissions ──────────────────────── */
function ManualGradePanel({ sub, onGrade }) {
  const [grade,      setGrade]      = useState("");
  const [error,      setError]      = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [graded,     setGraded]     = useState(false);
  const [publishedGrade, setPublishedGrade] = useState(null);

  const submit = async () => {
    const g = Number(grade);
    if (!grade || isNaN(g) || g < 0 || g > 100) {
      setError("Enter a grade between 0 and 100.");
      return;
    }
    setSubmitting(true);
    try {
      await addGrade(sub.id, g);
      setPublishedGrade(g);
      setGraded(true);
      onGrade(sub.id);
    } catch { setGraded(true); onGrade(sub.id); }
    finally { setSubmitting(false); }
  };

  const pct = grade !== "" && !isNaN(Number(grade)) ? Math.round((Number(grade) / 100) * 100) : null;
  const bar = pct === null ? "" : pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-blue-500" : "bg-amber-500";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-amber-200 dark:border-amber-800 shadow-sm overflow-hidden">
      <div className="px-6 py-4 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-100 dark:border-amber-800">
        <p className="text-sm font-bold text-amber-700 dark:text-amber-300">Manual Review Required</p>
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Student #{sub.studentId} · {sub.assignmentTitle} · {sub.courseName}
        </p>
      </div>
      <div className="p-6 space-y-4">
        {sub.imageUrl ? (
          <img src={sub.imageUrl} alt="Submission" className="w-full max-h-52 object-contain rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900" />
        ) : (
          <div className="w-full h-32 rounded-xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center border-2 border-dashed border-slate-200 dark:border-slate-600">
            <p className="text-xs text-slate-400 dark:text-slate-500">No image available</p>
          </div>
        )}

        {!graded ? (
          <>
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Grade (out of 100)</label>
              <div className="flex items-center gap-3">
                <input
                  type="number" min={0} max={100} value={grade}
                  onChange={(e) => { setGrade(e.target.value); setError(""); }}
                  placeholder="0 – 100"
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
            <button
              onClick={submit}
              disabled={submitting}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 active:scale-95 text-white text-sm font-bold rounded-xl shadow-sm transition-all flex items-center justify-center gap-2"
            >
              {submitting ? "Publishing…" : "Publish Grade"}
            </button>
          </>
        ) : (
          <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-sm font-semibold">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Grade published ({publishedGrade}/100)
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────────────── */
export default function InstructorGrading() {
  const [allSubs,  setAllSubs]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [gradedIds, setGradedIds] = useState(new Set());

  const markGraded = useCallback((id) => {
    setGradedIds((prev) => new Set([...prev, id]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getMyCourses()
      .then(async (res) => {
        const courses = res.data;
        const rows = [];

        await Promise.all(
          courses.map(async (course) => {
            try {
              const assignRes = await getCourseAssignments(course.id);
              await Promise.all(
                assignRes.data.map(async (assignment) => {
                  try {
                    const subRes = await getAssignmentSubmissions(assignment.id);
                    await Promise.all(
                      subRes.data.map(async (sub) => {
                        let aiFeedback = null;
                        if (sub.state === "graded") {
                          try {
                            const fbRes = await getAIFeedback(sub.id);
                            aiFeedback = fbRes.data;
                          } catch { /* no AI feedback */ }
                        }
                        rows.push({
                          id:             sub.id,
                          studentId:      sub.student_id,
                          assignmentTitle: assignment.title,
                          courseName:     course.name,
                          imageUrl:       sub.image_url,
                          rawState:       sub.state,
                          aiFeedback,
                        });
                      })
                    );
                  } catch { /* skip */ }
                })
              );
            } catch { /* skip */ }
          })
        );

        if (!cancelled) setAllSubs(rows);
      })
      .catch(() => { if (!cancelled) setAllSubs([]); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const aiGraded = allSubs.filter((s) => s.rawState === "graded" && s.aiFeedback && !gradedIds.has(s.id));
  const pending  = allSubs.filter((s) => s.rawState === "submitted" && !gradedIds.has(s.id));
  const processing = allSubs.filter((s) => s.rawState === "processing");
  const done     = allSubs.filter((s) => gradedIds.has(s.id));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">Grading Panel</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review AI-graded submissions and manually grade pending ones</p>
        </div>
        {done.length > 0 && (
          <div className="inline-flex items-center gap-2 bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-sm font-semibold px-4 py-2 rounded-xl">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {done.length} graded this session
          </div>
        )}
      </div>

      {/* Progress bar */}
      {!loading && allSubs.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Progress</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{done.length} / {allSubs.length}</p>
          </div>
          <div className="w-full h-2.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-indigo-600 transition-all duration-500" style={{ width: `${Math.round((done.length / allSubs.length) * 100)}%` }} />
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1.5">{allSubs.length - done.length} remaining</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-16">
          <svg className="w-8 h-8 animate-spin text-slate-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
        </div>
      )}

      {/* AI-graded submissions awaiting review */}
      {!loading && aiGraded.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block" />
            AI-Graded — Awaiting Your Review ({aiGraded.length})
          </h2>
          {aiGraded.map((sub) => (
            <AIGradingPanel key={sub.id} sub={sub} onGrade={markGraded} />
          ))}
        </div>
      )}

      {/* Processing */}
      {!loading && processing.map((sub) => (
        <div key={sub.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-blue-200 dark:border-blue-800 shadow-sm px-6 py-5 flex items-center gap-4">
          <svg className="w-6 h-6 text-blue-500 animate-spin shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <div>
            <p className="text-sm font-bold text-slate-900 dark:text-white">AI is grading: {sub.assignmentTitle}</p>
            <p className="text-xs text-slate-400 dark:text-slate-500">Student #{sub.studentId}</p>
          </div>
          <span className="ml-auto text-xs font-semibold bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-2.5 py-1 rounded-full border border-blue-200 dark:border-blue-800">Processing…</span>
        </div>
      ))}

      {/* Pending manual review */}
      {!loading && pending.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
            Pending Manual Review ({pending.length})
          </h2>
          {pending.map((sub) => (
            <ManualGradePanel key={sub.id} sub={sub} onGrade={markGraded} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && aiGraded.length === 0 && pending.length === 0 && processing.length === 0 && (
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
