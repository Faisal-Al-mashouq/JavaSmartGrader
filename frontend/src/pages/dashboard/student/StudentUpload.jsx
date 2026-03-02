import { useState, useRef } from "react";
import { useAuth } from "../../../context/AuthContext";
import { useSubmissions } from "../../../context/SubmissionsContext";

/** Detect which demo case the file belongs to based on its name */
function detectCase(filename) {
  const lower = filename.toLowerCase();
  if (lower.includes("file_1") || lower.includes("file1")) return 1;
  if (lower.includes("file_2") || lower.includes("file2")) return 2;
  return null;
}

const CASE_INFO = {
  1: {
    label: "Good Code Submission Detected",
    sub: "This file will be graded by the AI as a high-quality submission.",
    color: "border-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 dark:border-emerald-700",
    textColor: "text-emerald-700 dark:text-emerald-400",
    icon: (
      <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  2: {
    label: "Code Submission Detected",
    sub: "This file has been identified as a Java code assignment submission.",
    color: "border-blue-300 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-700",
    textColor: "text-blue-700 dark:text-blue-400",
    icon: (
      <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
};

export default function StudentUpload() {
  const { user }                    = useAuth();
  const { addSubmission }           = useSubmissions();

  const [file, setFile]             = useState(null);
  const [preview, setPreview]       = useState(null);
  const [caseType, setCaseType]     = useState(null);
  const [dragging, setDragging]     = useState(false);
  const [stage, setStage]           = useState("idle"); // idle | processing | done | error
  const [errorMsg, setErrorMsg]     = useState("");
  const inputRef                    = useRef(null);

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;
    if (!selectedFile.type.startsWith("image/")) {
      setErrorMsg("Only image files are allowed.");
      setStage("error");
      return;
    }
    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setCaseType(detectCase(selectedFile.name));
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
    setCaseType(null);
    setStage("idle");
    setErrorMsg("");
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleSubmit = () => {
    if (!file) { setErrorMsg("Please select a file first."); setStage("error"); return; }
    setStage("processing");

    const resolvedCase = caseType ?? 1; // default to case 1 for unknown files
    addSubmission({
      studentName: user?.username ?? "Student",
      fileUrl: preview,
      filename: file.name,
      caseType: resolvedCase,
    });

    // After 3 s the context will mark it "AI Graded" — mirror that here
    setTimeout(() => setStage("done"), 3000);
  };

  /* ── Done state ─────────────────────────────────────────────────── */
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
            <Row label="Assignment" value="Final Project - Banking System" />
            <Row label="Course"     value="CS201 – Object Oriented Programming" />
            <Row label="File"       value={file?.name} />
            <Row label="Status"     value="AI Grading in progress…" highlight />
          </div>
          <button
            onClick={handleRemove}
            className="mt-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold shadow-sm transition-all active:scale-95"
          >
            Submit Another File
          </button>
        </div>
      </div>
    );
  }

  /* ── Main upload form ───────────────────────────────────────────── */
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">Upload Exam</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Submit your handwritten exam sheet as an image file
        </p>
      </div>

      {/* Assignment info banner */}
      <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 rounded-2xl px-5 py-4 flex items-start gap-3">
        <svg className="w-5 h-5 text-indigo-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <div>
          <p className="text-sm font-bold text-indigo-700 dark:text-indigo-300">Active Assignment</p>
          <p className="text-sm text-indigo-600 dark:text-indigo-400 mt-0.5">Final Project – Banking System &nbsp;·&nbsp; CS201 &nbsp;·&nbsp; Due Dec 15, 2024</p>
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
                <svg className="w-4 h-4 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
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
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">PNG, JPG, JPEG – name your file <code className="bg-slate-100 dark:bg-slate-700 px-1 rounded">file_1</code> or <code className="bg-slate-100 dark:bg-slate-700 px-1 rounded">file_2</code></p>
            </>
          )}
        </div>

        <input ref={inputRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />

        {/* Detected-case banner */}
        {caseType && (
          <div className={`mx-5 mb-4 rounded-xl border px-4 py-3 flex items-start gap-3 ${CASE_INFO[caseType].color}`}>
            <span className="shrink-0 mt-0.5">{CASE_INFO[caseType].icon}</span>
            <div>
              <p className={`text-sm font-bold ${CASE_INFO[caseType].textColor}`}>{CASE_INFO[caseType].label}</p>
              <p className={`text-xs mt-0.5 ${CASE_INFO[caseType].textColor} opacity-80`}>{CASE_INFO[caseType].sub}</p>
            </div>
          </div>
        )}

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
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
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
            "Name your file file_1.jpg (good code) or file_2.jpg to trigger the demo cases",
            "Ensure the image is well-lit and all text is clearly visible",
            "Use PNG or JPG format for best OCR accuracy",
            "Crop out any unnecessary background before uploading",
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

function Row({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-400 dark:text-slate-500">{label}</span>
      <span className={`text-xs font-semibold ${highlight ? "text-blue-600 dark:text-blue-400" : "text-slate-700 dark:text-slate-300"}`}>{value}</span>
    </div>
  );
}
