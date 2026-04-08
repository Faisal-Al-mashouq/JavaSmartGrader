import { useState, useEffect, useCallback } from "react";
import { getMyCourses, getCourseAssignments } from "../../../services/courseService";
import { getAssignmentSubmissions } from "../../../services/submissionService";
import { getAIFeedback, getTranscription, addGrade, updateGrade, getConfidenceFlags, resolveConfidenceFlag } from "../../../services/gradingService";

/* ── Highlighted OCR code ───────────────────────────────────────────── */
function HighlightedCode({ text, flags, onResolve }) {
  const [openFlagId, setOpenFlagId] = useState(null);
  const [resolving,  setResolving]  = useState(null);

  // Build coordinate → flag lookup
  const flagMap = {};
  for (const f of flags) {
    if (f.coordinates) flagMap[f.coordinates] = f;
  }

  const handleResolve = async (flagId, suggestion) => {
    setResolving(flagId);
    try {
      await resolveConfidenceFlag(flagId, suggestion);
      onResolve();
    } finally {
      setResolving(null);
      setOpenFlagId(null);
    }
  };

  const lines = text.split("\n");

  return (
    <pre className="bg-slate-900 dark:bg-black/50 text-emerald-400 text-xs rounded-xl p-4 overflow-x-auto leading-relaxed font-mono border border-slate-700 dark:border-white/[0.08] whitespace-pre-wrap">
      {lines.map((line, lineIdx) => {
        const tokens = line.match(/\S+/g) || [];
        const separators = line.split(/\S+/);
        const parts = [];

        for (let wi = 0; wi < tokens.length; wi++) {
          if (separators[wi]) parts.push(separators[wi]);

          const coord = `line:${lineIdx}:word:${wi}`;
          const flag  = flagMap[coord];

          if (flag) {
            const isOpen      = openFlagId === flag.id;
            const suggestions = flag.suggestions
              ? flag.suggestions.split(",").map((s) => s.trim()).filter(Boolean)
              : [];

            parts.push(
              <span key={`${lineIdx}-${wi}`} className="relative inline-block">
                <span
                  onClick={() => setOpenFlagId(isOpen ? null : flag.id)}
                  className="text-red-400 bg-red-500/20 rounded px-0.5 cursor-pointer underline decoration-dotted decoration-red-400"
                  title={`Low confidence (${Math.round(Number(flag.confidence_score) * 100)}%) — click to fix`}
                >
                  {tokens[wi]}
                </span>
                {isOpen && (
                  <span className="absolute top-full left-0 z-50 mt-1 bg-slate-800 border border-white/[0.12] rounded-lg shadow-2xl py-1 min-w-[130px] block">
                    <span className="block text-[10px] text-slate-500 px-3 py-1 border-b border-white/[0.06]">
                      {Math.round(Number(flag.confidence_score) * 100)}% confidence
                    </span>
                    {suggestions.map((s, si) => (
                      <button
                        key={si}
                        type="button"
                        disabled={resolving === flag.id}
                        onClick={() => handleResolve(flag.id, s)}
                        className="w-full text-left text-xs px-3 py-1.5 text-slate-200 hover:bg-white/[0.08] font-mono transition-colors disabled:opacity-50"
                      >
                        {resolving === flag.id ? "Applying…" : s}
                      </button>
                    ))}
                  </span>
                )}
              </span>
            );
          } else {
            parts.push(tokens[wi]);
          }
        }

        if (separators[tokens.length]) parts.push(separators[tokens.length]);

        return (
          <span key={lineIdx}>
            {parts}
            {lineIdx < lines.length - 1 ? "\n" : ""}
          </span>
        );
      })}
    </pre>
  );
}

