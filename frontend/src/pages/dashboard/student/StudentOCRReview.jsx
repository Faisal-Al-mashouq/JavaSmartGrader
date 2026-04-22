import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getPendingReview,
  approveTranscription,
} from "../../../services/submissionService";

function FlagBadge({ flag }) {
  const pct = Math.round(Number(flag.confidence_score) * 100);
  const suggestions = flag.suggestions
    ? flag.suggestions
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : [];

  return (
    <div className="flex flex-col gap-1 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-xl px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-sm font-bold text-red-700 dark:text-red-400 break-all">
          "{flag.text_segment}"
        </span>
        <span className="shrink-0 text-xs font-semibold text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-500/20 px-2 py-0.5 rounded-full border border-red-200 dark:border-red-500/30">
          {pct}% confidence
        </span>
      </div>
      {suggestions.length > 0 && (
        <p className="text-xs text-red-600 dark:text-red-400">
          Suggestions:{" "}
          {suggestions.map((s, i) => (
            <span key={i}>
              <span className="font-mono font-semibold">{s}</span>
              {i < suggestions.length - 1 && ", "}
            </span>
          ))}
        </p>
      )}
      {flag.coordinates && (
        <p className="text-[10px] text-red-400 dark:text-red-500 font-mono">
          {flag.coordinates.replace(
            /line:(\d+):word:(\d+)/,
            "Line $1, Word $2",
          )}
        </p>
      )}
    </div>
  );
}

export default function StudentOCRReview() {
  const { submissionId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [flags, setFlags] = useState([]);
  const [text, setText] = useState("");
  const [originalText, setOriginalText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [done, setDone] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getPendingReview(submissionId);
      const t = res.data.transcribed_text ?? "";
      setText(t);
      setOriginalText(t);
      setFlags(res.data.flags ?? []);
    } catch (e) {
      const detail = e.response?.data?.detail;
      if (e.response?.status === 409) {
        setError("This submission is not awaiting your review.");
      } else if (e.response?.status === 403) {
        setError("You don't have access to this submission.");
      } else {
        setError(detail ?? "Failed to load OCR data.");
      }
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleApprove = async () => {
    if (!text.trim()) {
      setSubmitError("The transcription cannot be empty.");
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    try {
      await approveTranscription(submissionId, text);
      setDone(true);
    } catch (e) {
      setSubmitError(
        e.response?.data?.detail ?? "Failed to approve. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  /* ── Done state ─────────────────────────────────────────────────────── */
  if (done) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
        <div className="w-20 h-20 rounded-full bg-emerald-100 dark:bg-emerald-500/15 flex items-center justify-center shadow-lg">
          <svg
            className="w-10 h-10 text-emerald-600 dark:text-emerald-400"
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
        <div className="text-center">
          <h2 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Transcription Approved!
          </h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-2">
            Your code has been submitted for grading. You'll be notified when
            results are ready.
          </p>
        </div>
        <button
          onClick={() => navigate("/dashboard/submissions")}
          className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition-colors active:scale-95"
        >
          Back to My Submissions
        </button>
      </div>
    );
  }

  /* ── Loading ─────────────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-slate-400 dark:text-slate-500 text-sm">
          Loading OCR data…
        </p>
      </div>
    );
  }

  /* ── Error ───────────────────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-500/15 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-red-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div className="text-center">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">
            {error}
          </h2>
        </div>
        <button
          onClick={() => navigate("/dashboard/submissions")}
          className="px-5 py-2 rounded-xl border border-slate-200 dark:border-white/[0.1] text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
        >
          Back to Submissions
        </button>
      </div>
    );
  }

  const hasChanges = text !== originalText;

  /* ── Main UI ─────────────────────────────────────────────────────────── */
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs font-semibold text-amber-500 dark:text-amber-400 uppercase tracking-widest mb-1">
            Code Review
          </p>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Review Your Code
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Submission #{submissionId} · Check the extracted text, fix any
            mistakes, then approve.
          </p>
        </div>
        <button
          onClick={() => navigate("/dashboard/submissions")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 dark:border-white/[0.1] text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition-colors"
        >
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back
        </button>
      </div>

      {/* Info banner */}
      <div className="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-2xl px-5 py-4 flex gap-3">
        <svg
          className="w-5 h-5 text-amber-500 shrink-0 mt-0.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p className="text-sm text-amber-700 dark:text-amber-300 leading-relaxed">
          The text below was automatically extracted from your handwritten
          submission. Words highlighted in the{" "}
          <span className="font-semibold">Low-Confidence Words</span> panel may
          have been misread — please review and correct them directly in the
          editor before approving.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Code editor — takes 2/3 width on large screens */}
        <div className="lg:col-span-2 space-y-3">
          <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 dark:border-white/[0.06] bg-slate-50 dark:bg-white/[0.03] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <svg
                  className="w-4 h-4 text-slate-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                  />
                </svg>
                <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Extracted Code
                </span>
              </div>
              {hasChanges && (
                <span className="text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/15 px-2 py-0.5 rounded-full border border-indigo-200 dark:border-indigo-500/25">
                  Edited
                </span>
              )}
            </div>
            <textarea
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setSubmitError("");
              }}
              spellCheck={false}
              rows={24}
              className="w-full px-5 py-4 font-mono text-sm text-emerald-400 dark:text-emerald-400 bg-slate-900 dark:bg-black/50 focus:outline-none resize-none leading-relaxed placeholder-slate-600"
              placeholder="No transcription available…"
            />
          </div>

          {submitError && (
            <p className="text-sm text-red-500 dark:text-red-400 flex items-center gap-2">
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
                  d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {submitError}
            </p>
          )}

          {/* Approve button */}
          <button
            onClick={handleApprove}
            disabled={submitting || !text.trim()}
            className="w-full py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-bold shadow-sm transition-all active:scale-[0.99] flex items-center justify-center gap-2"
          >
            {submitting ? (
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
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Approve &amp; Submit for Grading
              </>
            )}
          </button>
        </div>

        {/* Flags sidebar */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 dark:border-white/[0.06] bg-slate-50 dark:bg-white/[0.03] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Low-Confidence Words
              </span>
              {flags.length > 0 && (
                <span className="ml-auto text-[11px] font-bold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/15 px-2 py-0.5 rounded-full border border-red-200 dark:border-red-500/25">
                  {flags.length}
                </span>
              )}
            </div>
            <div className="p-4 space-y-3 max-h-[520px] overflow-y-auto">
              {flags.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-8 text-center">
                  <svg
                    className="w-8 h-8 text-emerald-400"
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
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    All words were read with high confidence.
                  </p>
                </div>
              ) : (
                flags.map((f) => <FlagBadge key={f.id} flag={f} />)
              )}
            </div>
          </div>

          {/* Tips card */}
          <div className="bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-white/[0.08] shadow-sm dark:shadow-xl p-4 space-y-2">
            <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              Tips
            </p>
            <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              <li className="flex gap-2">
                <span className="text-indigo-500 font-bold shrink-0">1.</span>
                Find each flagged word in the editor and correct it if it was
                misread.
              </li>
              <li className="flex gap-2">
                <span className="text-indigo-500 font-bold shrink-0">2.</span>
                Only fix OCR mistakes — do not change your code logic.
              </li>
              <li className="flex gap-2">
                <span className="text-indigo-500 font-bold shrink-0">3.</span>
                Once satisfied, click{" "}
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                  Approve
                </span>{" "}
                to send to grading.
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
