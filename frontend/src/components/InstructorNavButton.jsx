import { Link } from "react-router-dom";

const variants = {
  neutral:
    "border-white/[0.1] text-slate-300 bg-slate-800/60 hover:bg-slate-700/80 hover:text-white",
  primary:
    "border-indigo-500/30 text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 hover:text-indigo-200",
};

export default function InstructorNavButton({ to, children, variant = "neutral", className = "" }) {
  return (
    <Link
      to={to}
      className={`inline-flex items-center justify-center text-center font-semibold text-xs px-3 py-1.5 rounded-lg border transition-all duration-200 shrink-0 ${variants[variant] ?? variants.neutral} ${className}`.trim()}
    >
      {children}
    </Link>
  );
}
