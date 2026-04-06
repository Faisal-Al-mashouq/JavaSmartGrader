import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { getAssignment } from "../../../services/courseService";

const CARDS = [
  {
    key: "questions",
    title: "Questions",
    desc: "Manage the questions students will answer for this assignment.",
    accent: "from-blue-500 to-cyan-500",
    icon: (
      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    key: "rubric",
    title: "Grading Rubric",
    desc: "Configure criteria weights for Correctness, Efficiency, Edge Cases, and Code Quality.",
    accent: "from-indigo-500 to-violet-500",
    icon: (
      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ),
  },
  {
    key: "submissions",
    title: "Submissions",
    desc: "Everything students have handed in for this assignment.",
    accent: "from-emerald-500 to-teal-500",
    icon: (
      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

export default function InstructorAssignmentDetail() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);
  const [assignment, setAssignment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!Number.isFinite(cid) || !Number.isFinite(aid)) return;
    let cancelled = false;
    (async () => {
      try {
        const aRes = await getAssignment(aid);
        if (cancelled) return;
        if (aRes.data.course_id !== cid) {
          setError("This assignment does not belong to the selected course.");
          return;
        }
        setAssignment(aRes.data);
      } catch (e) {
        if (!cancelled)
          setError(e.response?.data?.detail ?? "Could not load assignment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [cid, aid]);

  if (!Number.isFinite(cid) || !Number.isFinite(aid)) {
    return <p className="text-red-600 text-sm">Invalid link.</p>;
  }

  return (
    <div className="max-w-6xl space-y-8">
      {loading ? (
        <p className="text-slate-500 text-sm">Loading…</p>
      ) : error ? (
        <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
      ) : assignment ? (
        <>
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">Assignment</p>
              <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                {assignment.title}
              </h1>
              {assignment.description && (
                <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm leading-relaxed max-w-2xl">
                  {assignment.description}
                </p>
              )}
              {assignment.due_date && (
                <p className="text-xs text-slate-400 mt-1">
                  Due {new Date(assignment.due_date).toLocaleString()}
                </p>
              )}
            </div>
            <InstructorNavButton to={`/instructor/courses/${cid}/assignments`} variant="primary">
              ← Assignments
            </InstructorNavButton>
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            {CARDS.map(({ key, title, desc, accent, icon }) => (
              <Link
                key={key}
                to={`/instructor/courses/${cid}/assignments/${aid}/${key}`}
                className="relative group block bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] hover:border-slate-300 dark:hover:border-white/[0.18] shadow-sm hover:shadow-md dark:shadow-lg dark:hover:shadow-xl p-6 transition-all duration-300 overflow-hidden focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <div className={`absolute -top-6 -right-6 w-24 h-24 rounded-full bg-gradient-to-br ${accent} opacity-[0.08] dark:opacity-[0.1] blur-2xl group-hover:opacity-[0.16] dark:group-hover:opacity-[0.2] transition-opacity duration-300`} />
                <div className={`relative w-12 h-12 rounded-xl bg-gradient-to-br ${accent} flex items-center justify-center shadow-md mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  {icon}
                </div>
                <h2 className={`relative text-base font-bold text-slate-900 dark:text-white group-hover:bg-gradient-to-r group-hover:${accent} group-hover:bg-clip-text group-hover:text-transparent transition-all`}>
                  {title}
                </h2>
                <p className="relative text-sm text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                  {desc}
                </p>
              </Link>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
