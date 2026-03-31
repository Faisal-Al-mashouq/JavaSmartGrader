import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { createCourse, getMyCourses } from "../../../services/courseService";

export default function InstructorCourses() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const { data } = await getMyCourses();
      setCourses(data);
    } catch (e) {
      console.error(e);
      setError("Could not load courses.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError("");
    setSaving(true);
    try {
      await createCourse(name.trim(), description.trim() || undefined);
      setName("");
      setDescription("");
      setShowAdd(false);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Failed to create course.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">
      <div className="flex-1 min-w-0 space-y-1">
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Courses
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm pb-4">
          Your teaching spaces. Open a course for students, assignments, and
          materials.
        </p>

        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm overflow-hidden">
          {loading ? (
            <p className="p-10 text-center text-slate-500 text-sm">Loading…</p>
          ) : courses.length === 0 ? (
            <p className="p-10 text-center text-slate-500 dark:text-slate-400 text-sm">
              No courses yet. Use{" "}
              <strong className="font-medium text-slate-600 dark:text-slate-300">
                Add course
              </strong>{" "}
              on the right.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-700">
              {courses.map((c) => (
                <li key={c.id}>
                  <Link
                    to={`/instructor/courses/${c.id}`}
                    className="block px-6 py-5 hover:bg-slate-50 dark:hover:bg-slate-700/35 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="text-lg font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                          {c.name}
                        </p>
                        {c.description ? (
                          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1.5 leading-relaxed">
                            {c.description}
                          </p>
                        ) : (
                          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 italic">
                            No description
                          </p>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-slate-400 shrink-0 pt-1">
                        #{c.id}
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="pt-4">
          <InstructorNavButton to="/instructor" variant="primary">
            Dashboard
          </InstructorNavButton>
        </div>
      </div>

      <aside className="lg:w-52 shrink-0 flex flex-col gap-3 lg:sticky lg:top-24">
        <button
          type="button"
          onClick={() => {
            setShowAdd((v) => !v);
            setError("");
          }}
          className="self-end lg:self-stretch text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/80 transition-colors"
        >
          {showAdd ? "Close" : "+ Add course"}
        </button>

        {showAdd && (
          <form
            onSubmit={handleCreate}
            className="rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 p-3 space-y-2 shadow-sm"
          >
            {error && (
              <p className="text-[11px] text-red-600 dark:text-red-400 leading-snug">
                {error}
              </p>
            )}
            <input
              className="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 dark:text-white"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Course name"
              required
            />
            <textarea
              className="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-xs text-slate-900 dark:text-white min-h-[56px] resize-y"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
            />
            <button
              type="submit"
              disabled={saving}
              className="w-full text-xs font-semibold py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-60"
            >
              {saving ? "…" : "Save"}
            </button>
          </form>
        )}
      </aside>
    </div>
  );
}
