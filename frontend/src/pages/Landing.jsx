import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import Button from "../components/Button";
import HeroPreviewCard from "../components/HeroPreviewCard";
import MediaTypeCard from "../components/MediaTypeCard";
import StepTimeline from "../components/StepTimeline";
import TrustGauge from "../components/TrustGauge";
import { MEDIA_TYPE_LIST } from "../lib/mediaTypes";

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface">
      <Navbar />

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-6 pb-20 pt-16 md:pt-24">
        <div className="grid items-center gap-14 md:grid-cols-2">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-secondary px-3 py-1 text-xs font-medium text-ink-secondary">
              <ShieldCheck size={13} className="text-accent-700" />
              Built for investigators & newsrooms
            </span>
            <h1 className="text-balance mt-5 font-display text-4xl font-extrabold leading-[1.1] text-ink md:text-5xl">
              Know what's real before you publish it.
            </h1>
            <p className="mt-5 max-w-md text-base leading-relaxed text-ink-secondary">
              Truelens runs images, video, and audio through a transparent
              forensic pipeline, then hands you a single deepfake-probability
              score and an evidence-backed report, not just a fake-or-real
              guess.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button variant="primary" onClick={() => navigate("/select")}>
                Start an analysis
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  document
                    .getElementById("how-it-works")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
              >
                See how it works
              </Button>
            </div>
          </div>

          <div className="flex justify-center md:justify-end">
            <HeroPreviewCard />
          </div>
        </div>
      </section>

      {/* Media type selection */}
      <section id="media-types" className="border-t border-border bg-surface-secondary">
        <div className="mx-auto max-w-7xl px-6 py-16">
          <div className="max-w-lg">
            <h2 className="font-display text-2xl font-bold text-ink">
              Start with your media type
            </h2>
            <p className="mt-2 text-sm text-ink-secondary">
              Each media type runs through its own dedicated detection
              pipeline and pretrained model.
            </p>
          </div>
          <div className="mt-8 grid gap-5 sm:grid-cols-3">
            {MEDIA_TYPE_LIST.map((type) => (
              <MediaTypeCard
                key={type.id}
                icon={type.icon}
                title={type.title}
                description={type.description}
                onClick={() => navigate(`/select?type=${type.id}`)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="mx-auto max-w-7xl px-6 py-20">
        <div className="max-w-lg">
          <h2 className="font-display text-2xl font-bold text-ink">
            How the pipeline works
          </h2>
          <p className="mt-2 text-sm text-ink-secondary">
            Every upload moves through the same four stages, visible in real
            time on the dashboard.
          </p>
        </div>
        <div className="mt-8">
          <StepTimeline />
        </div>
      </section>

      {/* Deepfake probability explainer */}
      <section id="report" className="border-t border-border bg-surface-secondary">
        <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 md:grid-cols-2 md:items-center">
          <div>
            <h2 className="font-display text-2xl font-bold text-ink">
              A score you can defend in a byline
            </h2>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-secondary">
              One percentage, not two overlapping numbers. The deepfake
              probability condenses artifact checks and pattern matching into
              a single 0–100 figure, with the underlying reasoning always one
              click away.
            </p>
            <dl className="mt-7 space-y-4">
              {[
                { range: "0–20", label: "Likely authentic", tone: "text-success" },
                { range: "21–50", label: "Needs manual verification", tone: "text-warning" },
                { range: "51–100", label: "Likely manipulated", tone: "text-danger" },
              ].map((row) => (
                <div
                  key={row.range}
                  className="flex items-center gap-4 rounded-control border border-border bg-white px-4 py-3"
                >
                  <dt className="w-16 shrink-0 font-mono text-sm text-ink-secondary">
                    {row.range}
                  </dt>
                  <dd className={`text-sm font-semibold ${row.tone}`}>
                    {row.label}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="flex justify-center gap-6 rounded-card border border-border bg-white p-8 shadow-soft"
          >
            <TrustGauge score={8} label="Sample: Image" />
            <TrustGauge score={34} label="Sample: Audio" />
            <TrustGauge score={82} label="Sample: Video" />
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
