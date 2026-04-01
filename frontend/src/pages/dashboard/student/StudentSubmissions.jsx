import { useEffect, useMemo, useState } from "react";
import { getMySubmissions } from "../../../services/submissionService";
import {
  getAssignment,
  getCourseAssignments,
  getMyCourses,
} from "../../../services/courseService";
import { getAIFeedback } from "../../../services/gradingService";

const stateToStatus = (state) =>
  ({
    submitted: "Processing",
    processing: "Processing",
    graded: "AI Graded",
    failed: "Failed",
  })[state] ?? state;

const STATUS_CLS = {
  Processing:
    "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
  "AI Graded":
    "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-800",
  Failed:
    "bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
  "Not submitted":
    "bg-slate-50 text-slate-600 border border-slate-200 dark:bg-slate-800/40 dark:text-slate-300 dark:border-slate-700",
};

const STATUS_DOT = {
  Processing: "bg-blue-500 animate-pulse",
  "AI Graded": "bg-indigo-500",
  Failed: "bg-red-500",
  "Not submitted": "bg-slate-400",
};

function StatusBadge({ status }) {
  const cls = STATUS_CLS[status] ?? STATUS_CLS["Not submitted"];
  const dot = STATUS_DOT[status] ?? STATUS_DOT["Not submitted"];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {status}
    </span>
  );
}

function RubricBlock({ data }) {
  if (!data) return null;
  if (typeof data !== "object") {
    return (
      <pre className="text-xs bg-slate-100 dark:bg-slate-900 rounded-lg p-3 overflow-x-auto text-slate-700 dark:text-slate-300">
        {String(data)}
      </pre>
    );
  }

  const criteria = data.criteria ?? data;

  if (Array.isArray(criteria)) {
    return (
      <ul className="space-y-2">
        {criteria.map((c, idx) => {
          const name = c.criterion ?? c.name ?? `Criterion ${idx + 1}`;
          const desc = c.desc ?? c.description ?? null;
          const weight = c.weight ?? c.max ?? null;
          return (
            <li
              key={name + idx}
              className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-3 text-sm border-b border-slate-100 dark:border-slate-700/80 pb-2 last:border-0 last:pb-0"
            >
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-slate-800 dark:text-slate-200">
                  {name}
                </p>
                {desc && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 whitespace-pre-wrap">
                    {String(desc)}
                  </p>
                )}
              </div>
              {weight != null && (
                <span className="shrink-0 text-[11px] font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-0.5 rounded-md">
                  {weight} pts
                </span>
              )}
            </li>
          );
        })}
      </ul>
    );
  }

  if (typeof criteria === "object" && criteria !== null) {
    const entries = Object.entries(criteria);
    if (entries.length === 0) return null;
    return (
      <ul className="space-y-2">
        {entries.map(([name, val], idx) => {
          const description = val?.description ?? val?.desc ?? null;
          const weight = val?.weight ?? val?.max ?? null;
          return (
            <li
              key={name + idx}
              className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-3 text-sm border-b border-slate-100 dark:border-slate-700/80 pb-2 last:border-0 last:pb-0"
            >
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-slate-800 dark:text-slate-200">
                  {name}
                </p>
                {description && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 whitespace-pre-wrap">
                    {String(description)}
                  </p>
                )}
              </div>
              {weight != null && (
                <span className="shrink-0 text-[11px] font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-0.5 rounded-md">
                  {weight} pts
                </span>
              )}
            </li>
          );
        })}
      </ul>
    );
  }

  return (
    <pre className="text-xs bg-slate-100 dark:bg-slate-900 rounded-lg p-4 overflow-auto max-h-64 text-slate-700 dark:text-slate-300 font-mono leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function formatDT(dt) {
  try {
    return new Date(dt).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(dt);
  }
}

