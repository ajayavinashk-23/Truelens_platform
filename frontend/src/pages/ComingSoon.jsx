import { Link } from "react-router-dom";
import { ArrowLeft, Hammer } from "lucide-react";
import Navbar from "../components/Navbar";

export default function ComingSoon({ title }) {
  return (
    <div className="min-h-screen bg-surface">
      <Navbar />
      <div className="mx-auto flex max-w-7xl flex-col items-center px-6 py-32 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-control bg-accent-50 text-accent-700">
          <Hammer size={20} />
        </span>
        <h1 className="mt-5 font-display text-2xl font-bold text-ink">
          {title}
        </h1>
        <p className="mt-2 max-w-sm text-sm text-ink-secondary">
          This screen is next up in the build. The landing page and design
          system are wired and ready to extend.
        </p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 hover:text-accent-800"
        >
          <ArrowLeft size={14} /> Back to home
        </Link>
      </div>
    </div>
  );
}
