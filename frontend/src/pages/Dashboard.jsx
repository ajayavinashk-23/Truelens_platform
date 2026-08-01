import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams, Link } from "react-router-dom";
import { ArrowLeft, FileWarning } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import Button from "../components/Button";
import ProgressSteps from "../components/ProgressSteps";
import PipelineSteps from "../components/PipelineSteps";
import MediaPreviewPanel from "../components/MediaPreviewPanel";
import ForensicsReportPanel from "../components/ForensicsReportPanel";
import { PIPELINE_STEPS, STEP_INTERVAL_MS } from "../lib/pipelineSteps";
import { generateMockReport } from "../lib/mockAnalysis";
import { analyzeMedia, BackendUnreachableError } from "../lib/api";
import { addToHistory, getHistory } from "../lib/detectionHistory";

export default function Dashboard() {
  const { state } = useLocation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const typeId = searchParams.get("type");

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [usedDemoFallback, setUsedDemoFallback] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const hasStarted = useRef(false);

  const hasMedia = state?.previewUrl && typeId;

  useEffect(() => {
    if (!hasMedia || hasStarted.current) return;
    hasStarted.current = true;

    const timers = PIPELINE_STEPS.map((_, i) =>
      setTimeout(() => setCurrentStepIndex(i), i * STEP_INTERVAL_MS)
    );

    // Keep the pipeline animation on screen for at least this long, even if
    // the real backend responds faster — the step-by-step reveal is part of
    // the product's design language, not just a loading spinner.
    const minDisplayMs = PIPELINE_STEPS.length * STEP_INTERVAL_MS + 300;
    const minDisplay = new Promise((resolve) => setTimeout(resolve, minDisplayMs));

    // Run real inference in parallel with the animation. If the FastAPI
    // backend isn't reachable (e.g. not started yet during a demo), fall
    // back to the mock generator so the flow never dead-ends — but flag it
    // clearly so nobody mistakes a demo report for a real model result.
    const analysisPromise = state.file
      ? analyzeMedia(typeId, state.file).catch((err) => {
          if (err instanceof BackendUnreachableError) {
            // No backend running at all — this is the only situation the
            // demo report is meant to stand in for.
            console.warn(
              "Live inference unavailable, falling back to demo report:",
              err.message
            );
            setUsedDemoFallback(true);
            return generateMockReport(typeId, state.fileName);
          }
          // The backend WAS reached but returned an error (a real bug, bad
          // input, model exception, etc.). Previously this was also
          // swapped for a randomized demo report, which meant the same
          // image could come back with a different, fabricated verdict
          // every time the backend happened to fail. Surface it as a real
          // error instead.
          console.error("Analysis failed:", err.message);
          setAnalysisError(err.message);
          return null;
        })
      : (() => {
          setUsedDemoFallback(true);
          return Promise.resolve(generateMockReport(typeId, state.fileName));
        })();

    Promise.all([minDisplay, analysisPromise]).then(([, result]) => {
      if (result === null) return; // analysisError already set, nothing to render
      setReport(result);
      setHistory(addToHistory(result));
    });

    return () => {
      timers.forEach(clearTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMedia]);

  useEffect(() => {
    setHistory(getHistory());
  }, []);

  if (!hasMedia) {
    return (
      <div className="flex min-h-screen flex-col bg-surface">
        <Navbar />
        <div className="mx-auto flex max-w-7xl flex-1 flex-col items-center justify-center px-6 py-24 text-center">
          <FileWarning size={28} className="text-ink-secondary" />
          <h1 className="mt-4 font-display text-xl font-bold text-ink">
            No media to analyze
          </h1>
          <p className="mt-2 max-w-sm text-sm text-ink-secondary">
            Upload a file first so the dashboard has something to run through
            the detection pipeline.
          </p>
          <Link
            to="/select"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 hover:text-accent-800"
          >
            <ArrowLeft size={14} /> Start an analysis
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  const isAnalyzing = !report && !analysisError;

  if (analysisError) {
    return (
      <div className="flex min-h-screen flex-col bg-surface">
        <Navbar />
        <div className="mx-auto flex max-w-7xl flex-1 flex-col items-center justify-center px-6 py-24 text-center">
          <FileWarning size={28} className="text-danger" />
          <h1 className="mt-4 font-display text-xl font-bold text-ink">
            Analysis failed
          </h1>
          <p className="mt-2 max-w-md text-sm text-ink-secondary">{analysisError}</p>
          <Link
            to="/select"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 hover:text-accent-800"
          >
            <ArrowLeft size={14} /> Try another file
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <Navbar />

      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-14">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <ProgressSteps current={3} />
          {report && (
            <Button variant="secondary" onClick={() => navigate("/select")}>
              New analysis
            </Button>
          )}
        </div>

        <h1 className="mt-8 font-display text-3xl font-bold text-ink">
          Forensics dashboard
        </h1>
        <p className="mt-2 text-sm text-ink-secondary">
          {isAnalyzing
            ? "Running your media through the detection pipeline..."
            : "Compare the original media against the forensic findings below."}
        </p>

        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          {/* Media preview: always visible, one side */}
          <div className="lg:sticky lg:top-20 lg:self-start">
            <MediaPreviewPanel
              mediaType={typeId}
              previewUrl={state.previewUrl}
              fileName={state.fileName}
              isAnalyzing={isAnalyzing}
            />
          </div>

          {/* Analysis panel: pipeline while running, report once complete */}
          <div>
            {isAnalyzing ? (
              <PipelineSteps currentStepIndex={currentStepIndex} />
            ) : (
              <ForensicsReportPanel
                report={report}
                history={history}
                demoMode={usedDemoFallback}
              />
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
