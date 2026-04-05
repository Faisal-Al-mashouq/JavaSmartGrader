import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import InstructorNavButton from "../../../components/InstructorNavButton";
import { createCourse, getMyCourses } from "../../../services/courseService";

export default function InstructorCourses() {
  const [courses, setCourses]         = useState([]);
  const [loading, setLoading]         = useState(true);
  const [showAdd, setShowAdd]         = useState(false);
  const [name, setName]               = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving]           = useState(false);
  const [error, setError]             = useState("");

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

  useEffect(() => { load(); }, []);

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

  const ACCENTS = [
    "from-blue-500 to-cyan-500",
    "from-indigo-500 to-violet-500",
    "from-emerald-500 to-teal-500",
    "from-amber-500 to-orange-500",
    "from-rose-500 to-pink-500",
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-8 lg:items-start max-w-6xl">

      {/* ── Main content ── */}
      <div className="flex-1 min-w-0 space-y-1">
        <p className="text-xs font-semibold text-indigo-500 dark:text-indigo-400 uppercase tracking-widest mb-1">Instructor Panel</p>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mb-1">Courses</h1>
        <p className="text-slate-500 text-sm pb-5">
          Your teaching spaces. Open a course to manage students, assignments, and materials.
        </p>

        <div className="rounded-2xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-900/70 dark:backdrop-blur-sm shadow-sm dark:shadow-xl overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin mx-auto mb-3" />
              <p className="text-slate-400 text-sm">Loading courses…</p>
            </div>
          ) : courses.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center mx-auto">
                <svg className="w-7 h-7 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <p className="text-slate-500 dark:text-slate-400 text-sm">No courses yet.</p>
              <p className="text-slate-400 dark:text-slate-600 text-xs">Use <strong className="text-slate-600 dark:text-slate-400">+ Add course</strong> on the right to get started.</p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-white/[0.05]">
              {courses.map((c, idx) => {
                const accent = ACCENTS[idx % ACCENTS.length];
                return (
                  <li key={c.id}>
                    <Link to={`/instructor/courses/${c.id}`}
                      className="flex items-center gap-4 px-6 py-5 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors group">
                      <div className={`w-1 h-10 rounded-full bg-gradient-to-b ${accent} opacity-50 group-hover:opacity-100 transition-opacity shrink-0`} />
                      <div className="min-w-0 flex-1">
                        <p className="text-base font-semibold text-slate-700 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                          {c.name}
                        </p>
                        {c.description ? (
                          <p className="text-sm text-slate-500 mt-1 leading-relaxed line-clamp-1">{c.description}</p>
                        ) : (
                          <p className="text-xs text-slate-400 dark:text-slate-700 mt-1 italic">No description</p>
                        )}
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="text-[11px] font-mono text-slate-400 dark:text-slate-700">#{c.id}</span>
                        <svg className="w-4 h-4 text-slate-300 dark:text-slate-700 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                        </svg>
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="pt-4">
          <InstructorNavButton to="/instructor" variant="primary">← Dashboard</InstructorNavButton>
        </div>
      </div>

      {/* ── Sidebar ── */}
      <aside className="lg:w-56 shrink-0 flex flex-col gap-3 lg:sticky lg:top-24">
        <button type="button"
          onClick={() => { setShowAdd((v) => !v); setError(""); }}
          className={`w-full text-sm font-semibold px-4 py-2.5 rounded-xl border transition-all duration-200
            ${showAdd
              ? "border-red-300 dark:border-red-500/30 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10"
              : "border-indigo-300 dark:border-indigo-500/40 text-indigo-600 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20 shadow-sm"
            }`}>
          {showAdd ? "✕ Close" : "+ Add course"}
        </button>

        {showAdd && (
          <form onSubmit={handleCreate}
            className="rounded-2xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-900/80 dark:backdrop-blur-sm p-4 space-y-3 shadow-md dark:shadow-xl">
            {error && (
              <p className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 px-3 py-2 rounded-lg leading-snug">{error}</p>
            )}
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Name</label>
              <input
                className="w-full rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-800/60 px-3 py-2 text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                value={name} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. CS101" required />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Description</label>
              <textarea
                className="w-full rounded-xl border border-slate-200 dark:border-white/[0.08] bg-white dark:bg-slate-800/60 px-3 py-2 text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none min-h-[72px] resize-y"
                value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional" />
            </div>
            <button type="submit" disabled={saving}
              className="w-full text-sm font-semibold py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white disabled:opacity-50 shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30 transition-all">
              {saving ? "Saving…" : "Create course"}
            </button>
          </form>
        )}
      </aside>
    </div>
  );
}
