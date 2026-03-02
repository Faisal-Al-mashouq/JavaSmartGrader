import { useState } from "react";
import { useSubmissions } from "../../../context/SubmissionsContext";

/* ── Static historical submissions ─────────────────────────────────── */
const STATIC = [
  { id: "s1", name: "Midterm Exam - OOP Concepts",    course: "CS201", courseFull: "Object Oriented Programming", submittedAt: "Nov 30, 2024 · 11:42 AM", status: "Published", grade: 87, maxGrade: 100, feedback: "Great understanding of encapsulation and polymorphism." },
  { id: "s2", name: "Lab Assignment 3 - Inheritance", course: "CS201", courseFull: "Object Oriented Programming", submittedAt: "Dec 4, 2024 · 09:15 PM",  status: "Pending Review", grade: null, maxGrade: 100, feedback: null },
  { id: "s3", name: "Quiz 2 - Exception Handling",    course: "CS201", courseFull: "Object Oriented Programming", submittedAt: "Dec 7, 2024 · 02:30 PM",  status: "Processing",     grade: null, maxGrade: 50,  feedback: null },
  { id: "s4", name: "Assignment 2 - Data Structures", course: "CS301", courseFull: "Algorithms",                 submittedAt: "Dec 9, 2024 · 10:00 AM",  status: "Published", grade: 92, maxGrade: 100, feedback: "Excellent implementation of tree traversal algorithms." },
  { id: "s5", name: "Practical Exam 1",               course: "CS150", courseFull: "Introduction to Programming", submittedAt: "Nov 27, 2024 · 03:45 PM", status: "Published", grade: 78, maxGrade: 100, feedback: "Good work, but review loop conditions." },
];

/* ── Helpers ────────────────────────────────────────────────────────── */
const STATUS_CLS = {
  Published:       "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800",
  "Pending Review":"bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800",
  Processing:      "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  "AI Graded":     "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
};
const STATUS_DOT = {
  Published: "bg-emerald-500", "Pending Review": "bg-amber-500",
  Processing: "bg-blue-500",   "AI Graded": "bg-indigo-500",
};

