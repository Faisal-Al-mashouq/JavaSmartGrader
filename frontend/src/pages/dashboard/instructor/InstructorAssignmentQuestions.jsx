import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import {
  getAssignment,
  getAssignmentQuestions,
  createQuestion,
  deleteQuestion,
  getQuestionTestcases,
  addTestcase,
  deleteTestcase,
} from "../../../services/courseService";

export default function InstructorAssignmentQuestions() {
  const { courseId, assignmentId } = useParams();
  const cid = Number(courseId);
  const aid = Number(assignmentId);
  const [assignment, setAssignment] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [testcasesByQ, setTestcasesByQ] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newPrompt, setNewPrompt] = useState("");
  const [savingQ, setSavingQ] = useState(false);
  const [tcDraft, setTcDraft] = useState({});
  const [showAdd, setShowAdd] = useState(false);

  const loadAll = useCallback(async () => {
    const [aRes, qRes] = await Promise.all([
      getAssignment(aid),
      getAssignmentQuestions(aid),
    ]);
    if (aRes.data.course_id !== cid) {
      throw new Error("Assignment does not match this course.");
    }
    setAssignment(aRes.data);
    const qs = qRes.data;
    setQuestions(qs);
    const tcEntries = await Promise.all(
      qs.map(async (q) => {
        const r = await getQuestionTestcases(aid, q.id);
        return [q.id, r.data];
      }),
    );
    setTestcasesByQ(Object.fromEntries(tcEntries));
  }, [cid, aid]);

  useEffect(() => {
    if (!Number.isFinite(cid) || !Number.isFinite(aid)) return;
    let cancelled = false;
    (async () => {
      try {
        await loadAll();
      } catch (e) {
        if (!cancelled) {
          const msg =
            e?.response?.data?.detail ??
            e?.message ??
            "Could not load questions.";
          setError(msg);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cid, aid, loadAll]);

  const handleAddQuestion = async (e) => {
    e.preventDefault();
    if (!newPrompt.trim()) return;
    setSavingQ(true);
    setError("");
    try {
      await createQuestion(aid, newPrompt.trim());
      setNewPrompt("");
      setShowAdd(false);
      await loadAll();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not add question.");
    } finally {
      setSavingQ(false);
    }
  };

  const handleDeleteQuestion = async (qid) => {
    if (!window.confirm("Delete this question and its test cases?")) return;
    setError("");
    try {
      await deleteQuestion(aid, qid);
      await loadAll();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not delete.");
    }
  };

  const handleAddTc = async (qid) => {
    const d = tcDraft[qid] || { in: "", out: "" };
    setError("");
    try {
      await addTestcase(aid, qid, d.in ?? "", d.out ?? "");
      setTcDraft((prev) => ({ ...prev, [qid]: { in: "", out: "" } }));
      await loadAll();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not add test case.");
    }
  };

  const handleDeleteTc = async (qid, tcid) => {
    setError("");
    try {
      await deleteTestcase(aid, qid, tcid);
      await loadAll();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not delete test case.");
    }
  };

  if (!Number.isFinite(cid) || !Number.isFinite(aid)) {
    return <p className="text-red-600 text-sm">Invalid link.</p>;
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">
      <div className="flex-1 min-w-0 space-y-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Questions
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
            {assignment?.title ? `For “${assignment.title}”. ` : ""}
            Each item can include several test cases (input and expected
            output).
          </p>
        </div>

        <div className="flex flex-wrap gap-2 items-center">
          <InstructorNavButton
            to={`/instructor/courses/${cid}/assignments/${aid}`}
            variant="primary"
          >
            ← Assignment
          </InstructorNavButton>
        </div>

        {error && (
          <p className="text-sm text-amber-600 dark:text-amber-400">{error}</p>
        )}

        {loading ? (
          <p className="text-slate-500 text-sm">Loading…</p>
        ) : questions.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400 py-4">
            No questions yet. Use{" "}
            <strong className="font-medium text-slate-600 dark:text-slate-300">
              + Add question
            </strong>{" "}
            on the right.
          </p>
        ) : (
          <div className="space-y-4">
            {questions.map((q, idx) => (
              <div
                key={q.id}
                className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden"
              >
                <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400">
                      Question {idx + 1}
                    </span>
                    <p className="text-sm text-slate-800 dark:text-slate-200 mt-1 whitespace-pre-wrap leading-relaxed">
                      {q.question_text}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteQuestion(q.id)}
                    className="text-xs font-medium text-red-600 dark:text-red-400 hover:underline shrink-0"
                  >
                    Delete
                  </button>
                </div>

                <div className="px-5 py-4 space-y-3 bg-slate-50/80 dark:bg-slate-900/40">
                  <p className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    Test cases
                  </p>
                  {(testcasesByQ[q.id] ?? []).length === 0 ? (
                    <p className="text-xs text-slate-500">No test cases yet.</p>
                  ) : (
                    <ul className="space-y-2">
                      {(testcasesByQ[q.id] ?? []).map((tc) => (
                        <li
                          key={tc.id}
                          className="text-xs font-mono bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-lg p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-2"
                        >
                          <div className="space-y-1 min-w-0">
                            <p>
                              <span className="text-slate-400">in:</span>{" "}
                              <span className="text-slate-700 dark:text-slate-300 break-all">
                                {tc.input}
                              </span>
                            </p>
                            <p>
                              <span className="text-slate-400">out:</span>{" "}
                              <span className="text-slate-700 dark:text-slate-300 break-all">
                                {tc.expected_output}
                              </span>
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleDeleteTc(q.id, tc.id)}
                            className="text-[11px] font-semibold text-red-600 shrink-0"
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="grid sm:grid-cols-2 gap-2 pt-1">
                    <input
                      className="rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-xs font-mono text-slate-900 dark:text-white"
                      placeholder="Input"
                      value={tcDraft[q.id]?.in ?? ""}
                      onChange={(e) =>
                        setTcDraft((prev) => ({
                          ...prev,
                          [q.id]: {
                            ...prev[q.id],
                            in: e.target.value,
                            out: prev[q.id]?.out ?? "",
                          },
                        }))
                      }
                    />
                    <input
                      className="rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-xs font-mono text-slate-900 dark:text-white"
                      placeholder="Expected output"
                      value={tcDraft[q.id]?.out ?? ""}
                      onChange={(e) =>
                        setTcDraft((prev) => ({
                          ...prev,
                          [q.id]: {
                            ...prev[q.id],
                            out: e.target.value,
                            in: prev[q.id]?.in ?? "",
                          },
                        }))
                      }
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => handleAddTc(q.id)}
                    className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    + Add test case
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <aside className="lg:w-52 shrink-0 flex flex-col gap-3 lg:sticky lg:top-24">
        <button
          type="button"
          onClick={() => {
            setShowAdd((v) => !v);
            setError("");
          }}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/80 transition-colors"
        >
          {showAdd ? "Close" : "+ Add question"}
        </button>

        {showAdd && (
          <form
            onSubmit={handleAddQuestion}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 space-y-2 shadow-sm"
          >
            <textarea
              className="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 dark:text-white min-h-[72px] resize-y"
              placeholder="Question"
              value={newPrompt}
              onChange={(e) => setNewPrompt(e.target.value)}
              required
            />
            <button
              type="submit"
              disabled={savingQ}
              className="w-full text-xs font-semibold py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-60"
            >
              {savingQ ? "…" : "Save"}
            </button>
          </form>
        )}

        <InstructorNavButton
          to={`/instructor/courses/${cid}/assignments/${aid}/submissions`}
          className="lg:w-full"
          variant="primary"
        >
          Submissions
        </InstructorNavButton>
      </aside>
    </div>
  );
}
