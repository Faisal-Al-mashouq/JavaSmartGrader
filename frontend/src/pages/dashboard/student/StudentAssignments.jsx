import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { submitAnswer } from "../../../services/submissionService";
import {
  getAssignmentQuestions,
  getCourseAssignments,
  getMyCourses,
} from "../../../services/courseService";

function formatDue(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString("en-US", {
      weekday: "short",
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

export default function StudentAssignments() {
  const [rows, setRows] = useState([]); // { course, assignment }[]
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [selectedKey, setSelectedKey] = useState(null); // `${courseId}:${assignmentId}`
  const [questionsCache, setQuestionsCache] = useState({}); // assignmentId -> questions[]
  const [loadingQuestions, setLoadingQuestions] = useState(false);

  const [query, setQuery] = useState("");

  const selected = useMemo(() => {
    if (!selectedKey) return null;
    const [cid, aid] = selectedKey.split(":").map(Number);
    return (
      rows.find((r) => r.course.id === cid && r.assignment.id === aid) ?? null
    );
  }, [rows, selectedKey]);

  const questions = selected
    ? (questionsCache[selected.assignment.id] ?? [])
    : [];

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setLoadError("");
      try {
        const coursesRes = await getMyCourses();
        const courses = coursesRes.data ?? [];
        const pairs = await Promise.all(
          courses.map(async (course) => {
            try {
              const asgRes = await getCourseAssignments(course.id);
              return (asgRes.data ?? []).map((assignment) => ({
                course,
                assignment,
              }));
            } catch {
              return [];
            }
          }),
        );
        if (cancelled) return;
        const flat = pairs.flat();
        flat.sort((a, b) => {
          const c = a.course.name.localeCompare(b.course.name);
          if (c !== 0) return c;
          return a.assignment.title.localeCompare(b.assignment.title);
        });
        setRows(flat);
      } catch (e) {
        console.error(e);
        if (!cancelled)
          setLoadError("Could not load your courses or assignments.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function ensureQuestions(assignmentId) {
    if (questionsCache[assignmentId]) return;
    setLoadingQuestions(true);
    try {
      const res = await getAssignmentQuestions(assignmentId);
      setQuestionsCache((prev) => ({
        ...prev,
        [assignmentId]: res.data ?? [],
      }));
    } catch {
      setQuestionsCache((prev) => ({ ...prev, [assignmentId]: [] }));
    } finally {
      setLoadingQuestions(false);
    }
  }

  const selectRow = async (course, assignment) => {
    const key = `${course.id}:${assignment.id}`;
    setSelectedKey(key);
    await ensureQuestions(assignment.id);
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.assignment.title.toLowerCase().includes(q) ||
        r.course.name.toLowerCase().includes(q),
    );
  }, [rows, query]);

  const grouped = useMemo(() => {
    const map = new Map();
    for (const r of filtered) {
      const id = r.course.id;
      if (!map.has(id)) map.set(id, { course: r.course, items: [] });
      map.get(id).items.push(r);
    }
    return [...map.values()];
  }, [filtered]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Assignments
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm max-w-2xl">
          Open a course assignment to read instructions and submit your work for
          each question. Everything is organized by the course you are enrolled
          in.
        </p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-4 sm:p-5">
        <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-2">
          Search
        </label>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by assignment or course name…"
          className="w-full px-3 py-2 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-5 space-y-4">
          <h2 className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide px-1">
            Your courses
          </h2>
          {loading ? (
            <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-10 text-center text-slate-400 text-sm">
              Loading…
            </div>
          ) : loadError ? (
            <div className="rounded-2xl border border-red-200 dark:border-red-900/50 bg-red-50/50 dark:bg-red-900/10 p-6 text-sm text-red-700 dark:text-red-400">
              {loadError}
            </div>
          ) : grouped.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-10 text-center space-y-2">
              <p className="text-slate-600 dark:text-slate-300 text-sm font-medium">
                No assignments yet
              </p>
              <p className="text-slate-400 dark:text-slate-500 text-xs">
                When your instructor enrolls you in a course, assignments for
                that course will show up here.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {grouped.map(({ course, items }) => (
                <div key={course.id}>
                  <p className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-2 px-1">
                    {course.name}
                  </p>
                  <ul className="space-y-2">
                    {items.map(({ assignment }) => {
                      const key = `${course.id}:${assignment.id}`;
                      const active = selectedKey === key;
                      const overdue = isOverdue(assignment.due_date);
                      return (
                        <li key={key}>
                          <button
                            type="button"
                            onClick={() => selectRow(course, assignment)}
                            className={`w-full text-left rounded-2xl border px-4 py-3.5 transition-all duration-150 ${
                              active
                                ? "border-blue-500 bg-blue-50/80 dark:bg-blue-950/40 ring-1 ring-blue-500/30"
                                : "border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-slate-200 dark:hover:border-slate-600"
                            }`}
                          >
                            <p className="text-sm font-bold text-slate-900 dark:text-white">
                              {assignment.title}
                            </p>
                            <div className="flex flex-wrap items-center gap-2 mt-2">
                              {assignment.due_date && (
                                <span
                                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${
                                    overdue
                                      ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                                      : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                                  }`}
                                >
                                  Due {formatDue(assignment.due_date)}
                                </span>
                              )}
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-7">
          {!selected ? (
            <div className="rounded-2xl border border-dashed border-slate-200 dark:border-slate-600 p-12 text-center">
              <p className="text-slate-500 dark:text-slate-400 text-sm">
                Choose an assignment on the left to view instructions, rubric,
                and submit your answers.
              </p>
            </div>
          ) : (
            <AssignmentPanel
              course={selected.course}
              assignment={selected.assignment}
              questions={questions}
              loadingQuestions={loadingQuestions}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function AssignmentPanel({
  course,
  assignment: a,
  questions,
  loadingQuestions,
}) {
  const overdue = isOverdue(a.due_date);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-hidden">
      <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30">
        <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-1">
          {course.name}
        </p>
        <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          {a.title}
        </h2>
        {a.due_date && (
          <p
            className={`text-sm mt-3 font-medium ${
              overdue
                ? "text-amber-700 dark:text-amber-400"
                : "text-slate-600 dark:text-slate-300"
            }`}
          >
            Due: {formatDue(a.due_date)}
            {overdue && (
              <span className="ml-2 text-xs font-bold uppercase tracking-wide text-amber-600 dark:text-amber-500">
                Past due
              </span>
            )}
          </p>
        )}
      </div>

      <div className="px-6 py-5 space-y-6">
        {a.description ? (
          <section>
            <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
              Instructions
            </h3>
            <div className="text-sm leading-relaxed text-slate-700 dark:text-slate-200 whitespace-pre-wrap">
              {a.description}
            </div>
          </section>
        ) : null}

        {a.rubric_json && Object.keys(a.rubric_json).length > 0 ? (
          <section>
            <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
              Rubric
            </h3>
            <RubricBlock data={a.rubric_json} />
          </section>
        ) : null}

        <section>
          <h3 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-3">
            Questions
          </h3>
          {loadingQuestions ? (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              Loading questions…
            </p>
          ) : questions.length === 0 ? (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              No questions have been published for this assignment yet.
            </p>
          ) : (
            <ol className="space-y-6">
              {questions.map((q, index) => (
                <li
                  key={`${q.assignment_id}-${q.id}`}
                  className="rounded-xl border border-slate-100 dark:border-slate-600 bg-slate-50/80 dark:bg-slate-900/40 p-4"
                >
                  <div className="flex items-start gap-3 mb-3">
                    <span className="shrink-0 w-9 h-9 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 flex items-center justify-center text-sm font-bold text-slate-600 dark:text-slate-300">
                      {index + 1}
                    </span>
                    <p className="text-sm text-slate-800 dark:text-slate-100 leading-relaxed whitespace-pre-wrap flex-1 pt-1">
                      {q.question_text}
                    </p>
                  </div>
                  <QuestionSubmit assignmentId={a.id} questionId={q.id} />
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}

function QuestionSubmit({ assignmentId, questionId }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [stage, setStage] = useState("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleFile = (f) => {
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      setErrorMsg("Only image files are allowed.");
      setStage("error");
      return;
    }
    if (preview) URL.revokeObjectURL(preview);
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setStage("idle");
    setErrorMsg("");
  };

  const clearFile = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setStage("idle");
    setErrorMsg("");
  };

  const handleSubmit = async () => {
    if (!file) {
      setErrorMsg("Choose an image of your answer first.");
      setStage("error");
      return;
    }
    setStage("submitting");
    setErrorMsg("");
    try {
      await submitAnswer(questionId, assignmentId);
      setStage("done");
    } catch (err) {
      setErrorMsg(
        err.response?.data?.detail ?? "Submission failed. Try again.",
      );
      setStage("error");
    }
  };

  if (stage === "done") {
    return (
      <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50/80 dark:bg-emerald-950/30 px-4 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-start gap-2">
          <svg
            className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-200">
              Submitted — your answer is being graded
            </p>
            <p className="text-xs text-emerald-700/90 dark:text-emerald-400/90 mt-0.5">
              You can track status under{" "}
              <Link
                to="/dashboard/submissions"
                className="font-semibold underline underline-offset-2"
              >
                Submissions
              </Link>
              .
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            clearFile();
            setStage("idle");
          }}
          className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 hover:underline self-start sm:self-center"
        >
          Submit another image
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3 pl-0 sm:pl-12">
      <div
        className={`rounded-xl border-2 border-dashed flex flex-col items-center justify-center text-center transition-colors cursor-pointer ${
          file
            ? "border-slate-200 dark:border-slate-600 p-3"
            : "border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 p-6"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
        }}
        onDrop={(e) => {
          e.preventDefault();
          handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() =>
          !file &&
          document.getElementById(`file-${assignmentId}-${questionId}`)?.click()
        }
      >
        <input
          id={`file-${assignmentId}-${questionId}`}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {preview ? (
          <div className="w-full">
            <img
              src={preview}
              alt=""
              className="max-h-48 mx-auto rounded-lg object-contain"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 truncate max-w-full">
              {file?.name} · {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Drop an image here or click to browse
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
              PNG, JPG, JPEG
            </p>
          </>
        )}
      </div>

      {file && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              clearFile();
            }}
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Remove
          </button>
          <button
            type="button"
            onClick={() =>
              document
                .getElementById(`file-${assignmentId}-${questionId}`)
                ?.click()
            }
            className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Change image
          </button>
          <button
            type="button"
            disabled={stage === "submitting"}
            onClick={handleSubmit}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-bold shadow-sm"
          >
            {stage === "submitting" ? "Submitting…" : "Submit answer"}
          </button>
        </div>
      )}

      {stage === "error" && errorMsg && (
        <p className="text-xs text-red-600 dark:text-red-400 font-medium">
          {errorMsg}
        </p>
      )}
    </div>
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

  // Your backend rubric defaults to: { criteria: { CriterionName: { weight, description } } }
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
          const hasNested =
            val &&
            typeof val === "object" &&
            val.weight == null &&
            val.description == null &&
            val.desc == null &&
            val.max == null;

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
                {hasNested && (
                  <pre className="text-[11px] bg-slate-50 dark:bg-slate-900/30 rounded-md p-2 overflow-x-auto text-slate-600 dark:text-slate-300 mt-2 border border-slate-100 dark:border-slate-700 font-mono leading-relaxed">
                    {JSON.stringify(val, null, 2)}
                  </pre>
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
