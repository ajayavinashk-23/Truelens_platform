import { ScanFace, Image as ImageIcon, Gauge } from "lucide-react";

const PIPELINE_LABELS = {
  face_deepfake_detector: "Face deepfake detector (SigLIP2)",
  face_deepfake_detector_fallback: "Face deepfake detector (fallback, no-face mode)",
  general_ai_image_detector: "General AI image detector",
};

function pipelineLabel(pipelineUsed) {
  return PIPELINE_LABELS[pipelineUsed] ?? pipelineUsed;
}

function MetricBar({ label, value, max = 100, suffix = "" }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-ink-secondary">{label}</span>
        <span className="font-medium text-ink">
          {value}
          {suffix}
        </span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-secondary">
        <div
          className="h-full rounded-full bg-accent-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Renders quality_score / blur_score / brightness / contrast / resolution
 * / pipeline_used for image reports (and, loosely, video reports which
 * carry frame-level pipeline info instead). No-op if none of that data
 * is present, so it's safe to render unconditionally from the report
 * panel for image/video reports.
 */
export default function QualityMetricsCard({ report }) {
  const hasQuality = report.quality_score !== undefined || report.pipeline_used;
  if (!hasQuality) return null;

  return (
    <div className="rounded-card border border-border bg-white p-6 shadow-soft">
      <div className="flex items-center gap-2">
        <Gauge size={16} className="text-accent-700" />
        <h3 className="font-display text-base font-semibold text-ink">
          Pipeline &amp; input quality
        </h3>
      </div>

      {report.pipeline_used && (
        <div className="mt-3 flex items-center gap-2 text-sm">
          <ScanFace size={15} className="shrink-0 text-ink-secondary" />
          <span className="text-ink-secondary">Detector used:</span>
          <span className="font-medium text-ink">{pipelineLabel(report.pipeline_used)}</span>
        </div>
      )}

      {report.face_count !== undefined && report.face_count > 0 && (
        <div className="mt-1.5 flex items-center gap-2 text-sm">
          <ImageIcon size={15} className="shrink-0 text-ink-secondary" />
          <span className="text-ink-secondary">Faces analyzed:</span>
          <span className="font-medium text-ink">{report.face_count}</span>
        </div>
      )}

      {report.quality_score !== undefined && (
        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
          <MetricBar label="Quality score" value={report.quality_score} suffix="/100" />
          {report.blur_score !== undefined && (
            <MetricBar label="Sharpness" value={Math.min(report.blur_score, 300)} max={300} />
          )}
          {report.confidence !== undefined && (
            <MetricBar label="Confidence" value={report.confidence} suffix="%" />
          )}
          {report.resolution && (
            <div>
              <p className="text-xs text-ink-secondary">Resolution</p>
              <p className="mt-1.5 text-sm font-medium text-ink">
                {report.resolution.width}×{report.resolution.height}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
