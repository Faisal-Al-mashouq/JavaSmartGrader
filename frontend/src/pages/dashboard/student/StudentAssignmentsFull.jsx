import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  getAssignmentQuestions,
  getCourseAssignments,
  getMyCourses,
} from "../../../services/courseService";

function formatDue(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return String(iso);
  }
}

function isOverdue(iso) {
  if (!iso) return false;
  return new Date(iso) < new Date();
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

  // Backend default rubric shape: { criteria: { CriterionName: { weight, description } } }
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

function QuestionCard({ question, index, onUpload }) {
  return (
    <li className="rounded-xl border border-slate-100 dark:border-slate-600 bg-slate-50/80 dark:bg-slate-900/40 p-4">
      <div className="flex items-start gap-3 mb-3">
        <span className="shrink-0 w-9 h-9 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 flex items-center justify-center text-sm font-bold text-slate-600 dark:text-slate-300">
          {index + 1}
        </span>
        <p className="text-sm text-slate-800 dark:text-slate-100 leading-relaxed whitespace-pre-wrap flex-1">
          {question.question_text}
        </p>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <button
          type="button"
          onClick={() => onUpload(question.id)}
          className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all active:scale-[0.98]"
        >
          Upload answer
        </button>
      </div>
    </li>
  );
}

export default function StudentAssignmentsFull() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const courseIdParam = searchParams.get("course");

  const courseId = courseIdParam ? parseInt(courseIdParam, 10) : null;

  const [courses, setCourses] = useState([]);
  const [coursesLoading, setCoursesLoading] = useState(true);
  const [courseError, setCourseError] = useState("");

  const courseName = useMemo(() => {
    const c = courses.find((x) => x.id === courseId);
    return c?.name ?? "";
  }, [courses, courseId]);

  const [assignments, setAssignments] = useState([]);
  const [assignmentsLoading, setAssignmentsLoading] = useState(false);
  const [assignmentsError, setAssignmentsError] = useState("");

  const [selectedAssignmentId, setSelectedAssignmentId] = useState(null);
  const selectedAssignment = useMemo(
    () => assignments.find((a) => a.id === selectedAssignmentId) ?? null,
    [assignments, selectedAssignmentId],
  );

  const [questionsCache, setQuestionsCache] = useState({}); // assignmentId -> questions
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const questions = selectedAssignment
    ? (questionsCache[selectedAssignment.id] ?? [])
    : [];

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setCoursesLoading(true);
        setCourseError("");
        const res = await getMyCourses();
        if (!cancelled) setCourses(res.data ?? []);
      } catch (e) {
        console.error("StudentAssignmentsFull courses error:", e);
        if (!cancelled) setCourseError("Could not load your courses.");
      } finally {
        if (!cancelled) setCoursesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!courseId) return;
    let cancelled = false;

    (async () => {
      try {
        setAssignmentsLoading(true);
        setAssignmentsError("");
        const res = await getCourseAssignments(courseId);
        if (cancelled) return;
        const list = res.data ?? [];
        setAssignments(list);
        const first = list[0]?.id ?? null;
        setSelectedAssignmentId(first);
        setQuestionsCache({});
      } catch (e) {
        console.error("StudentAssignmentsFull assignments error:", e);
        if (!cancelled)
          setAssignmentsError("Could not load assignments for this course.");
      } finally {
        if (!cancelled) setAssignmentsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [courseId]);

  useEffect(() => {
    if (!selectedAssignmentId) return;
    if (questionsCache[selectedAssignmentId]) return;
    let cancelled = false;

    (async () => {
      try {
        setLoadingQuestions(true);
        const res = await getAssignmentQuestions(selectedAssignmentId);
        if (cancelled) return;
        setQuestionsCache((prev) => ({
          ...prev,
          [selectedAssignmentId]: res.data ?? [],
        }));
      } catch (e) {
        console.error("StudentAssignmentsFull questions error:", e);
        if (!cancelled)
          setQuestionsCache((prev) => ({
            ...prev,
            [selectedAssignmentId]: [],
          }));
      } finally {
        if (!cancelled) setLoadingQuestions(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedAssignmentId, questionsCache]);

  const upload = (assignmentId, questionId) => {
    navigate("/dashboard/upload", {
      state: { assignmentId, questionId },
    });
  };

  if (!courseId) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Assignments
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            Choose a course first.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/dashboard/courses")}
          className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold shadow-sm transition-all active:scale-[0.98]"
        >
          Go to courses
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Assignments
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            {coursesLoading ? "Loading course…" : courseName}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => navigate("/dashboard/courses")}
            className="px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            Change course
          </button>
        </div>
      </div>

      {courseError ? (
        <div className="rounded-2xl border border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-900/10 p-6 text-sm text-red-700 dark:text-red-400">
          {courseError}
        </div>
      ) : assignmentsError ? (
        <div className="rounded-2xl border border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-900/10 p-6 text-sm text-red-700 dark:text-red-400">
          {assignmentsError}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className="lg:col-span-5 space-y-3">
            <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide px-1">
              Assignment list
            </h2>

            {assignmentsLoading ? (
              <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-10 text-center text-slate-400 text-sm">
                Loading…
              </div>
            ) : assignments.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-10 text-center text-slate-400 text-sm">
                No assignments available for this course.
              </div>
            ) : (
              <ul className="space-y-2">
                {assignments.map((a) => {
                  const active = a.id === selectedAssignmentId;
                  const overdue = isOverdue(a.due_date);
                  return (
                    <li key={a.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedAssignmentId(a.id)}
                        className={`w-full text-left rounded-2xl border px-4 py-3.5 transition-all duration-150 ${
                          active
                            ? "border-blue-500 bg-blue-50/80 dark:bg-blue-950/40 ring-1 ring-blue-500/30"
                            : "border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-slate-200 dark:hover:border-slate-600"
                        }`}
                      >
                        <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
                          {a.title}
                        </p>
                        {a.due_date ? (
                          <div className="flex flex-wrap items-center gap-2 mt-2">
                            <span
                              className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${
                                overdue
                                  ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                                  : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                              }`}
                            >
                              Due {formatDue(a.due_date)}
                            </span>
                          </div>
                        ) : null}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="lg:col-span-7">
            {!selectedAssignment ? (
              <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-12 text-center">
                <p className="text-slate-500 dark:text-slate-400 text-sm">
                  Select an assignment to view questions and submit answers.
                </p>
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-hidden">
                <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30">
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                    {selectedAssignment.title}
                  </h2>
                  {selectedAssignment.due_date ? (
                    <p
                      className={`text-sm mt-3 font-medium ${
                        isOverdue(selectedAssignment.due_date)
                          ? "text-amber-700 dark:text-amber-400"
                          : "text-slate-600 dark:text-slate-300"
                      }`}
                    >
                      Due: {formatDue(selectedAssignment.due_date)}
                    </p>
                  ) : null}
                </div>

                <div className="px-6 py-5 space-y-6">
                  {selectedAssignment.description ? (
                    <section>
                      <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
                        Instructions
                      </h3>
                      <div className="text-sm leading-relaxed text-slate-700 dark:text-slate-200 whitespace-pre-wrap">
                        {selectedAssignment.description}
                      </div>
                    </section>
                  ) : null}

                  {selectedAssignment.rubric_json &&
                  Object.keys(selectedAssignment.rubric_json).length > 0 ? (
                    <section>
                      <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
                        Rubric
                      </h3>
                      <RubricBlock data={selectedAssignment.rubric_json} />
                    </section>
                  ) : null}

                  <section>
                    <div className="flex items-center justify-between gap-4 mb-3">
                      <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide">
                        Questions
                      </h3>
                      <span className="text-xs font-medium text-slate-400 dark:text-slate-500">
                        {loadingQuestions ? "Loading…" : questions.length}
                      </span>
                    </div>

                    {loadingQuestions ? (
                      <div className="text-sm text-slate-400 dark:text-slate-500">
                        Loading questions…
                      </div>
                    ) : questions.length === 0 ? (
                      <div className="text-sm text-slate-400 dark:text-slate-500">
                        No questions found for this assignment.
                      </div>
                    ) : (
                      <ol className="space-y-4">
                        {questions.map((q, idx) => (
                          <QuestionCard
                            key={`${q.id}`}
                            question={q}
                            index={idx}
                            onUpload={(qid) =>
                              upload(selectedAssignment.id, qid)
                            }
                          />
                        ))}
                      </ol>
                    )}
                  </section>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
