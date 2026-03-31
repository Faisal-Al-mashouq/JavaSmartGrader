import { Link } from "react-router-dom";

const variants = {
  neutral:
    "border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/80",
  primary:
    "border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 bg-indigo-50/80 dark:bg-indigo-950/40 hover:bg-indigo-100/80 dark:hover:bg-indigo-900/40",
};

/**
 * Router Link styled as a compact button for instructor in-page navigation.
 */
export default function InstructorNavButton({
  to,
  children,
  variant = "neutral",
  className = "",
}) {
  return (
    <Link
      to={to}
      className={`inline-flex items-center justify-center text-center font-semibold text-xs px-3 py-1.5 rounded-lg border transition-colors shrink-0 ${variants[variant] ?? variants.neutral} ${className}`.trim()}
    >
      {children}
    </Link>
  );
}
