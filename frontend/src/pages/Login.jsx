import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const floatKeyframes = `
  @keyframes snippetPulse {
    0%   { opacity: 0;    }
    5%   { opacity: 0.03; }
    10%  { opacity: 0.07; }
    15%  { opacity: 0.11; }
    20%  { opacity: 0.15; }
    25%  { opacity: 0.18; }
    30%  { opacity: 0.18; }
    45%  { opacity: 0.18; }
    50%  { opacity: 0.15; }
    55%  { opacity: 0.11; }
    60%  { opacity: 0.07; }
    65%  { opacity: 0.03; }
    70%  { opacity: 0;    }
    100% { opacity: 0;    }
  }
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
    0%, 100% { transform: translate(0,0)   scale(1);   }
    50%       { transform: translate(20px,30px) scale(1.06); }
  }
  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`;

// Safe zone: the gap between the logo (~18%) and the headline (~42%).
// Nothing important lives in that band, so snippets pulse there only.
const codeSnippets = [
  { text: "public int grade()",        top: "22%", left: "4%"  },
  { text: "for (int i = 0; i < n)",    top: "28%", left: "38%" },
  { text: "// O(n log n)",             top: "24%", left: "62%" },
  { text: "return result;",            top: "34%", left: "8%"  },
  { text: "assert output == expected", top: "31%", left: "52%" },
  { text: "throw new Exception()",     top: "38%", left: "30%" },
  { text: "List<Integer> ans",         top: "26%", left: "76%" },
  { text: "class Solution {",          top: "36%", left: "68%" },
];

export default function Login() {
  const { login }   = useAuth();
  const navigate    = useNavigate();
  const [form, setForm]             = useState({ username: "", password: "" });
  const [error, setError]           = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [focused, setFocused]       = useState("");

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = await login(form.username, form.password);
      navigate(user.role === "instructor" ? "/instructor" : "/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Login failed. Please check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <style>{floatKeyframes}</style>

      <div className="min-h-screen flex bg-slate-950 overflow-hidden">

        {/* ── animated background blobs ── */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden">
          <div style={{ animation: "blob1 18s ease-in-out infinite", willChange: "transform" }}
            className="absolute -top-40 -left-40 w-[520px] h-[520px] rounded-full bg-indigo-600 opacity-20 blur-[120px]" />
          <div style={{ animation: "blob2 22s ease-in-out infinite 3s", willChange: "transform" }}
            className="absolute top-1/2 -right-60 w-[480px] h-[480px] rounded-full bg-violet-600 opacity-15 blur-[120px]" />
          <div style={{ animation: "blob3 15s ease-in-out infinite 6s", willChange: "transform" }}
            className="absolute -bottom-40 left-1/3 w-[400px] h-[400px] rounded-full bg-blue-700 opacity-15 blur-[100px]" />
        </div>

        {/* ══════════ LEFT BRAND PANEL ══════════ */}
        <div className="hidden lg:flex flex-col justify-between w-[52%] relative px-16 py-14 overflow-hidden">

          {/* floating code snippets — positioned in safe zones only */}
          {codeSnippets.map(({ text, top, left }, i) => (
            <span
              key={i}
              className="absolute font-mono text-xs text-indigo-300 whitespace-nowrap select-none pointer-events-none"
              style={{
                top,
                left,
                animation: `snippetPulse ${12 + i * 2}s linear ${i * 2.5}s infinite backwards`,
              }}
            >
              {text}
            </span>
          ))}

          {/* brand */}
          <div style={{ animation: "fadeSlideIn 0.7s ease both" }}>
            <div className="flex items-center gap-3 mb-2">
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
                Grade smarter,<br />
                <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-blue-400 bg-clip-text text-transparent">
                  not harder.
                </span>
              </h1>
              <p className="mt-4 text-slate-400 text-lg leading-relaxed max-w-sm">
                AI-powered Java assignment grading with instant feedback, rubric control, and deep code analysis.
              </p>
            </div>

            {/* feature pills */}
            <div className="flex flex-wrap gap-3">
              {[
                { icon: "⚡", label: "AI-Powered Grading" },
                { icon: "🎯", label: "Rubric Control" },
                { icon: "📊", label: "Instant Feedback" },
              ].map(({ icon, label }) => (
                <span key={label}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-slate-300 text-sm font-medium backdrop-blur-sm">
                  <span>{icon}</span>{label}
                </span>
              ))}
            </div>
          </div>

          {/* bottom quote */}
          <div style={{ animation: "fadeSlideIn 0.7s ease 0.3s both" }}>
            <p className="text-slate-600 text-sm">
              Built for instructors who value their time.
            </p>
          </div>
        </div>

        {/* ══════════ RIGHT FORM PANEL ══════════ */}
        <div className="flex-1 flex items-center justify-center px-6 py-12 relative">
          <div
            className="w-full max-w-sm space-y-8"
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
              <div className="mb-7">
                <h2 className="text-2xl font-extrabold text-white">Welcome back</h2>
                <p className="text-slate-400 text-sm mt-1">Sign in to your account</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">

                {/* username */}
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
                    Username
                  </label>
                  <div className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-200
                    ${focused === "username"
                      ? "border-indigo-500 bg-indigo-950/40 ring-2 ring-indigo-500/20"
                      : "border-white/10 bg-white/5"}`}>
                    <svg className="w-4 h-4 text-slate-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
                    </svg>
                    <input
                      type="text"
                      name="username"
                      value={form.username}
                      onChange={handleChange}
                      onFocus={() => setFocused("username")}
                      onBlur={() => setFocused("")}
                      className="flex-1 bg-transparent text-white placeholder-slate-600 text-sm outline-none"
                      placeholder="your username"
                      required
                    />
                  </div>
                </div>

                {/* password */}
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
                    Password
                  </label>
                  <div className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-200
                    ${focused === "password"
                      ? "border-indigo-500 bg-indigo-950/40 ring-2 ring-indigo-500/20"
                      : "border-white/10 bg-white/5"}`}>
                    <svg className="w-4 h-4 text-slate-500 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                    </svg>
                    <input
                      type="password"
                      name="password"
                      value={form.password}
                      onChange={handleChange}
                      onFocus={() => setFocused("password")}
                      onBlur={() => setFocused("")}
                      className="flex-1 bg-transparent text-white placeholder-slate-600 text-sm outline-none"
                      placeholder="••••••••"
                      required
                    />
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
                      Signing in…
                    </span>
                  ) : "Sign In"}
                </button>
              </form>
            </div>

            <p className="text-center text-slate-500 text-sm">
              Don't have an account?{" "}
              <Link to="/register" className="text-indigo-400 hover:text-indigo-300 font-semibold transition-colors">
                Create one
              </Link>
            </p>
          </div>
        </div>

      </div>
    </>
  );
}
