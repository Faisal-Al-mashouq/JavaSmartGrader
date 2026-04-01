import { useState, useRef, useEffect, useCallback } from "react";
import {
  useNavigate,
  useLocation,
  useSearchParams,
  Link,
} from "react-router-dom";
import { submitAnswer } from "../../../services/submissionService";
import {
  getAssignment,
  getAssignmentQuestions,
  getCourse,
} from "../../../services/courseService";

export default function StudentUpload() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [assignmentId, setAssignmentId] = useState("");
  const [questionId, setQuestionId] = useState("");
  const [questions, setQuestions] = useState([]);
  const [loadingQ, setLoadingQ] = useState(false);
  const [autoQ, setAutoQ] = useState(false);

  const [assignmentTitle, setAssignmentTitle] = useState("");
  const [courseName, setCourseName] = useState("");
  const [courseId, setCourseId] = useState("");

  const loadQuestionsForAssignment = useCallback(
    async (rawId, preferredQuestionId) => {
      const id =
        typeof rawId === "number" ? rawId : parseInt(String(rawId), 10);
      if (!id) return;
      setLoadingQ(true);
      setAutoQ(false);
      setQuestions([]);
      setQuestionId("");
      try {
        const [asgRes, qsRes] = await Promise.all([
          getAssignment(id),
          getAssignmentQuestions(id),
        ]);
        const asg = asgRes.data;
        setAssignmentTitle(asg.title ?? "");
        const courseRes = await getCourse(asg.course_id);
        setCourseName(courseRes.data?.name ?? "");
        setCourseId(String(asg.course_id));

        const list = qsRes.data ?? [];
        if (list.length > 0) {
          setQuestions(list);
          const pref =
            preferredQuestionId != null
              ? list.find((q) => q.id === Number(preferredQuestionId))
              : null;
          const pick = pref ?? list[0];
          setQuestionId(String(pick.id));
          setAutoQ(true);
        }
      } catch {
        setAssignmentTitle("");
        setCourseName("");
        setCourseId("");
      } finally {
        setLoadingQ(false);
      }
    },
    [],
  );

  useEffect(() => {
    const fromState = location.state?.assignmentId;
    const fromQuery = searchParams.get("assignment");
    const qid = location.state?.questionId;
    const id = fromState ?? (fromQuery ? parseInt(fromQuery, 10) : NaN);
    if (!id || Number.isNaN(id)) return;
    setAssignmentId(String(id));
    loadQuestionsForAssignment(id, qid);
  }, [location.state, searchParams, loadQuestionsForAssignment]);

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const [stage, setStage] = useState("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [result, setResult] = useState(null);

  const hasContext = Boolean(assignmentId && parseInt(assignmentId, 10));

  const handleFile = (f) => {
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      setErrorMsg("Only image files are allowed.");
      setStage("error");
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setStage("idle");
    setErrorMsg("");
  };

  const handleFileChange = (e) => handleFile(e.target.files[0]);
  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };
  const handleRemove = () => {
    setFile(null);
    setPreview(null);
    setStage("idle");
    setErrorMsg("");
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleSubmit = async () => {
    const aId = parseInt(assignmentId, 10);
    const qId = parseInt(questionId, 10);

    if (!aId || !qId) {
      setErrorMsg(
        "Choose an assignment and question from the Assignments page.",
      );
      setStage("error");
      return;
    }
    if (!file) {
      setErrorMsg("Please select an image file.");
      setStage("error");
      return;
    }

    setStage("submitting");
    setErrorMsg("");
    try {
      const res = await submitAnswer(qId, aId);
      setResult(res.data);
      setStage("done");
    } catch (err) {
      setErrorMsg(
        err.response?.data?.detail ?? "Submission failed. Please try again.",
      );
      setStage("error");
    }
  };

  /* No assignment context — direct visits use Assignments hub */
  if (!hasContext) {
    return (
      <div className="max-w-lg mx-auto space-y-6 text-center">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Submit an answer
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-2">
            Pick your course assignment, then open a question and upload your
            work there.
          </p>
        </div>
        <Link
          to="/dashboard/courses"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-sm transition-all"
        >
          Go to courses
        </Link>
      </div>
    );
  }

  if (stage === "done" && result) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Submitted
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Your answer is being processed by the grader.
          </p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-8 flex flex-col items-center gap-4 text-center">
          <div className="w-16 h-16 bg-emerald-50 dark:bg-emerald-900/30 rounded-2xl flex items-center justify-center">
            <svg
              className="w-8 h-8 text-emerald-500"
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
          </div>
          <div>
            <p className="text-lg font-bold text-slate-900 dark:text-white">
              Received
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              You can track progress under Submissions.
            </p>
          </div>
          <div className="w-full bg-slate-50 dark:bg-slate-700/50 rounded-xl px-5 py-4 text-left space-y-1.5">
            <Row label="Course" value={courseName || "—"} />
            <Row label="Assignment" value={assignmentTitle || "—"} highlight />
            <Row label="File" value={file?.name} />
            <Row label="Status" value="Processing…" highlight />
          </div>
          <div className="flex gap-3 mt-2 flex-wrap justify-center">
            <button
              onClick={() => {
                setStage("idle");
                setResult(null);
                handleRemove();
              }}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold shadow-sm transition-all active:scale-95"
            >
              Submit another
            </button>
            <button
              onClick={() => navigate("/dashboard/submissions")}
              className="px-5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              View submissions
            </button>
            <Link
              to={
                courseId
                  ? `/dashboard/assignments?course=${courseId}`
                  : "/dashboard/courses"
              }
              className="px-5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              Back to assignments
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Submit answer
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Upload a clear image of your handwritten work for this question.
        </p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-5 space-y-3">
        <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide">
          {courseName || "Course"}
        </p>
        <p className="text-sm font-bold text-slate-800 dark:text-slate-100">
          {assignmentTitle || "Assignment"}
        </p>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">
            Question{" "}
            {loadingQ && (
              <span className="normal-case font-normal text-blue-500 ml-1">
                loading…
              </span>
            )}
            {autoQ && !loadingQ && (
              <span className="normal-case font-normal text-emerald-500 ml-1">
                ready
              </span>
            )}
          </label>
          {questions.length > 0 ? (
            <select
              value={questionId}
              onChange={(e) => setQuestionId(e.target.value)}
              className="px-3 py-2 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {questions.map((q, i) => (
                <option key={q.id} value={q.id}>
                  Question {i + 1}
                  {(q.question_text ?? "").slice(0, 60)
                    ? ` — ${(q.question_text ?? "").slice(0, 60)}${(q.question_text ?? "").length > 60 ? "…" : ""}`
                    : ""}
                </option>
              ))}
            </select>
          ) : (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              No questions loaded.
            </p>
          )}
        </div>
        <p className="text-xs text-slate-400 dark:text-slate-500">
          <Link
            to={
              courseId
                ? `/dashboard/assignments?course=${courseId}`
                : "/dashboard/courses"
            }
            className="text-blue-600 dark:text-blue-400 font-medium hover:underline"
          >
            Choose a different assignment
          </Link>
        </p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => !file && inputRef.current?.click()}
          className={`m-5 rounded-xl border-2 border-dashed transition-all duration-200 flex flex-col items-center justify-center text-center
            ${
              file
                ? "border-slate-200 dark:border-slate-600 p-4 cursor-default"
                : dragging
                  ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 cursor-copy p-10"
                  : "border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-slate-50 dark:hover:bg-slate-700/40 cursor-pointer p-10"
            }`}
        >
          {preview ? (
            <div className="w-full">
              <img
                src={preview}
                alt="Preview"
                className="max-h-64 mx-auto rounded-lg object-contain shadow-sm"
              />
              <div className="flex items-center justify-center gap-2 mt-3">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium truncate max-w-[240px]">
                  {file.name}
                </span>
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  ({(file.size / 1024).toFixed(1)} KB)
                </span>
              </div>
            </div>
          ) : (
            <>
              <div
                className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-colors ${dragging ? "bg-blue-100 dark:bg-blue-900/40" : "bg-slate-100 dark:bg-slate-700"}`}
              >
                <svg
                  className={`w-7 h-7 transition-colors ${dragging ? "text-blue-600 dark:text-blue-400" : "text-slate-400 dark:text-slate-500"}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                  />
                </svg>
              </div>
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                {dragging
                  ? "Drop your image here"
                  : "Drag & drop or click to upload"}
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                PNG, JPG, JPEG
              </p>
            </>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="px-5 pb-5 flex flex-col gap-3">
          {file ? (
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleRemove}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Remove
              </button>
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Change file
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={stage === "submitting"}
                className="flex-[2] py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-70 active:scale-95 text-white text-sm font-bold shadow-sm transition-all duration-150 flex items-center justify-center gap-2"
              >
                {stage === "submitting" ? (
                  <>
                    <svg
                      className="w-4 h-4 animate-spin"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v8z"
                      />
                    </svg>
                    Submitting…
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                      />
                    </svg>
                    Submit
                  </>
                )}
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-2"
            >
              Choose file
            </button>
          )}

          {stage === "error" && (
            <div className="flex items-center gap-2 text-sm px-4 py-3 rounded-xl font-medium bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400">
              <svg
                className="w-4 h-4 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {errorMsg}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs text-slate-400 dark:text-slate-500">
        {label}
      </span>
      <span
        className={`text-xs font-semibold text-right ${highlight ? "text-blue-600 dark:text-blue-400" : "text-slate-700 dark:text-slate-300"}`}
      >
        {value}
      </span>
    </div>
  );
}
