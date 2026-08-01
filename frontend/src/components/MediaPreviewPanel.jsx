import { motion } from "framer-motion";

const CORNER_POSITIONS = [
  "top-3 left-3 border-t-2 border-l-2",
  "top-3 right-3 border-t-2 border-r-2",
  "bottom-3 left-3 border-b-2 border-l-2",
  "bottom-3 right-3 border-b-2 border-r-2",
];

export default function MediaPreviewPanel({
  mediaType,
  previewUrl,
  fileName,
  isAnalyzing,
}) {
  return (
    <div className="overflow-hidden rounded-card border border-border bg-white shadow-soft">
      <div className="border-b border-border px-5 py-3">
        <p className="text-sm font-medium text-ink">Uploaded media</p>
        <p className="truncate text-xs text-ink-secondary">{fileName}</p>
      </div>

      <div className="relative flex min-h-[280px] items-center justify-center bg-ink p-4">
        {mediaType === "image" && (
          <img
            src={previewUrl}
            alt="Uploaded media"
            className="max-h-[420px] rounded-control object-contain"
          />
        )}
        {mediaType === "video" && (
          <video
            src={previewUrl}
            controls
            className="max-h-[420px] w-full rounded-control"
          />
        )}
        {mediaType === "audio" && (
          <div className="flex w-full flex-col items-center gap-6 py-10">
            <div className="flex h-16 items-end gap-1">
              {Array.from({ length: 28 }).map((_, i) => (
                <motion.span
                  key={i}
                  className="w-1.5 rounded-full bg-accent-200/70"
                  animate={
                    isAnalyzing
                      ? { height: [6, 10 + ((i * 13) % 40), 6] }
                      : { height: 6 + ((i * 7) % 24) }
                  }
                  transition={
                    isAnalyzing
                      ? {
                          duration: 0.9 + (i % 5) * 0.1,
                          repeat: Infinity,
                          ease: "easeInOut",
                        }
                      : { duration: 0 }
                  }
                />
              ))}
            </div>
            <audio src={previewUrl} controls className="w-full max-w-sm" />
          </div>
        )}

        {/* Analysis overlays: only for visual media, only while running */}
        {isAnalyzing && (mediaType === "image" || mediaType === "video") && (
          <>
            {CORNER_POSITIONS.map((pos, i) => (
              <div
                key={i}
                className={`pointer-events-none absolute h-6 w-6 border-accent-200/80 ${pos}`}
              />
            ))}
            <motion.div
              className="pointer-events-none absolute inset-x-4 h-px bg-accent-200/80"
              style={{ boxShadow: "0 0 8px 1px rgba(153,246,228,0.6)" }}
              animate={{ top: ["8%", "92%", "8%"] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
            />
            <div className="pointer-events-none absolute bottom-2 left-2 flex items-center gap-1.5 rounded-full bg-black/40 px-2.5 py-1 text-[11px] font-medium text-white backdrop-blur-sm">
              <span className="h-1.5 w-1.5 animate-pulseSoft rounded-full bg-accent-200" />
              Scanning
            </div>
          </>
        )}
      </div>
    </div>
  );
}
