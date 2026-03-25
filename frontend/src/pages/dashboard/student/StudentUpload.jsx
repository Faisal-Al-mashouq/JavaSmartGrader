import { useState, useRef, useEffect } from "react";
import { getMyCourses, getCourseAssignments, getQuestions, createSubmission } from "../../../services/api";

/* ── Row helper ──────────────────────────────────────────────────────── */
function Row({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-400 dark:text-slate-500">{label}</span>
      <span className={`text-xs font-semibold ${highlight ? "text-blue-600 dark:text-blue-400" : "text-slate-700 dark:text-slate-300"}`}>{value}</span>
    </div>
  );
}

export default function StudentUpload() {
  /* ── Assignment / question selection state ───────────────────────── */
  const [courses,     setCourses]     = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [questions,   setQuestions]   = useState([]);
  const [selectedCourse,     setSelectedCourse]     = useState("");
  const [selectedAssignment, setSelectedAssignment] = useState("");
  const [selectedQuestion,   setSelectedQuestion]   = useState("");
  const [loadingCourses,     setLoadingCourses]     = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(false);
  const [loadingQuestions,   setLoadingQuestions]   = useState(false);

  /* ── File upload state ───────────────────────────────────────────── */
  const [file,     setFile]     = useState(null);
  const [preview,  setPreview]  = useState(null);
  const [dragging, setDragging] = useState(false);
  const [stage,    setStage]    = useState("idle"); // idle | processing | done | error
  const [errorMsg, setErrorMsg] = useState("");
  const inputRef = useRef(null);

  /* ── Fetch courses on mount ──────────────────────────────────────── */
  useEffect(() => {
    // For students there is no "get my courses" endpoint, so we try to fetch
    // all courses the student has submissions for, or fall back gracefully.
    // We use a general GET /courses list via the assignments mechanism.
    // Since only instructors have GET /courses/me, we load from the student's
    // submissions to discover which courses they're enrolled in.
    // Alternatively, instructors can use GET /courses/me — we attempt it and
    // fall back to an empty list.
    getMyCourses()
      .then((res) => setCourses(res.data))
      .catch(() => setCourses([]))
      .finally(() => setLoadingCourses(false));
  }, []);

  /* ── Fetch assignments when course changes ───────────────────────── */
  useEffect(() => {
    if (!selectedCourse) { setAssignments([]); setSelectedAssignment(""); return; }
    setLoadingAssignments(true);
    getCourseAssignments(selectedCourse)
      .then((res) => { setAssignments(res.data); setSelectedAssignment(""); setSelectedQuestion(""); })
      .catch(() => setAssignments([]))
      .finally(() => setLoadingAssignments(false));
  }, [selectedCourse]);

  /* ── Fetch questions when assignment changes ─────────────────────── */
  useEffect(() => {
    if (!selectedAssignment) { setQuestions([]); setSelectedQuestion(""); return; }
    setLoadingQuestions(true);
    getQuestions(selectedAssignment)
      .then((res) => { setQuestions(res.data); setSelectedQuestion(""); })
      .catch(() => setQuestions([]))
      .finally(() => setLoadingQuestions(false));
  }, [selectedAssignment]);

  /* ── File handling ───────────────────────────────────────────────── */
  const handleFile = (selectedFile) => {
    if (!selectedFile) return;
    if (!selectedFile.type.startsWith("image/")) {
      setErrorMsg("Only image files are allowed.");
      setStage("error");
      return;
    }
    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
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

  /* ── Submit ──────────────────────────────────────────────────────── */
  const handleSubmit = async () => {
    if (!file) { setErrorMsg("Please select a file first."); setStage("error"); return; }
    if (!selectedAssignment) { setErrorMsg("Please select an assignment."); setStage("error"); return; }
    if (!selectedQuestion && questions.length > 0) { setErrorMsg("Please select a question."); setStage("error"); return; }

    setStage("processing");
    setErrorMsg("");

    // Use the first question if none selected and none available
    const questionId = selectedQuestion || (questions[0]?.id ?? null);
    if (!questionId) { setErrorMsg("No question available for this assignment."); setStage("error"); return; }

    try {
      await createSubmission(questionId, selectedAssignment);
      setStage("done");
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Submission failed. Please try again.");
      setStage("error");
    }
  };

  const selectedAssignmentObj = assignments.find((a) => String(a.id) === String(selectedAssignment));
  const selectedCourseObj     = courses.find((c) => String(c.id) === String(selectedCourse));

  const selectCls = "w-full text-sm text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm";

  /* ── Done state ──────────────────────────────────────────────────── */
  if (stage === "done") {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">Upload Exam</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Submit your handwritten exam sheet as an image file</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm p-8 flex flex-col items-center gap-4 text-center">
          <div className="w-16 h-16 bg-emerald-50 dark:bg-emerald-900/30 rounded-2xl flex items-center justify-center">
            <svg className="w-8 h-8 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p className="text-lg font-bold text-slate-900 dark:text-white">Submitted Successfully!</p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Your exam has been submitted and is being graded by the AI grader.
              The instructor will review the results shortly.
            </p>
          </div>
          <div className="w-full bg-slate-50 dark:bg-slate-700/50 rounded-xl px-5 py-4 text-left space-y-1.5">
            <Row label="Assignment" value={selectedAssignmentObj?.title ?? "—"} />
            <Row label="Course"     value={selectedCourseObj?.name ?? "—"} />
            <Row label="File"       value={file?.name} />
            <Row label="Status"     value="Processing…" highlight />
          </div>
          <button
            onClick={() => { handleRemove(); setSelectedCourse(""); }}
            className="mt-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold shadow-sm transition-all active:scale-95"
          >
            Submit Another File
          </button>
        </div>
      </div>
    );
  }

  /* ── Main upload form ─────────────────────────────────────────────── */
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">Upload Exam</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Submit your handwritten exam sheet as an image file
        </p>
      </div>

      {/* Assignment selector card */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-700">
          <p className="text-sm font-bold text-slate-700 dark:text-slate-200">Select Assignment</p>
        </div>
        <div className="px-5 py-4 space-y-3">
          {/* Course */}
          <div>
            <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Course</label>
            {loadingCourses ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 italic">Loading courses…</p>
            ) : courses.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 italic">No courses available. Contact your instructor.</p>
            ) : (
              <select value={selectedCourse} onChange={(e) => setSelectedCourse(e.target.value)} className={selectCls}>
                <option value="">— Select a course —</option>
                {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            )}
          </div>

          {/* Assignment */}
          {selectedCourse && (
            <div>
              <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Assignment</label>
              {loadingAssignments ? (
                <p className="text-sm text-slate-400 dark:text-slate-500 italic">Loading assignments…</p>
              ) : assignments.length === 0 ? (
                <p className="text-sm text-slate-400 dark:text-slate-500 italic">No assignments for this course.</p>
              ) : (
                <select value={selectedAssignment} onChange={(e) => setSelectedAssignment(e.target.value)} className={selectCls}>
                  <option value="">— Select an assignment —</option>
                  {assignments.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.title}{a.due_date ? ` · Due ${new Date(a.due_date).toLocaleDateString()}` : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* Question */}
          {selectedAssignment && questions.length > 1 && (
            <div>
              <label className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-1">Question</label>
              {loadingQuestions ? (
                <p className="text-sm text-slate-400 dark:text-slate-500 italic">Loading questions…</p>
              ) : (
                <select value={selectedQuestion} onChange={(e) => setSelectedQuestion(e.target.value)} className={selectCls}>
                  <option value="">— Select a question —</option>
                  {questions.map((q, i) => (
                    <option key={q.id} value={q.id}>Question {i + 1}: {q.text?.slice(0, 60) ?? `Q${q.id}`}</option>
                  ))}
                </select>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Upload card */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => !file && inputRef.current?.click()}
          className={`m-5 rounded-xl border-2 border-dashed transition-all duration-200 flex flex-col items-center justify-center text-center
            ${file
              ? "border-slate-200 dark:border-slate-600 p-4 cursor-default"
              : dragging
              ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 cursor-copy p-10"
              : "border-slate-300 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-slate-50 dark:hover:bg-slate-700/40 cursor-pointer p-10"
            }`}
        >
          {preview ? (
            <div className="w-full">
              <img src={preview} alt="Preview" className="max-h-64 mx-auto rounded-lg object-contain shadow-sm" />
              <div className="flex items-center justify-center gap-2 mt-3">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium truncate max-w-[240px]">{file.name}</span>
                <span className="text-xs text-slate-400 dark:text-slate-500">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
            </div>
          ) : (
            <>
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-colors ${dragging ? "bg-blue-100 dark:bg-blue-900/40" : "bg-slate-100 dark:bg-slate-700"}`}>
                <svg className={`w-7 h-7 transition-colors ${dragging ? "text-blue-600 dark:text-blue-400" : "text-slate-400 dark:text-slate-500"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                {dragging ? "Drop your image here" : "Drag & drop or click to upload"}
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">PNG, JPG, JPEG accepted</p>
            </>
          )}
        </div>

        <input ref={inputRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />

        {/* Actions */}
        <div className="px-5 pb-5 flex flex-col gap-3">
          {file ? (
            <div className="flex gap-3">
              <button onClick={handleRemove} className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                Remove
              </button>
              <button onClick={() => inputRef.current?.click()} className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                Change File
              </button>
              <button
                onClick={handleSubmit}
                disabled={stage === "processing"}
                className="flex-[2] py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-70 active:scale-95 text-white text-sm font-bold shadow-sm transition-all duration-150 flex items-center justify-center gap-2"
              >
                {stage === "processing" ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                    Submitting…
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    Submit Exam
                  </>
                )}
              </button>
            </div>
          ) : (
            <button onClick={() => inputRef.current?.click()} className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13l-3 3m0 0l-3-3m3 3V8m0 13a9 9 0 110-18 9 9 0 010 18z" />
              </svg>
              Choose File
            </button>
          )}

          {stage === "error" && (
            <div className="flex items-center gap-2 text-sm px-4 py-3 rounded-xl font-medium bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {errorMsg}
            </div>
          )}
        </div>
      </div>

      {/* Tips */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-2xl px-5 py-4">
        <p className="text-xs font-bold text-blue-700 dark:text-blue-400 uppercase tracking-wide mb-2">Tips for best results</p>
        <ul className="space-y-1">
          {[
            "Ensure the image is well-lit and all text is clearly visible",
            "Use PNG or JPG format for best OCR accuracy",
            "Crop out any unnecessary background before uploading",
            "Make sure all code and text is legible and within frame",
          ].map((tip) => (
            <li key={tip} className="flex items-start gap-2 text-xs text-blue-600 dark:text-blue-400">
              <svg className="w-3.5 h-3.5 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4" />
              </svg>
              {tip}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
