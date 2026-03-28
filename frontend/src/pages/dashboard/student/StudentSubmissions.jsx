import { useState, useEffect } from "react";
import { getMySubmissions } from "../../../services/submissionService";
import { getAssignment } from "../../../services/courseService";
import { getAIFeedback } from "../../../services/gradingService";

/* ── helpers ─────────────────────────────────────────────────────── */
const stateToStatus = (state) => ({
  submitted:  "Processing",
  processing: "Processing",
  graded:     "AI Graded",
  failed:     "Failed",
}[state] ?? state);

const STATUS_CLS = {
  "Processing": "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  "AI Graded":  "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
  "Failed":     "bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
};
const STATUS_DOT = {
  "Processing": "bg-blue-500 animate-pulse",
  "AI Graded":  "bg-indigo-500",
  "Failed":     "bg-red-500",
};

function StatusBadge({ status }) {
  const cls = STATUS_CLS[status] ?? "bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600";
  const dot = STATUS_DOT[status] ?? "bg-slate-400";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {status}
    </span>
  );
}

function GradeCircle({ grade, max }) {
  const pct = Math.round((grade / max) * 100);
  const [color, bg] = pct >= 85
    ? ["text-emerald-600 dark:text-emerald-400", "bg-emerald-50 dark:bg-emerald-900/30"]
    : pct >= 70
    ? ["text-blue-600 dark:text-blue-400",       "bg-blue-50 dark:bg-blue-900/30"]
    : ["text-amber-600 dark:text-amber-400",     "bg-amber-50 dark:bg-amber-900/30"];
  return (
    <div className={`w-14 h-14 rounded-full ${bg} flex flex-col items-center justify-center shrink-0`}>
      <span className={`text-base font-extrabold leading-none ${color}`}>{grade}</span>
      <span className="text-xs text-slate-400 dark:text-slate-500 leading-none">/{max}</span>
    </div>
  );
}

