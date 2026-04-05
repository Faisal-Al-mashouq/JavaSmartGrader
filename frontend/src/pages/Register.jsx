import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { registerUser } from "../services/authService";

const keyframes = `
  @keyframes blob1 {
    0%, 100% { transform: translate(0,0)   scale(1);   }
    33%       { transform: translate(40px,-30px) scale(1.1); }
    66%       { transform: translate(-20px,20px) scale(0.95); }
  }
  @keyframes blob2 {
    0%, 100% { transform: translate(0,0)   scale(1);   }
    33%       { transform: translate(-35px,25px) scale(1.08); }
    66%       { transform: translate(25px,-20px) scale(0.97); }
  }
  @keyframes blob3 {
    0%, 100% { transform: translate(0,0) scale(1);   }
    50%       { transform: translate(20px,30px) scale(1.06); }
  }
  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`;

const ROLES = [
  {
    value: "student",
    label: "Student",
    desc: "Submit assignments and get AI feedback",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
        <path d="M10.394 2.08a1 1 0 00-.788 0l-7 3a1 1 0 000 1.84L5.25 8.051a.999.999 0 01.356-.257l4-1.714a1 1 0 11.788 1.838L7.667 9.088l1.94.831a1 1 0 00.787 0l7-3a1 1 0 000-1.838l-7-3zM3.31 9.397L5 10.12v4.102a8.969 8.969 0 00-1.05-.174 1 1 0 01-.89-.89 11.115 11.115 0 01.25-3.762zM9.3 16.573A9.026 9.026 0 007 14.935v-3.957l1.818.78a3 3 0 002.364 0l5.508-2.361a11.026 11.026 0 01.25 3.762 1 1 0 01-.89.89 8.968 8.968 0 00-5.35 2.524 1 1 0 01-1.4 0zM6 18a1 1 0 001-1v-2.065a8.935 8.935 0 00-2-.712V17a1 1 0 001 1z" />
      </svg>
    ),
  },
  {
    value: "instructor",
    label: "Instructor",
    desc: "Create assignments and grade submissions",
    icon: (
      <svg className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-5.5-2.5a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM10 12a5.99 5.99 0 00-4.793 2.39A6.483 6.483 0 0010 16.5a6.483 6.483 0 004.793-2.11A5.99 5.99 0 0010 12z" clipRule="evenodd" />
      </svg>
    ),
  },
];

