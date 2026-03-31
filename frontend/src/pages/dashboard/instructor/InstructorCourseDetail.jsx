import { useState, useEffect, useCallback } from "react";
import { Link, useParams, useLocation } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import {
  getCourse,
  getCourseStudents,
  getCourseAssignments,
  enrollStudentInCourse,
  unenrollStudentFromCourse,
} from "../../../services/courseService";
import { getStudents } from "../../../services/userService";

export default function InstructorCourseDetail() {
  const { courseId } = useParams();
  const location = useLocation();
  const id = Number(courseId);
  const [course, setCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [enrolled, setEnrolled] = useState([]);
  const [allStudents, setAllStudents] = useState([]);
  const [pickStudent, setPickStudent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showEnroll, setShowEnroll] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [cRes, aRes, enRes, stRes] = await Promise.all([
        getCourse(id),
        getCourseAssignments(id),
        getCourseStudents(id),
        getStudents(),
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

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    load();
  }, [id, load]);

  useEffect(() => {
    if (loading || !course) return;
    if (location.hash === "#assignments") {
      requestAnimationFrame(() => {
        document
          .getElementById("course-assignments")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }, [loading, course, assignments, location.hash]);

  const enrolledIds = new Set(enrolled.map((u) => u.id));
  const enrollOptions = allStudents.filter((u) => !enrolledIds.has(u.id));

  const handleEnroll = async (e) => {
    e.preventDefault();
    if (!pickStudent) return;
    setBusy(true);
    setError("");
    try {
      await enrollStudentInCourse(id, Number(pickStudent));
      setShowEnroll(false);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Enrollment failed.");
    } finally {
      setBusy(false);
    }
  };

  const handleUnenroll = async (studentId) => {
    if (!window.confirm("Remove this student from the course?")) return;
    setBusy(true);
    setError("");
    try {
      await unenrollStudentFromCourse(id, studentId);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not unenroll.");
    } finally {
      setBusy(false);
    }
  };

  if (!Number.isFinite(id)) {
    return <p className="text-red-600 text-sm">Invalid course.</p>;
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">
      <div className="flex-1 min-w-0 space-y-6">
        {loading ? (
          <p className="text-slate-500 text-sm">Loading…</p>
        ) : error && !course ? (
          <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
        ) : course ? (
          <>
            <header className="space-y-2">
              <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                {course.name}
              </h1>
              {course.description ? (
                <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed max-w-3xl">
                  {course.description}
                </p>
              ) : (
                <p className="text-xs text-slate-400 italic">No description</p>
              )}
            </header>

            <div className="flex flex-wrap gap-2 pt-1">
              <InstructorNavButton to="/instructor/courses">
                All courses
              </InstructorNavButton>
              <InstructorNavButton to="/instructor" variant="primary">
                Dashboard
              </InstructorNavButton>
            </div>

            {error && (
              <p className="text-sm text-amber-600 dark:text-amber-400">
                {error}
              </p>
            )}

            <section
              id="course-assignments"
              className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden scroll-mt-24"
            >
              <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                  Assignments
                </h2>
                <span className="text-xs text-slate-400 tabular-nums">
                  {assignments.length}
                </span>
              </div>
              {assignments.length === 0 ? (
                <p className="px-5 py-8 text-sm text-slate-500 dark:text-slate-400">
                  No assignments yet. Create one with{" "}
                  <strong className="font-medium text-slate-600 dark:text-slate-300">
                    + New assignment
                  </strong>{" "}
                  on the right.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-slate-700">
                  {assignments.map((a) => (
                    <li key={a.id}>
                      <Link
                        to={`/instructor/courses/${id}/assignments/${a.id}`}
                        className="block px-5 py-4 hover:bg-slate-50 dark:hover:bg-slate-700/35 transition-colors group"
                      >
                        <p className="text-base font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                          {a.title}
                        </p>
                        {a.description && (
                          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 line-clamp-2">
                            {a.description}
                          </p>
                        )}
                        {a.due_date && (
                          <p className="text-xs text-slate-400 mt-1.5">
                            Due {new Date(a.due_date).toLocaleString()}
                          </p>
                        )}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                  Students enrolled
                </h2>
                <span className="text-xs text-slate-400 tabular-nums">
                  {enrolled.length}
                </span>
              </div>
              {enrolled.length === 0 ? (
                <p className="px-5 py-8 text-sm text-slate-500 dark:text-slate-400">
                  No students yet. Enroll accounts from the panel on the right.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100 dark:divide-slate-700">
                  {enrolled.map((u) => (
                    <li
                      key={u.id}
                      className="px-5 py-3.5 flex items-center justify-between gap-3 hover:bg-slate-50/80 dark:hover:bg-slate-700/30"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                          {u.username}
                        </p>
                        <p className="text-xs text-slate-500 truncate">
                          {u.email}
                        </p>
                      </div>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleUnenroll(u.id)}
                        className="text-xs font-medium text-red-600 dark:text-red-400 hover:underline disabled:opacity-50 shrink-0"
                      >
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

      <aside className="lg:w-52 shrink-0 flex flex-col gap-3 lg:sticky lg:top-24">
        <InstructorNavButton
          to={`/instructor/courses/${id}/assignments/new`}
          className="lg:w-full"
        >
          + New assignment
        </InstructorNavButton>

        <button
          type="button"
          onClick={() => {
            setShowEnroll((v) => !v);
            setError("");
          }}
          disabled={!course || enrollOptions.length === 0}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/80 disabled:opacity-45 disabled:cursor-not-allowed transition-colors"
        >
          {showEnroll ? "Close" : "+ Add student"}
        </button>

        {showEnroll && course && enrollOptions.length > 0 && (
          <form
            onSubmit={handleEnroll}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 space-y-2 shadow-sm"
          >
            <select
              className="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 dark:text-white"
              value={pickStudent}
              onChange={(e) => setPickStudent(e.target.value)}
              required
            >
              {enrollOptions.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.username}
                </option>
              ))}
            </select>
            <button
              type="submit"
              disabled={busy}
              className="w-full text-xs font-semibold py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-60"
            >
              {busy ? "…" : "Enroll"}
            </button>
          </form>
        )}

        {!loading && course && allStudents.length === 0 && (
          <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">
            No student accounts in the system yet. Students must register first.
          </p>
        )}
      </aside>
    </div>
  );
}
