import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { cn } from "../lib/utils";

export default function MediaTypeCard({
  icon: Icon,
  title,
  description,
  onClick,
  highlighted = false,
}) {
  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.99 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className={cn(
        "group flex flex-col items-start gap-4 rounded-card border bg-white p-6 text-left shadow-soft transition-colors hover:border-accent-700/40",
        highlighted ? "border-accent-700 ring-1 ring-accent-700" : "border-border"
      )}
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-control bg-accent-50 text-accent-700">
        <Icon size={20} strokeWidth={2} />
      </span>
      <div>
        <h3 className="font-display text-base font-semibold text-ink">
          {title}
        </h3>
        <p className="mt-1 text-sm text-ink-secondary">{description}</p>
      </div>
      <span className="mt-1 flex items-center gap-1 text-sm font-medium text-accent-700 opacity-0 transition-opacity group-hover:opacity-100">
        Analyze {title.toLowerCase()} <ArrowRight size={14} />
      </span>
    </motion.button>
  );
}