export default function Register() {
  const navigate    = useNavigate();
  const [form, setForm]             = useState({ username: "", email: "", password: "", role: "student" });
  const [error, setError]           = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [focused, setFocused]       = useState("");

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await registerUser(form);
      navigate("/login");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail[0]?.msg ?? "Registration failed." : (detail ?? "Registration failed."));
    } finally {
      setSubmitting(false);
    }
  };

  const fields = [
    {
      name: "username",
      label: "Username",
      type: "text",
      placeholder: "choose a username",
      icon: (
        <svg className="w-4 h-4 text-slate-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
          <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
        </svg>
      ),
    },
    {
      name: "email",
      label: "Email",
      type: "email",
      placeholder: "you@example.com",
      icon: (
        <svg className="w-4 h-4 text-slate-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
          <path d="M3 4a2 2 0 00-2 2v1.161l8.441 4.221a1.25 1.25 0 001.118 0L19 7.162V6a2 2 0 00-2-2H3z" />
          <path d="M19 8.839l-7.77 3.885a2.75 2.75 0 01-2.46 0L1 8.839V14a2 2 0 002 2h14a2 2 0 002-2V8.839z" />
        </svg>
      ),
    },
    {
      name: "password",
      label: "Password",
      type: "password",
      placeholder: "••••••••",
      icon: (
        <svg className="w-4 h-4 text-slate-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
        </svg>
      ),
    },
  ];

  return (
    <>
      <style>{keyframes}</style>

      <div className="min-h-screen flex bg-slate-950 overflow-hidden">

        {/* ── animated background blobs ── */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div style={{ animation: "blob1 18s ease-in-out infinite" }}
            className="absolute -top-40 -right-40 w-[520px] h-[520px] rounded-full bg-violet-600 opacity-20 blur-[120px]" />
          <div style={{ animation: "blob2 22s ease-in-out infinite 3s" }}
            className="absolute bottom-0 -left-40 w-[480px] h-[480px] rounded-full bg-indigo-700 opacity-15 blur-[120px]" />
          <div style={{ animation: "blob3 16s ease-in-out infinite 5s" }}
            className="absolute top-1/3 left-1/2 w-[360px] h-[360px] rounded-full bg-blue-600 opacity-10 blur-[100px]" />
        </div>

        {/* ══════════ LEFT BRAND PANEL ══════════ */}
        <div className="hidden lg:flex flex-col justify-between w-[48%] relative px-16 py-14">
          {/* brand */}
          <div style={{ animation: "fadeSlideIn 0.7s ease both" }}>
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-900/50">
                <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.745 3.745 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.745 3.745 0 013.296-1.043A3.745 3.745 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.745 3.745 0 013.296 1.043 3.745 3.745 0 011.043 3.296A3.745 3.745 0 0121 12z" />
                </svg>
              </div>
              <span className="text-white font-bold text-lg tracking-tight">JavaSmartGrader</span>
            </div>
          </div>

          {/* headline */}
          <div className="space-y-6" style={{ animation: "fadeSlideIn 0.7s ease 0.15s both" }}>
            <div>
              <h1 className="text-5xl font-extrabold leading-tight text-white">
                Join the future<br />
                <span className="bg-gradient-to-r from-violet-400 via-indigo-400 to-blue-400 bg-clip-text text-transparent">
                  of grading.
                </span>
              </h1>
              <p className="mt-4 text-slate-400 text-lg leading-relaxed max-w-sm">
                Whether you teach or learn, JavaSmartGrader gives you AI-powered tools to level up your Java coursework.
              </p>
            </div>

            {/* stats */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { num: "AI", label: "Powered" },
                { num: "4", label: "Rubric Criteria" },
                { num: "∞", label: "Submissions" },
              ].map(({ num, label }) => (
                <div key={label} className="rounded-2xl bg-white/5 border border-white/10 p-4 text-center backdrop-blur-sm">
                  <p className="text-2xl font-extrabold text-white">{num}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <div style={{ animation: "fadeSlideIn 0.7s ease 0.3s both" }}>
            <p className="text-slate-600 text-sm">Already have an account?{" "}
              <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors">Sign in</Link>
            </p>
          </div>
        </div>

        {/* ══════════ RIGHT FORM PANEL ══════════ */}
        <div className="flex-1 flex items-center justify-center px-6 py-12 relative">
          <div
            className="w-full max-w-sm space-y-6"
            style={{ animation: "fadeSlideIn 0.6s ease 0.1s both" }}
          >

            {/* mobile logo */}
            <div className="lg:hidden flex items-center gap-3 justify-center">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.745 3.745 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.745 3.745 0 013.296-1.043A3.745 3.745 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.745 3.745 0 013.296 1.043 3.745 3.745 0 011.043 3.296A3.745 3.745 0 0121 12z" />
                </svg>
              </div>
              <span className="text-white font-bold text-lg">JavaSmartGrader</span>
            </div>

            {/* card */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl shadow-black/40">
              <div className="mb-6">
                <h2 className="text-2xl font-extrabold text-white">Create account</h2>
                <p className="text-slate-400 text-sm mt-1">Get started for free</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">

                {/* text fields */}
                {fields.map(({ name, label, type, placeholder, icon }) => (
                  <div key={name}>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
                      {label}
                    </label>
                    <div className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-200
                      ${focused === name
                        ? "border-indigo-500 bg-indigo-950/40 ring-2 ring-indigo-500/20"
                        : "border-white/10 bg-white/5"}`}>
                      {icon}
                      <input
                        type={type}
                        name={name}
                        value={form[name]}
                        onChange={handleChange}
                        onFocus={() => setFocused(name)}
                        onBlur={() => setFocused("")}
                        className="flex-1 bg-transparent text-white placeholder-slate-600 text-sm outline-none"
                        placeholder={placeholder}
                        required
                      />
                    </div>
                  </div>
                ))}

                {/* role selector */}
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                    I am a…
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {ROLES.map((r) => (
                      <button
                        key={r.value}
                        type="button"
                        onClick={() => setForm({ ...form, role: r.value })}
                        className={`flex flex-col items-start gap-1.5 p-3.5 rounded-xl border text-left transition-all duration-200
                          ${form.role === r.value
                            ? "border-indigo-500 bg-indigo-950/50 ring-2 ring-indigo-500/20"
                            : "border-white/10 bg-white/5 hover:border-white/20"}`}
                      >
                        <span className={form.role === r.value ? "text-indigo-400" : "text-slate-500"}>
                          {r.icon}
                        </span>
                        <span className={`text-sm font-bold ${form.role === r.value ? "text-white" : "text-slate-400"}`}>
                          {r.label}
                        </span>
                        <span className="text-xs text-slate-600 leading-tight">{r.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {error && (
                  <div className="flex items-start gap-2.5 text-sm text-red-300 bg-red-950/50 border border-red-800/60 px-4 py-3 rounded-xl">
                    <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                    </svg>
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-indigo-900/40 hover:shadow-indigo-900/60 hover:-translate-y-0.5 active:translate-y-0"
                >
                  {submitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
                      </svg>
                      Creating account…
                    </span>
                  ) : "Create Account"}
                </button>
              </form>
            </div>

            <p className="text-center text-slate-500 text-sm lg:hidden">
              Already have an account?{" "}
              <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>

      </div>
    </>
  );
}
