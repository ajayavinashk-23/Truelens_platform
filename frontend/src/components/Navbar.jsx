import { Link, useNavigate } from "react-router-dom";
import { ScanEye } from "lucide-react";
import Button from "./Button";

const NAV_LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Forensics report", href: "#report" },
  { label: "Media types", href: "#media-types" },
];

export default function Navbar() {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white/80 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-control bg-accent-700 text-white">
            <ScanEye size={18} strokeWidth={2.25} />
          </span>
          <span className="font-display text-[17px] font-bold text-ink">
            Truelens
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-ink-secondary transition-colors hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Button variant="ghost" className="hidden sm:inline-flex">
            Sign in
          </Button>
          <Button variant="primary" onClick={() => navigate("/select")}>
            Start analysis
          </Button>
        </div>
      </div>
    </header>
  );
}
