import { useState, useEffect, useCallback } from "react";
import { Link, useParams, useLocation } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import {
  getCourse, getCourseStudents, getCourseAssignments,
  enrollStudentInCourse, unenrollStudentFromCourse,
} from "../../../services/courseService";
import { getStudents } from "../../../services/userService";

export default function InstructorCourseDetail() {
  const { courseId } = useParams();
  const location     = useLocation();
  const id           = Number(courseId);

  const [course, setCourse]           = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [enrolled, setEnrolled]       = useState([]);
  const [allStudents, setAllStudents] = useState([]);
  const [pickStudent, setPickStudent] = useState("");
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState("");
  const [busy, setBusy]               = useState(false);
  const [showEnroll, setShowEnroll]   = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [cRes, aRes, enRes, stRes] = await Promise.all([
        getCourse(id), getCourseAssignments(id), getCourseStudents(id), getStudents(),
      ]);
      setCourse(cRes.data);
      setAssignments(aRes.data);
      setEnrolled(enRes.data);
      setAllStudents(stRes.data);
      const enrolledIds = new Set(enRes.data.map((u) => u.id));
      const first = stRes.data.find((u) => !enrolledIds.has(u.id));
      setPickStudent(first ? String(first.id) : "");
    } catch (e) {
      console.error(e);
      setError(e.response?.data?.detail ?? "Could not load course.");
      setCourse(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { if (!Number.isFinite(id)) return; load(); }, [id, load]);

  useEffect(() => {
    if (loading || !course) return;
    if (location.hash === "#assignments") {
      requestAnimationFrame(() => {
        document.getElementById("course-assignments")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }, [loading, course, assignments, location.hash]);

  const enrolledIds   = new Set(enrolled.map((u) => u.id));
  const enrollOptions = allStudents.filter((u) => !enrolledIds.has(u.id));

  const handleEnroll = async (e) => {
    e.preventDefault();
    if (!pickStudent) return;
    setBusy(true); setError("");
    try {
      await enrollStudentInCourse(id, Number(pickStudent));
      setShowEnroll(false);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Enrollment failed.");
    } finally { setBusy(false); }
  };

  const handleUnenroll = async (studentId) => {
    if (!window.confirm("Remove this student from the course?")) return;
    setBusy(true); setError("");
    try {
      await unenrollStudentFromCourse(id, studentId);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not unenroll.");
    } finally { setBusy(false); }
  };

  if (!Number.isFinite(id)) return <p className="text-red-500 text-sm">Invalid course.</p>;

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">

      {/* ── Main content ── */}
      <div className="flex-1 min-w-0 space-y-6">
        {loading ? (
          <div className="flex items-center gap-3 text-slate-400 text-sm py-8">
            <div className="w-5 h-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
            Loading…
          </div>
        ) : error && !course ? (
          <p className="text-red-500 text-sm">{error}</p>
        ) : course ? (
          <>
            {/* Header */}
            <header className="space-y-2">
              <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest">Course</p>
              <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">{course.name}</h1>
              {course.description ? (
                <p className="text-slate-500 text-sm leading-relaxed max-w-3xl">{course.description}</p>
              ) : (
                <p className="text-xs text-slate-400 italic">No description</p>
              )}
            </header>

            <div className="flex flex-wrap gap-2">
              <InstructorNavButton to="/instructor/courses">← All courses</InstructorNavButton>
              <InstructorNavButton to="/instructor" variant="primary">Dashboard</InstructorNavButton>
            </div>

            {error && <p className="text-sm text-amber-600 dark:text-amber-400">{error}</p>}

            {/* Assignments section */}
            <section id="course-assignments"
              className="rounded-2xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm shadow-sm dark:shadow-xl overflow-hidden scroll-mt-24">
              <div className="px-5 py-4 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white">Assignments</h2>
                </div>
                <span className="text-xs font-bold text-slate-400 bg-slate-100 dark:text-slate-600 dark:bg-slate-800 px-2 py-0.5 rounded-full tabular-nums">
                  {assignments.length}
                </span>
              </div>

              {assignments.length === 0 ? (
                <div className="px-5 py-10 text-center space-y-2">
                  <p className="text-sm text-slate-400 dark:text-slate-500">No assignments yet.</p>
                  <p className="text-xs text-slate-400 dark:text-slate-700">Create one with <strong className="text-slate-500">+ New assignment</strong> on the right.</p>
                </div>
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-white/[0.04]">
                  {assignments.map((a, idx) => (
                    <li key={a.id}>
                      <Link to={`/instructor/courses/${id}/assignments/${a.id}`}
                        className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors group">
                        <span className="w-6 h-6 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-[10px] font-bold text-indigo-500 dark:text-indigo-400 shrink-0">
                          {idx + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-slate-700 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                            {a.title}
                          </p>
                          {a.description && (
                            <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{a.description}</p>
                          )}
                          {a.due_date && (
                            <p className="text-xs text-slate-400 dark:text-slate-700 mt-1">
                              Due {new Date(a.due_date).toLocaleString()}
                            </p>
                          )}
                        </div>
                        <svg className="w-4 h-4 text-slate-300 dark:text-slate-700 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors shrink-0"
                          viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                        </svg>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Students section */}
            <section className="rounded-2xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm shadow-sm dark:shadow-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 dark:border-white/[0.06] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  </div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white">Enrolled Students</h2>
                </div>
                <span className="text-xs font-bold text-slate-400 bg-slate-100 dark:text-slate-600 dark:bg-slate-800 px-2 py-0.5 rounded-full tabular-nums">
                  {enrolled.length}
                </span>
              </div>

              {enrolled.length === 0 ? (
                <div className="px-5 py-10 text-center space-y-2">
                  <p className="text-sm text-slate-400 dark:text-slate-500">No students yet.</p>
                  <p className="text-xs text-slate-400 dark:text-slate-700">Enroll students from the panel on the right.</p>
                </div>
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-white/[0.04]">
                  {enrolled.map((u) => (
                    <li key={u.id} className="px-5 py-3.5 flex items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors group">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-100 to-teal-100 dark:from-emerald-500/30 dark:to-teal-500/30 border border-emerald-200 dark:border-emerald-500/20 flex items-center justify-center shrink-0">
                          <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                            {u.username.slice(0, 2).toUpperCase()}
                          </span>
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{u.username}</p>
                          <p className="text-xs text-slate-400 truncate">{u.email}</p>
                        </div>
                      </div>
                      <button type="button" disabled={busy} onClick={() => handleUnenroll(u.id)}
                        className="text-xs font-semibold text-slate-400 dark:text-slate-700 hover:text-red-500 dark:hover:text-red-400 disabled:opacity-50 transition-colors shrink-0">
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </div>

      {/* ── Sidebar ── */}
      <aside className="lg:w-56 shrink-0 flex flex-col gap-3 lg:sticky lg:top-24">
        <Link to={`/instructor/courses/${id}/assignments/new`}
          className="block text-center text-sm font-semibold px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30 transition-all">
          + New assignment
        </Link>

        <button type="button"
          onClick={() => { setShowEnroll((v) => !v); setError(""); }}
          disabled={!course || enrollOptions.length === 0}
          className={`w-full text-sm font-semibold px-4 py-2.5 rounded-xl border transition-all duration-200
            ${showEnroll
              ? "border-red-300 dark:border-red-500/30 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10"
              : "border-slate-200 dark:border-white/[0.08] text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
            }`}>
          {showEnroll ? "✕ Close" : "+ Add student"}
        </button>

        {showEnroll && course && enrollOptions.length > 0 && (
          <form onSubmit={handleEnroll}
            className="rounded-2xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-900/80 dark:backdrop-blur-sm p-4 space-y-3 shadow-md dark:shadow-xl">
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Select student
            </label>
            <select
              className="w-full rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-800/60 px-3 py-2 text-sm text-slate-800 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none"
              value={pickStudent} onChange={(e) => setPickStudent(e.target.value)} required>
              {enrollOptions.map((u) => (
                <option key={u.id} value={u.id}>{u.username}</option>
              ))}
            </select>
            <button type="submit" disabled={busy}
              className="w-full text-sm font-semibold py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white disabled:opacity-50 shadow-lg shadow-emerald-100 dark:shadow-none transition-all">
              {busy ? "Enrolling…" : "Enroll"}
            </button>
          </form>
        )}

        {!loading && course && allStudents.length === 0 && (
          <p className="text-[11px] text-slate-400 dark:text-slate-600 leading-snug px-1">
            No student accounts in the system yet. Students must register first.
          </p>
        )}
      </aside>
    </div>
  );
}