export default function StudentSubmissions() {
  const [mySubmissions, setMySubmissions] = useState([]);
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);

  const [selectedCourseId, setSelectedCourseId] = useState(null);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState(null);

  const [loading, setLoading] = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(false);

  const [aiFeedbackBySubmissionId, setAiFeedbackBySubmissionId] = useState({});
  const [loadingAI, setLoadingAI] = useState(false);

  const [expandedQuestionId, setExpandedQuestionId] = useState(null);

  const selectCourse = (courseId) => {
    setSelectedCourseId(courseId);
    setSelectedAssignmentId(null);
    setAssignments([]);
    setSelectedAssignment(null);
    setAiFeedbackBySubmissionId({});
    setExpandedQuestionId(null);
  };

  const selectAssignment = (assignmentId) => {
    setSelectedAssignmentId(assignmentId);
    setSelectedAssignment(assignments.find((a) => a.id === assignmentId) ?? null);
    setAiFeedbackBySubmissionId({});
    setExpandedQuestionId(null);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [subsRes, coursesRes] = await Promise.all([
          getMySubmissions(),
          getMyCourses(),
        ]);
        if (cancelled) return;

        setMySubmissions(subsRes.data ?? []);
        const courseList = coursesRes.data ?? [];
        setCourses(courseList);
        if (courseList.length > 0) {
          setSelectedCourseId(courseList[0].id);
        }
      } catch (e) {
        console.error("StudentSubmissions load error:", e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedCourseId) return;
    let cancelled = false;

    (async () => {
      setLoadingAssignments(true);
      try {
        const res = await getCourseAssignments(selectedCourseId);
        if (cancelled) return;
        const list = res.data ?? [];
        setAssignments(list);
        if (list.length > 0) {
          setSelectedAssignmentId(list[0].id);
          setSelectedAssignment(list[0]);
        } else {
          setSelectedAssignmentId(null);
          setSelectedAssignment(null);
              }
      } catch (e) {
        console.error("StudentSubmissions assignments error:", e);
        if (!cancelled) setAssignments([]);
      } finally {
        if (!cancelled) setLoadingAssignments(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedCourseId]);

  useEffect(() => {
    if (!selectedAssignmentId) return;
    let cancelled = false;
    (async () => {
      const maybe = assignments.find((a) => a.id === selectedAssignmentId);
      if (maybe) {
        setSelectedAssignment(maybe);
      } else {
        try {
          const asgRes = await getAssignment(selectedAssignmentId);
          if (!cancelled) setSelectedAssignment(asgRes.data ?? null);
        } catch {
          // ignore
        }
      }
    })();
    return () => { cancelled = true; };
  }, [selectedAssignmentId, assignments]);

  // Fetch AI feedback for graded submissions on this assignment
  useEffect(() => {
    if (!selectedAssignmentId) return;
    const subsForAssignment = mySubmissions.filter(
      (s) => s.assignment_id === selectedAssignmentId,
    );
    const graded = subsForAssignment.filter((s) => s.state === "graded");
    let cancelled = false;

    (async () => {
      setLoadingAI(true);
      try {
        const results = await Promise.all(
          graded.map((s) => getAIFeedback(s.id).catch(() => null)),
        );
        if (cancelled) return;
        const map = {};
        results.forEach((fb, i) => {
          if (fb) map[graded[i].id] = fb.data;
        });
        setAiFeedbackBySubmissionId(map);
      } catch (e) {
        console.error("StudentSubmissions AI feedback error:", e);
        if (!cancelled) setAiFeedbackBySubmissionId({});
      } finally {
        if (!cancelled) setLoadingAI(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedAssignmentId, mySubmissions]);

  const submissionsForAssignment = useMemo(() => {
    if (!selectedAssignmentId) return [];
    return mySubmissions.filter((s) => s.assignment_id === selectedAssignmentId);
  }, [mySubmissions, selectedAssignmentId]);

  const aiAvg = useMemo(() => {
    const subsForAssignment = selectedAssignmentId
      ? mySubmissions.filter((s) => s.assignment_id === selectedAssignmentId)
      : [];
    const graded = subsForAssignment.filter((s) => s.state === "graded");
    const vals = graded
      .map((s) => aiFeedbackBySubmissionId[s.id]?.suggested_grade)
      .filter((v) => v != null);
    if (vals.length === 0) return null;
    const avg = vals.reduce((sum, v) => sum + Number(v), 0) / vals.length;
    return Math.round(avg);
  }, [aiFeedbackBySubmissionId, mySubmissions, selectedAssignmentId]);

  const totalSubmittedForAssignment = useMemo(() => {
    if (!selectedAssignmentId) return 0;
    return mySubmissions.filter((s) => s.assignment_id === selectedAssignmentId)
      .length;
  }, [mySubmissions, selectedAssignmentId]);

  const aiGradedForAssignment = useMemo(() => {
    if (!selectedAssignmentId) return 0;
    return mySubmissions.filter(
      (s) => s.assignment_id === selectedAssignmentId && s.state === "graded",
    ).length;
  }, [mySubmissions, selectedAssignmentId]);

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            My Submissions
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Loading your assignments…
          </p>
        </div>
        <div className="text-center py-12 text-slate-400 dark:text-slate-500 text-sm">
          Loading submissions…
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          My Submissions
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Pick a course and assignment to see every question and your grading
          status.
        </p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">
              Course
            </label>
            <select
              value={selectedCourseId ?? ""}
              onChange={(e) =>
                selectCourse(e.target.value ? Number(e.target.value) : null)
              }
              className="px-3 py-2 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">
              Assignment
            </label>
            <select
              value={selectedAssignmentId ?? ""}
              onChange={(e) =>
                selectAssignment(e.target.value ? Number(e.target.value) : null)
              }
              disabled={loadingAssignments || assignments.length === 0}
              className="px-3 py-2 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
            >
              {assignments.length === 0 ? (
                <option value="">No assignments</option>
              ) : (
                assignments.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.title}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>
      </div>

      {!selectedAssignmentId ? (
        <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-12 text-center">
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Choose a course and assignment to view questions and grading status.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Rubric + mini summary */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-1">
                    {selectedAssignment ? "Assignment" : ""}
                  </p>
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                    {selectedAssignment?.title ?? ""}
                  </h2>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                    {selectedAssignment ? "Rubric & grading status" : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs font-bold text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-700 px-2 py-1 rounded-md">
                    Submitted: {totalSubmittedForAssignment}
                  </span>
                  <span className="text-xs font-bold text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-700 px-2 py-1 rounded-md">
                    AI Graded: {aiGradedForAssignment}
                  </span>
                  {aiAvg != null && (
                    <span className="text-xs font-bold text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-700 px-2 py-1 rounded-md">
                      Avg AI: {aiAvg}/100
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="px-6 py-5 space-y-4">
              {selectedAssignment?.rubric_json ? (
                <div>
                  <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
                    Rubric
                  </h3>
                  <RubricBlock data={selectedAssignment.rubric_json} />
                </div>
              ) : null}
            </div>
          </div>

          {/* Submissions */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-6">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">
              My Submissions ({submissionsForAssignment.length})
            </h3>

            {submissionsForAssignment.length === 0 ? (
              <div className="text-center py-10 text-slate-400 dark:text-slate-500 text-sm">
                No submissions yet for this assignment.
              </div>
            ) : (
              <ol className="space-y-4">
                {submissionsForAssignment.map((sub, idx) => {
                  const status = stateToStatus(sub.state);
                  const aiFb = aiFeedbackBySubmissionId[sub.id] ?? null;
                  const grade = aiFb?.suggested_grade != null ? Math.round(aiFb.suggested_grade) : null;
                  const expanded = expandedQuestionId === sub.id;
                  const canExpand = Boolean(aiFb);

                  return (
                    <li key={sub.id} className="rounded-xl border border-slate-100 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-900/40 p-4">
                      <div className="flex items-start gap-3">
                        <span className="shrink-0 w-8 h-8 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 flex items-center justify-center text-sm font-bold text-slate-600 dark:text-slate-300">
                          {idx + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs text-slate-400 dark:text-slate-500 flex flex-wrap items-center gap-x-3 gap-y-1">
                            <StatusBadge status={status} />
                            <span>Submitted {formatDT(sub.submitted_at)}</span>
                            {grade != null && (
                              <span className="font-semibold text-slate-700 dark:text-slate-200">
                                AI grade: {grade}/100
                              </span>
                            )}
                            {loadingAI && sub.state === "graded" && (
                              <span className="text-slate-500">Loading AI…</span>
                            )}
                          </p>
                        </div>
                      </div>

                      {aiFb && expanded && (
                        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700 space-y-3">
                          {aiFb.student_feedback && (
                            <div>
                              <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-1">AI Feedback</p>
                              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{aiFb.student_feedback}</p>
                            </div>
                          )}
                          <p className="text-xs text-slate-400 dark:text-slate-500 italic">
                            Awaiting instructor review before grade is published.
                          </p>
                        </div>
                      )}

                      {canExpand && (
                        <div className="mt-3">
                          <button
                            type="button"
                            onClick={() => setExpandedQuestionId(expanded ? null : sub.id)}
                            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                          >
                            {expanded ? "Hide" : "View AI grading"}
                          </button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
