import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, X, FileWarning, ArrowLeft } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import Button from "../components/Button";
import ProgressSteps from "../components/ProgressSteps";
import { MEDIA_TYPES, isAcceptedFile } from "../lib/mediaTypes";
import { cn } from "../lib/utils";

export default function Upload() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const typeId = searchParams.get("type");
  const typeConfig = MEDIA_TYPES[typeId];

  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  if (!typeConfig) {
    return (
      <div className="flex min-h-screen flex-col bg-surface">
        <Navbar />
        <div className="mx-auto flex max-w-7xl flex-1 flex-col items-center justify-center px-6 py-24 text-center">
          <FileWarning size={28} className="text-ink-secondary" />
          <h1 className="mt-4 font-display text-xl font-bold text-ink">
            No media type selected
          </h1>
          <p className="mt-2 max-w-sm text-sm text-ink-secondary">
            Pick a media type first so we know which detection pipeline to
            load.
          </p>
          <Link
            to="/select"
            className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-accent-700 hover:text-accent-800"
          >
            <ArrowLeft size={14} /> Choose a media type
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  const Icon = typeConfig.icon;

  function handleFile(candidate) {
    setError(null);
    if (!isAcceptedFile(candidate, typeConfig)) {
      setError(`That file type isn't supported for ${typeConfig.title.toLowerCase()} analysis. ${typeConfig.hint}.`);
      return;
    }
    const maxBytes = typeConfig.maxSizeMB * 1024 * 1024;
    if (candidate.size > maxBytes) {
      setError(`File is larger than ${typeConfig.maxSizeMB}MB. ${typeConfig.hint}.`);
      return;
    }
    setFile(candidate);
    setPreviewUrl(URL.createObjectURL(candidate));
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) handleFile(dropped);
  }

  function clearFile() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleAnalyze() {
    if (!file) return;
    navigate(`/dashboard?type=${typeId}`, {
      state: {
        file,
        fileName: file.name,
        fileSize: file.size,
        fileKind: file.type,
        previewUrl,
      },
    });
  }

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <Navbar />

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-14">
        <ProgressSteps current={2} />

        <div className="mt-10 flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-ink">
              Upload your {typeConfig.title.toLowerCase()}
            </h1>
            <p className="mt-2 text-sm text-ink-secondary">{typeConfig.hint}</p>
          </div>
          <Link
            to="/select"
            className="mt-2 flex shrink-0 items-center gap-1.5 text-sm font-medium text-ink-secondary hover:text-ink"
          >
            <ArrowLeft size={14} /> Change type
          </Link>
        </div>

        {!file ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "mt-8 flex cursor-pointer flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed bg-white px-6 py-16 text-center transition-colors duration-150",
              isDragging
                ? "border-accent-700 bg-accent-50"
                : "border-border hover:border-accent-700/50"
            )}
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-control bg-accent-50 text-accent-700">
              <UploadCloud size={22} />
            </span>
            <p className="text-sm font-medium text-ink">
              Drag and drop your file here, or click to browse
            </p>
            <p className="text-xs text-ink-secondary">{typeConfig.hint}</p>
            <input
              ref={inputRef}
              type="file"
              accept={typeConfig.acceptAttr}
              className="hidden"
              onChange={(e) => {
                const selected = e.target.files?.[0];
                if (selected) handleFile(selected);
              }}
            />
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="mt-8 overflow-hidden rounded-card border border-border bg-white shadow-soft"
          >
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <div className="flex items-center gap-2 text-sm font-medium text-ink">
                <Icon size={16} className="text-accent-700" />
                {file.name}
                <span className="font-normal text-ink-secondary">
                  ({(file.size / (1024 * 1024)).toFixed(1)} MB)
                </span>
              </div>
              <button
                onClick={clearFile}
                aria-label="Remove file"
                className="flex h-7 w-7 items-center justify-center rounded-control text-ink-secondary transition-colors hover:bg-surface-secondary hover:text-ink"
              >
                <X size={15} />
              </button>
            </div>

            <div className="flex items-center justify-center bg-ink p-4">
              {typeId === "image" && (
                <img
                  src={previewUrl}
                  alt="Upload preview"
                  className="max-h-80 rounded-control object-contain"
                />
              )}
              {typeId === "video" && (
                <video
                  src={previewUrl}
                  controls
                  className="max-h-80 w-full rounded-control"
                />
              )}
              {typeId === "audio" && (
                <div className="w-full py-8">
                  <audio src={previewUrl} controls className="w-full" />
                </div>
              )}
            </div>
          </motion.div>
        )}

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="mt-4 flex items-start gap-2 rounded-control border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger"
            >
              <FileWarning size={16} className="mt-0.5 shrink-0" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-8 flex justify-end gap-3">
          {file && (
            <Button variant="secondary" onClick={clearFile}>
              Replace file
            </Button>
          )}
          <Button
            variant="primary"
            onClick={handleAnalyze}
            disabled={!file}
            className={!file ? "cursor-not-allowed opacity-50" : ""}
          >
            Run forensic analysis
          </Button>
        </div>
      </main>

      <Footer />
    </div>
  );
}