/* ── Submission card ─────────────────────────────────────────────── */
function SubmissionCard({ sub, expanded, onToggle }) {
  const fb     = sub.aiFeedback;
  const isAI   = sub.status === "AI Graded";
  const grade  = fb?.suggested_grade != null ? Math.round(fb.suggested_grade) : null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
      <div className="px-6 py-4 flex items-center gap-4">

        {/* Grade circle / spinner */}
        <div className="shrink-0">
          {isAI && grade !== null ? (
            <GradeCircle grade={grade} max={100} />
          ) : (
            <div className="w-14 h-14 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
              {sub.status === "Processing" ? (
                <svg className="w-6 h-6 text-slate-300 dark:text-slate-500 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
              ) : (
                <svg className="w-6 h-6 text-slate-300 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{sub.assignmentTitle}</p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-md">
                  Course {sub.courseId}
                </span>
                <span className="text-xs text-slate-400 dark:text-slate-500 font-mono">#{sub.id}</span>
              </div>
            </div>
            <StatusBadge status={sub.status} />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs text-slate-400 dark:text-slate-500">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Submitted {new Date(sub.submitted_at).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>

        {/* Expand AI results */}
        {isAI && fb && (
          <button
            onClick={onToggle}
            className="shrink-0 flex items-center gap-1.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 px-3 py-1.5 rounded-lg transition-colors"
          >
            AI Results
            <svg className={`w-4 h-4 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* AI feedback panel */}
      {isAI && fb && expanded && (
        <div className="px-6 pb-5 border-t border-slate-100 dark:border-slate-700 pt-4 bg-slate-50 dark:bg-slate-900/40 space-y-4">

          {/* Transcribed code */}
          {sub.transcription?.transcribed_text && (
            <div>
              <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Extracted Code (OCR)</p>
              <pre className="bg-slate-900 dark:bg-slate-950 text-emerald-400 text-xs rounded-xl p-4 overflow-x-auto leading-relaxed font-mono border border-slate-700">
                {sub.transcription.transcribed_text}
              </pre>
            </div>
          )}

          {/* Score */}
          {grade !== null && (
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">AI Suggested Grade</p>
                <div className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${grade >= 85 ? "bg-emerald-500" : grade >= 70 ? "bg-blue-500" : "bg-amber-500"}`}
                    style={{ width: `${grade}%` }}
                  />
                </div>
              </div>
              <div className={`w-20 h-20 rounded-full border-4 flex flex-col items-center justify-center shrink-0 ${grade >= 70 ? "border-emerald-400 dark:border-emerald-600" : "border-amber-400 dark:border-amber-600"}`}>
                <span className={`text-2xl font-extrabold ${grade >= 70 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>{grade}</span>
                <span className="text-xs text-slate-400 dark:text-slate-500">/100</span>
              </div>
            </div>
          )}

          {/* Feedback text */}
          {fb.student_feedback && (
            <div>
              <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">AI Feedback</p>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{fb.student_feedback}</p>
            </div>
          )}
          {fb.instructor_guidance && (
            <div>
              <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">Instructor Guidance (from AI)</p>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed italic">{fb.instructor_guidance}</p>
            </div>
          )}
          <p className="text-xs text-slate-400 dark:text-slate-500 italic">Awaiting instructor review before grade is published.</p>
        </div>
      )}
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────────── */
export default function StudentSubmissions() {
  const [submissions, setSubmissions] = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [expanded,    setExpanded]    = useState(null);

  const toggle = (id) => setExpanded((prev) => (prev === id ? null : id));

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        // 1. My submissions
        const subsRes = await getMySubmissions();
        const subs    = subsRes.data;

        // 2. Fetch assignment details (parallel)
        const uniqueAIds = [...new Set(subs.map((s) => s.assignment_id))];
        const asgResults = await Promise.all(
          uniqueAIds.map((id) => getAssignment(id).catch(() => null))
        );
        const asgMap = {};
        uniqueAIds.forEach((id, i) => {
          if (asgResults[i]) asgMap[id] = asgResults[i].data;
        });

        // 3. Fetch AI feedback for graded submissions (parallel)
        const gradedSubs = subs.filter((s) => s.state === "graded");
        const fbResults  = await Promise.all(
          gradedSubs.map((s) => getAIFeedback(s.id).catch(() => null))
        );
        const fbMap = {};
        gradedSubs.forEach((s, i) => {
          if (fbResults[i]) fbMap[s.id] = fbResults[i].data;
        });

        if (cancelled) return;

        const enriched = subs.map((s) => ({
          ...s,
          status:          stateToStatus(s.state),
          assignmentTitle: asgMap[s.assignment_id]?.title ?? `Assignment #${s.assignment_id}`,
          courseId:        asgMap[s.assignment_id]?.course_id ?? "—",
          aiFeedback:      fbMap[s.id] ?? null,
        }));

        setSubmissions(enriched);
      } catch (e) {
        console.error("StudentSubmissions fetch error:", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  const graded   = submissions.filter((s) => s.grade !== null || s.aiFeedback?.suggested_grade != null);
  const avgPct   = graded.length > 0
    ? Math.round(graded.reduce((sum, s) => {
        const g = s.aiFeedback?.suggested_grade ?? 0;
        return sum + (g / 100) * 100;
      }, 0) / graded.length)
    : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">My Submissions</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review all your submitted exams and grades</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Submitted", value: submissions.length, iconCls: "text-blue-600 dark:text-blue-400", bg: "bg-blue-50 dark:bg-blue-900/30", path: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" },
          { label: "AI Graded", value: submissions.filter((s) => s.status === "AI Graded").length, iconCls: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-900/30", path: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
          { label: "Average Score", value: avgPct !== null ? `${avgPct}%` : "—", iconCls: "text-indigo-600 dark:text-indigo-400", bg: "bg-indigo-50 dark:bg-indigo-900/30", path: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" },
        ].map(({ label, value, iconCls, bg, path }) => (
          <div key={label} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm px-5 py-4 flex items-center gap-4 hover:shadow-md transition-shadow">
            <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center shrink-0`}>
              <svg className={`w-5 h-5 ${iconCls}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={path} />
              </svg>
            </div>
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500 font-medium">{label}</p>
              <p className="text-xl font-extrabold text-slate-900 dark:text-white">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Cards */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">Loading submissions…</div>
        ) : submissions.length === 0 ? (
          <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">No submissions yet.</div>
        ) : (
          submissions.map((sub) => (
            <SubmissionCard
              key={sub.id}
              sub={sub}
              expanded={expanded === sub.id}
              onToggle={() => toggle(sub.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
