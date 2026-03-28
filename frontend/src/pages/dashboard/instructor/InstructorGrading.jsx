import { useState, useEffect } from "react";
import { getMyCourses, getCourseAssignments } from "../../../services/courseService";
import { getAssignmentSubmissions } from "../../../services/submissionService";
import { getAIFeedback, getTranscription, addGrade, updateGrade } from "../../../services/gradingService";

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
function AIGradingPanel({ sub, onPublished }) {
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
      // Try POST first, fall back to PUT if grade already exists
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
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-emerald-200 dark:border-emerald-800 shadow-sm px-6 py-5 flex items-center gap-4">
        <div className="w-11 h-11 rounded-full bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center shrink-0">
          <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-bold text-slate-900 dark:text-white">Grade Published — Submission #{sub.id}</p>
          <p className="text-xs text-slate-400 dark:text-slate-500">{sub.assignment?.title ?? `Assignment #${sub.assignment_id}`}</p>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />Published
        </span>
      </div>
    );
  }

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
            Student #{sub.student_id} · {sub.assignment?.title ?? `Assignment #${sub.assignment_id}`} · {sub.course?.name ?? ""}
          </p>
        </div>
        <span className="text-xs font-bold px-2.5 py-1 rounded-full border bg-indigo-100 text-indigo-700 border-indigo-200 dark:bg-indigo-900/50 dark:text-indigo-300 dark:border-indigo-700">
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
            {showCode && sub.transcription?.transcribed_text && (
              <pre className="bg-slate-900 dark:bg-slate-950 text-emerald-400 text-xs rounded-xl p-4 overflow-x-auto leading-relaxed font-mono border border-slate-700">
                {sub.transcription.transcribed_text}
              </pre>
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
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl px-4 py-4 border border-slate-200 dark:border-slate-700">
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">AI Feedback</p>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{fb.student_feedback}</p>
          </div>
        )}
        {fb?.instructor_guidance && (
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl px-4 py-4 border border-amber-200 dark:border-amber-800">
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
            <textarea
              rows={3} value={manualFb}
              onChange={(e) => setManualFb(e.target.value)}
              placeholder="Optional: note the reason for override…"
              className="w-full px-3 py-2 text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
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
              <button onClick={() => { setOverrideMode(false); setOverrideErr(""); }} className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────────────── */
export default function InstructorGrading() {
  const [aiGraded,  setAiGraded]  = useState([]); // graded submissions enriched with aiFeedback
  const [processing, setProcessing] = useState([]); // submitted/processing submissions
  const [loading,   setLoading]   = useState(true);
  const [published, setPublished] = useState({}); // submissionId → grade

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
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

        // Fetch AI feedback + transcription for graded subs (parallel)
        const enriched = await Promise.all(
          gradedSubs.map(async (s) => {
            const [fbRes, tRes] = await Promise.all([
              getAIFeedback(s.id).catch(() => null),
              getTranscription(s.id).catch(() => null),
            ]);
            return { ...s, aiFeedback: fbRes?.data ?? null, transcription: tRes?.data ?? null };
          })
        );

        if (!cancelled) {
          setAiGraded(enriched);
          setProcessing(processingList);
          setLoading(false);
        }
      } catch (e) {
        console.error("InstructorGrading fetch error:", e);
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  const handlePublished = (submissionId, grade) => {
    setPublished((prev) => ({ ...prev, [submissionId]: grade }));
  };

  const totalDone = Object.keys(published).length;
  const totalAll  = aiGraded.length + processing.length;
  const pendingReview = aiGraded.filter((s) => !(s.id in published));

  return (
    <div className="space-y-8">

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">Grading Panel</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review AI-graded submissions and publish grades</p>
        </div>
        {totalDone > 0 && (
          <div className="inline-flex items-center gap-2 bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-sm font-semibold px-4 py-2 rounded-xl">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {totalDone} published this session
          </div>
        )}
      </div>

      {/* Progress bar */}
      {!loading && totalAll > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm px-6 py-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Session Progress</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{totalDone} / {aiGraded.length} AI-graded reviewed</p>
          </div>
          <div className="w-full h-2.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-indigo-600 transition-all duration-500" style={{ width: `${aiGraded.length > 0 ? Math.round((totalDone / aiGraded.length) * 100) : 0}%` }} />
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
            <AIGradingPanel
              key={sub.id}
              sub={sub}
              onPublished={handlePublished}
            />
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
            <div key={sub.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-blue-200 dark:border-blue-800 shadow-sm px-6 py-5 flex items-center gap-4">
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
              <span className="ml-auto text-xs font-semibold bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-2.5 py-1 rounded-full border border-blue-200 dark:border-blue-800">Processing…</span>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && aiGraded.length === 0 && processing.length === 0 && (
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
