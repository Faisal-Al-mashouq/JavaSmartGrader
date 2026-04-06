import { Link } from "react-router-dom";

const variants = {
  neutral:
    "border-slate-200 dark:border-white/[0.1] text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-700/80 hover:text-slate-900 dark:hover:text-white shadow-sm",
  primary:
    "border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/10 hover:bg-indigo-100 dark:hover:bg-indigo-500/20 hover:text-indigo-700 dark:hover:text-indigo-200",
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