/* ── Score ring ─────────────────────────────────────────────────────── */
function ScoreRing({ score, max }) {
  const pct = Math.round((score / max) * 100);
  const ringColor = pct >= 85 ? "border-emerald-400 dark:border-emerald-500" : pct >= 70 ? "border-blue-400 dark:border-blue-500" : "border-amber-400 dark:border-amber-500";
  const txtColor  = pct >= 85 ? "text-emerald-600 dark:text-emerald-400" : pct >= 70 ? "text-blue-600 dark:text-blue-400" : "text-amber-600 dark:text-amber-400";
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`w-24 h-24 rounded-full border-4 ${ringColor} flex flex-col items-center justify-center`}>
        <span className={`text-2xl font-extrabold leading-none ${txtColor}`}>{Math.round(score)}</span>
        <span className="text-xs text-slate-400 dark:text-slate-500">/ {max}</span>
      </div>
    </div>
  );
}

/* ── AI Panel ───────────────────────────────────────────────────────── */
function AIGradingPanel({ sub, onPublished, onFlagResolved }) {
  const fb = sub.aiFeedback;
  const [overrideMode, setOverrideMode] = useState(false);
  const [manualScore,  setManualScore]  = useState("");
  const [manualFb,     setManualFb]     = useState("");
  const [overrideErr,  setOverrideErr]  = useState("");
  const [showCode,     setShowCode]     = useState(false);
  const [publishing,   setPublishing]   = useState(false);
  const [published,    setPublished]    = useState(false);

  const suggestedGrade = fb?.suggested_grade ?? 0;

  const doPublish = async (grade) => {
    setPublishing(true);
    try {
      try {
        await addGrade(sub.id, grade);
      } catch (e) {
        if (e.response?.status === 409) {
          await updateGrade(sub.id, grade);
        } else {
          throw e;
        }
      }
      setPublished(true);
      onPublished(sub.id, grade);
    } catch (e) {
      setOverrideErr(e.response?.data?.detail ?? "Failed to publish grade.");
    } finally {
      setPublishing(false);
    }
  };

  const handleAccept   = () => doPublish(suggestedGrade);
  const handleOverride = () => {
    const g = Number(manualScore);
    if (!manualScore || isNaN(g) || g < 0 || g > 100) {
      setOverrideErr("Enter a valid grade between 0 and 100.");
      return;
    }
    doPublish(g);
  };

  if (published) {
    return (
      <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-emerald-200 dark:border-emerald-500/25 shadow-sm dark:shadow-xl px-6 py-5 flex items-center gap-4">
        <div className="w-11 h-11 rounded-full bg-emerald-100 dark:bg-emerald-500/15 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-bold text-slate-900 dark:text-white">Grade Published — Submission #{sub.id}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">{sub.assignment?.title ?? `Assignment #${sub.assignment_id}`}</p>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/25">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />Published
        </span>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-indigo-200 dark:border-indigo-500/25 shadow-md dark:shadow-xl overflow-hidden">

      {/* Header */}
      <div className="px-6 py-4 bg-indigo-50 dark:bg-indigo-500/10 border-b border-indigo-100 dark:border-indigo-500/15 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shrink-0 shadow-md">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636-6.364l.707.707M12 21v-1M6.343 17.657l-.707-.707M17.657 17.657l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-bold text-indigo-700 dark:text-indigo-300">AI Grading Results</p>
          <p className="text-xs text-indigo-500 dark:text-indigo-400">
            Student #{sub.student_id} · {sub.assignment?.title ?? `Assignment #${sub.assignment_id}`} · {sub.course?.name ?? ""}
          </p>
        </div>
        <span className="text-xs font-bold px-2.5 py-1 rounded-full border bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/25">
          Submission #{sub.id}
        </span>
      </div>

      <div className="p-6 space-y-6">

        {/* Score + code toggle */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div className="space-y-2">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide">Extracted Code (OCR)</p>
            <button
              onClick={() => setShowCode((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-white/[0.05] hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-colors text-sm font-semibold text-slate-700 dark:text-slate-200"
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
            {showCode && sub.transcription?.transcribed_text && (
              <HighlightedCode
                text={sub.transcription.transcribed_text}
                flags={sub.confidenceFlags ?? []}
                onResolve={onFlagResolved}
              />
            )}
            {showCode && (sub.confidenceFlags ?? []).length > 0 && (
              <p className="text-[11px] text-red-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                {sub.confidenceFlags.length} low-confidence word{sub.confidenceFlags.length > 1 ? "s" : ""} flagged — click to fix
              </p>
            )}
            {showCode && !sub.transcription?.transcribed_text && (
              <p className="text-xs text-slate-400 dark:text-slate-500 italic px-1">No OCR transcription available.</p>
            )}
          </div>

          <div className="space-y-3">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide">AI Suggested Score</p>
            <div className="flex justify-center py-2">
              <ScoreRing score={suggestedGrade} max={100} />
            </div>
          </div>
        </div>

        {/* Feedback */}
        {fb?.student_feedback && (
          <div className="bg-slate-50 dark:bg-white/[0.03] rounded-xl px-4 py-4 border border-slate-200 dark:border-white/[0.08]">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">AI Feedback</p>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{fb.student_feedback}</p>
          </div>
        )}
        {fb?.instructor_guidance && (
          <div className="bg-amber-50 dark:bg-amber-500/10 rounded-xl px-4 py-4 border border-amber-200 dark:border-amber-500/20">
            <p className="text-xs font-bold text-amber-500 dark:text-amber-400 uppercase tracking-wide mb-2">Instructor Guidance (from AI)</p>
            <p className="text-sm text-amber-700 dark:text-amber-300 leading-relaxed">{fb.instructor_guidance}</p>
          </div>
        )}

        {/* Accept / Override */}
        {!overrideMode ? (
          <div className="flex gap-3">
            <button
              onClick={handleAccept}
              disabled={publishing}
              className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-70 active:scale-95 text-white text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-2"
            >
              {publishing ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              )}
              Accept &amp; Publish AI Grade ({Math.round(suggestedGrade)}/100)
            </button>
            <button
              onClick={() => setOverrideMode(true)}
              className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-white/[0.1] text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
            >
              Override Grade
            </button>
          </div>
        ) : (
          <div className="space-y-3 border border-slate-200 dark:border-white/[0.08] rounded-xl p-4">
            <p className="text-sm font-bold text-slate-700 dark:text-slate-200">Manual Override</p>
            <div className="flex items-center gap-3">
              <input
                type="number" min={0} max={100}
                value={manualScore}
                onChange={(e) => { setManualScore(e.target.value); setOverrideErr(""); }}
                placeholder="0 – 100"
                className="w-28 px-3 py-2 text-sm font-bold text-slate-900 dark:text-white bg-white dark:bg-white/[0.05] border border-slate-200 dark:border-white/[0.1] rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <span className="text-sm text-slate-400 dark:text-slate-500">/ 100</span>
            </div>
            <textarea
              rows={3} value={manualFb}
              onChange={(e) => setManualFb(e.target.value)}
              placeholder="Optional: note the reason for override…"
              className="w-full px-3 py-2 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-white/[0.05] border border-slate-200 dark:border-white/[0.1] rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
            {overrideErr && <p className="text-xs text-red-500 dark:text-red-400">{overrideErr}</p>}
            <div className="flex gap-2">
              <button
                onClick={handleOverride}
                disabled={publishing}
                className="flex-1 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70 text-white text-sm font-bold transition-colors active:scale-95"
              >
                {publishing ? "Publishing…" : "Publish Override"}
              </button>
              <button onClick={() => { setOverrideMode(false); setOverrideErr(""); }} className="px-4 py-2 rounded-xl border border-slate-200 dark:border-white/[0.1] text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────────────── */
export default function InstructorGrading() {
  const [aiGraded,   setAiGraded]   = useState([]);
  const [processing, setProcessing] = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [published,  setPublished]  = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const coursesRes  = await getMyCourses();
      const courses     = coursesRes.data;

      const assignmentsByCoursePairs = await Promise.all(
        courses.map((c) =>
          getCourseAssignments(c.id)
            .then((r) => r.data.map((a) => ({ ...a, course: c })))
            .catch(() => [])
        )
      );
      const allAssignments = assignmentsByCoursePairs.flat();

      const subsByAssignmentPairs = await Promise.all(
        allAssignments.map((a) =>
          getAssignmentSubmissions(a.id)
            .then((r) => r.data.map((s) => ({ ...s, assignment: a, course: a.course })))
            .catch(() => [])
        )
      );
      const allSubs = subsByAssignmentPairs.flat();
      allSubs.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));

      const gradedSubs     = allSubs.filter((s) => s.state === "graded");
      const processingList = allSubs.filter((s) => s.state === "submitted" || s.state === "processing");

      const enriched = await Promise.all(
        gradedSubs.map(async (s) => {
          const [fbRes, tRes] = await Promise.all([
            getAIFeedback(s.id).catch(() => null),
            getTranscription(s.id).catch(() => null),
          ]);
          const transcription = tRes?.data ?? null;
          let confidenceFlags = [];
          if (transcription?.id) {
            confidenceFlags = await getConfidenceFlags(transcription.id)
              .then((r) => r.data)
              .catch(() => []);
          }
          return { ...s, aiFeedback: fbRes?.data ?? null, transcription, confidenceFlags };
        })
      );

      setAiGraded(enriched);
      setProcessing(processingList);
    } catch (e) {
      console.error("InstructorGrading fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handlePublished = (submissionId, grade) => {
    setPublished((prev) => ({ ...prev, [submissionId]: grade }));
  };

  const totalDone     = Object.keys(published).length;
  const totalAll      = aiGraded.length + processing.length;
  const pendingReview = aiGraded.filter((s) => !(s.id in published));

  return (
    <div className="space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">Grading</p>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">Grading Panel</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review AI-graded submissions and publish grades</p>
        </div>
        {totalDone > 0 && (
          <div className="inline-flex items-center gap-2 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-sm font-semibold px-4 py-2 rounded-xl">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {totalDone} published this session
          </div>
        )}
      </div>

      {/* Progress bar */}
      {!loading && totalAll > 0 && (
        <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Session Progress</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{totalDone} / {aiGraded.length} AI-graded reviewed</p>
          </div>
          <div className="w-full h-2.5 bg-slate-100 dark:bg-white/[0.05] rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500" style={{ width: `${aiGraded.length > 0 ? Math.round((totalDone / aiGraded.length) * 100) : 0}%` }} />
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1.5">{pendingReview.length} remaining to review</p>
        </div>
      )}

      {loading && (
        <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">Loading submissions…</div>
      )}

      {/* AI Graded — awaiting review */}
      {!loading && pendingReview.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block" />
            AI-Graded — Awaiting Your Review ({pendingReview.length})
          </h2>
          {pendingReview.map((sub) => (
            <AIGradingPanel key={sub.id} sub={sub} onPublished={handlePublished} onFlagResolved={load} />
          ))}
        </div>
      )}

      {/* Processing */}
      {!loading && processing.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse inline-block" />
            Being Processed ({processing.length})
          </h2>
          {processing.map((sub) => (
            <div key={sub.id} className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-blue-200 dark:border-blue-500/25 shadow-sm dark:shadow-xl px-6 py-5 flex items-center gap-4">
              <svg className="w-6 h-6 text-blue-500 animate-spin shrink-0" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
              <div>
                <p className="text-sm font-bold text-slate-900 dark:text-white">
                  {sub.assignment?.title ?? `Assignment #${sub.assignment_id}`}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Student #{sub.student_id} · Submission #{sub.id} · {new Date(sub.submitted_at).toLocaleDateString()}
                </p>
              </div>
              <span className="ml-auto text-xs font-semibold bg-blue-50 dark:bg-blue-500/15 text-blue-600 dark:text-blue-400 px-2.5 py-1 rounded-full border border-blue-200 dark:border-blue-500/25">Processing…</span>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && aiGraded.length === 0 && processing.length === 0 && (
        <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl py-16 flex flex-col items-center gap-3">
          <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-2xl flex items-center justify-center shadow-lg">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