function StatusBadge({ status }) {
  const cls = STATUS_CLS[status] ?? "bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-700 dark:text-slate-400 dark:border-slate-600";
  const dot = STATUS_DOT[status] ?? "bg-slate-400";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot} ${status === "Processing" ? "animate-pulse" : ""}`} />
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

/* ── Dynamic submission card (from context) ─────────────────────────── */
function DynamicCard({ sub, expanded, onToggle }) {
  const result = sub.aiResult;
  const isAI   = sub.status === "AI Graded";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
      <div className="px-6 py-4 flex items-center gap-4">

        {/* Grade circle or processing spinner */}
        <div className="shrink-0">
          {isAI && result ? (
            <GradeCircle grade={result.total} max={result.max} />
          ) : (
            <div className="w-14 h-14 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
              <svg className="w-6 h-6 text-slate-300 dark:text-slate-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{sub.assignment}</p>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-md">{sub.course}</span>
                <span className="text-xs text-slate-400 dark:text-slate-500">{sub.courseFull}</span>
              </div>
            </div>
            <StatusBadge status={sub.status} />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs text-slate-400 dark:text-slate-500">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Submitted {sub.submittedAt}
            {sub.filename && <span className="ml-2 italic">· {sub.filename}</span>}
          </div>
        </div>

        {/* Expand AI results */}
        {isAI && result && (
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

      {/* AI grading breakdown */}
      {isAI && result && expanded && (
        <div className="px-6 pb-5 border-t border-slate-100 dark:border-slate-700 pt-4 bg-slate-50 dark:bg-slate-900/40 space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">AI Rubric Breakdown</p>
              <div className="space-y-2">
                {result.rubric.map((r) => {
                  const pct = Math.round((r.score / r.max) * 100);
                  const bar = pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-blue-500" : "bg-amber-500";
                  return (
                    <div key={r.criterion}>
                      <div className="flex justify-between text-xs mb-0.5">
                        <span className="text-slate-600 dark:text-slate-300 font-medium">{r.criterion}</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200">{r.score}/{r.max}</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="shrink-0 text-center">
              <div className={`w-20 h-20 rounded-full flex flex-col items-center justify-center border-4 ${result.total >= 70 ? "border-emerald-400 dark:border-emerald-600" : "border-amber-400 dark:border-amber-600"}`}>
                <span className={`text-2xl font-extrabold ${result.total >= 70 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>{result.total}</span>
                <span className="text-xs text-slate-400 dark:text-slate-500">/{result.max}</span>
              </div>
              <p className={`text-xs font-bold mt-1 ${result.total >= 70 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>{result.verdict}</p>
            </div>
          </div>
          <div>
            <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">AI Feedback</p>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{result.feedback}</p>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 italic">Awaiting instructor review before grade is published.</p>
        </div>
      )}
    </div>
  );
}

/* ── Static submission card ─────────────────────────────────────────── */
function StaticCard({ s, expanded, onToggle }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
      <div className="px-6 py-4 flex items-center gap-4">
        <div className="shrink-0">
          {s.grade !== null ? (
            <GradeCircle grade={s.grade} max={s.maxGrade} />
          ) : (
            <div className="w-14 h-14 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
              <svg className="w-6 h-6 text-slate-300 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">{s.name}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-md">{s.course}</span>
                <span className="text-xs text-slate-400 dark:text-slate-500">{s.courseFull}</span>
              </div>
            </div>
            <StatusBadge status={s.status} />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs text-slate-400 dark:text-slate-500">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Submitted {s.submittedAt}
          </div>
        </div>
        {s.feedback && (
          <button onClick={onToggle} className="shrink-0 flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 px-3 py-1.5 rounded-lg transition-colors">
            Feedback
            <svg className={`w-4 h-4 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>
      {s.feedback && expanded && (
        <div className="px-6 pb-4 pt-4 border-t border-slate-100 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
          <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">Instructor Feedback</p>
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{s.feedback}</p>
        </div>
      )}
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────────────── */
export default function StudentSubmissions() {
  const { submissions } = useSubmissions();
  const [expanded, setExpanded] = useState(null);
  const toggle = (id) => setExpanded((prev) => (prev === id ? null : id));

  const graded = STATIC.filter((s) => s.grade !== null);
  const dynGraded = submissions.filter((s) => s.status === "AI Graded" || s.status === "Published");
  const avgPct = graded.length > 0
    ? Math.round(graded.reduce((sum, s) => sum + (s.grade / s.maxGrade) * 100, 0) / graded.length)
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
          { label: "Total Submitted", value: STATIC.length + submissions.length, iconCls: "text-blue-600 dark:text-blue-400",    bg: "bg-blue-50 dark:bg-blue-900/30",    path: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" },
          { label: "Graded",          value: graded.length + dynGraded.length,    iconCls: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-50 dark:bg-emerald-900/30", path: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
          { label: "Average Score",   value: avgPct !== null ? `${avgPct}%` : "—", iconCls: "text-indigo-600 dark:text-indigo-400",  bg: "bg-indigo-50 dark:bg-indigo-900/30",  path: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" },
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

      {/* Dynamic submissions (from upload) */}
      {submissions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block" />
            Recently Submitted
          </h2>
          {submissions.map((sub) => (
            <DynamicCard
              key={sub.id}
              sub={sub}
              expanded={expanded === sub.id}
              onToggle={() => toggle(sub.id)}
            />
          ))}
        </div>
      )}

      {/* Static submissions */}
      <div className="space-y-3">
        {submissions.length > 0 && (
          <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />
            Previous Submissions
          </h2>
        )}
        {STATIC.map((s) => (
          <StaticCard
            key={s.id}
            s={s}
            expanded={expanded === s.id}
            onToggle={() => toggle(s.id)}
          />
        ))}
      </div>
    </div>
  );
}
