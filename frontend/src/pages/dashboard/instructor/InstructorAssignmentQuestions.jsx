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
      })
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
          setError(e?.response?.data?.detail ?? e?.message ?? "Could not load questions.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
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
      <div className="flex-1 min-w-0 space-y-6">

        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">Questions</p>
            <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {assignment?.title ?? "Assignment"}
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-1 text-sm">
              Each question can include test cases with expected input and output.
            </p>
          </div>
          <InstructorNavButton to={`/instructor/courses/${cid}/assignments/${aid}`} variant="primary">
            ← Assignment
          </InstructorNavButton>
        </div>

        {error && (
          <p className="text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl px-4 py-3">{error}</p>
        )}

        {loading ? (
          <p className="text-slate-500 text-sm">Loading…</p>
        ) : questions.length === 0 ? (
          <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl py-16 flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm font-bold text-slate-900 dark:text-white">No questions yet</p>
            <p className="text-xs text-slate-400">Use <strong className="text-slate-500 dark:text-slate-300">+ Add question</strong> on the right.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {questions.map((q, idx) => (
              <div
                key={q.id}
                className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl overflow-hidden"
              >
                <div className="px-6 py-4 border-b border-slate-100 dark:border-white/[0.06] flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shrink-0 shadow-sm mt-0.5">
                      <span className="text-xs font-extrabold text-white">{idx + 1}</span>
                    </div>
                    <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap">
                      {q.question_text}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeleteQuestion(q.id)}
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors shrink-0"
                    title="Delete question"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>

                <div className="px-6 py-4 space-y-3 bg-slate-50 dark:bg-white/[0.02]">
                  <p className="text-[11px] font-bold text-slate-400 dark:text-slate-600 uppercase tracking-widest">
                    Test cases
                  </p>
                  {(testcasesByQ[q.id] ?? []).length === 0 ? (
                    <p className="text-xs text-slate-400 dark:text-slate-500">No test cases yet.</p>
                  ) : (
                    <ul className="space-y-2">
                      {(testcasesByQ[q.id] ?? []).map((tc) => (
                        <li
                          key={tc.id}
                          className="text-xs font-mono bg-white dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.08] rounded-xl p-3 flex flex-col sm:flex-row sm:items-start justify-between gap-2"
                        >
                          <div className="space-y-1 min-w-0">
                            <p>
                              <span className="text-slate-400">in:</span>{" "}
                              <span className="text-slate-700 dark:text-slate-300 break-all">{tc.input}</span>
                            </p>
                            <p>
                              <span className="text-slate-400">out:</span>{" "}
                              <span className="text-slate-700 dark:text-slate-300 break-all">{tc.expected_output}</span>
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleDeleteTc(q.id, tc.id)}
                            className="text-[11px] font-semibold text-red-500 dark:text-red-400 hover:underline shrink-0"
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="grid sm:grid-cols-2 gap-2 pt-1">
                    <input
                      className="rounded-lg border border-slate-200 dark:border-white/[0.1] bg-white dark:bg-white/[0.05] px-3 py-1.5 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="Input"
                      value={tcDraft[q.id]?.in ?? ""}
                      onChange={(e) =>
                        setTcDraft((prev) => ({
                          ...prev,
                          [q.id]: { ...prev[q.id], in: e.target.value, out: prev[q.id]?.out ?? "" },
                        }))
                      }
                    />
                    <input
                      className="rounded-lg border border-slate-200 dark:border-white/[0.1] bg-white dark:bg-white/[0.05] px-3 py-1.5 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="Expected output"
                      value={tcDraft[q.id]?.out ?? ""}
                      onChange={(e) =>
                        setTcDraft((prev) => ({
                          ...prev,
                          [q.id]: { ...prev[q.id], out: e.target.value, in: prev[q.id]?.in ?? "" },
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
          onClick={() => { setShowAdd((v) => !v); setError(""); }}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-white/[0.1] text-slate-700 dark:text-slate-200 bg-white dark:bg-white/[0.05] hover:bg-slate-50 dark:hover:bg-white/[0.08] transition-colors"
        >
          {showAdd ? "Close" : "+ Add question"}
        </button>

        {showAdd && (
          <form
            onSubmit={handleAddQuestion}
            className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-xl border border-slate-200 dark:border-white/[0.08] p-3 space-y-2 shadow-sm dark:shadow-xl"
          >
            <textarea
              className="w-full rounded-lg border border-slate-200 dark:border-white/[0.1] bg-white dark:bg-white/[0.05] px-3 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 min-h-[72px] resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Question text…"
              value={newPrompt}
              onChange={(e) => setNewPrompt(e.target.value)}
              required
            />
            <button
              type="submit"
              disabled={savingQ}
              className="w-full text-xs font-bold py-1.5 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-600 hover:to-violet-600 text-white disabled:opacity-60 transition-all"
            >
              {savingQ ? "Saving…" : "Save question"}
            </button>
          </form>
        )}

        <InstructorNavButton
          to={`/instructor/courses/${cid}/assignments/${aid}/rubric`}
          className="lg:w-full"
        >
          Grading Rubric
        </InstructorNavButton>
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
