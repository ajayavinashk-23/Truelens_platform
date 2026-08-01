import { motion } from "framer-motion";
import { cn } from "../lib/utils";

const variants = {
  primary:
    "bg-accent-700 text-white hover:bg-accent-800 shadow-soft",
  secondary:
    "bg-white text-ink border border-border hover:border-accent-700/40 hover:bg-accent-50",
  ghost: "bg-transparent text-ink-secondary hover:text-ink hover:bg-surface-secondary",
};

/**
 * Standard button. Hover: scale 1 -> 1.02, 180ms ease-out (per motion spec).
 */
export default function Button({
  as: Component = "button",
  variant = "primary",
  className,
  children,
  disabled = false,
  ...props
}) {
  return (
    <motion.div
      className="inline-block"
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      <Component
        disabled={disabled}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-control px-5 py-2.5 text-sm font-medium transition-colors duration-150",
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </Component>
    </motion.div>
  );
}
