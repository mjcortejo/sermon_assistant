import { useState } from "react";
import type { DragEvent, FormEvent } from "react";
import { downloadVideoLive, probeVideo, uploadVideo } from "../api";
import { formatBytes, formatEta, type ImportProgress, type Session } from "../types";

type Props = {
  session: Session;
  busy: string;
  error: string;
  onBusy: (value: string) => void;
  onError: (value: string) => void;
  onLoaded: (patch: Partial<Session> & { sourceUrl?: string }) => void;
  onContinue: () => void;
};

function progressCopy(progress: ImportProgress): string {
  const parts = [progress.message || "Working…"];
  if (progress.percent != null && Number.isFinite(progress.percent)) {
    parts.push(`${Math.round(progress.percent)}%`);
  }
  if (progress.downloaded_bytes != null && progress.total_bytes) {
    parts.push(`${formatBytes(progress.downloaded_bytes)} of ${formatBytes(progress.total_bytes)}`);
  } else if (progress.downloaded_bytes) {
    parts.push(formatBytes(progress.downloaded_bytes));
  }
  if (progress.speed) parts.push(`${formatBytes(progress.speed)}/s`);
  if (progress.eta != null && progress.eta >= 1) parts.push(`${formatEta(progress.eta)} left`);
  return parts.join(" · ");
}

export function ImportView({
  session,
  busy,
  error,
  onBusy,
  onError,
  onLoaded,
  onContinue,
}: Props) {
  const [url, setUrl] = useState("");
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<ImportProgress | null>(null);

  async function afterPath(filePath: string, title: string, durationHint?: number, sourceUrl = "") {
    let duration = durationHint ?? 0;
    try {
      const probed = await probeVideo(filePath);
      duration = probed.duration || duration;
    } catch {
      // Probe needs FFmpeg; the trim studio can still read duration from the video element.
    }
    onLoaded({
      sourcePath: filePath,
      sourceUrl,
      videoPath: filePath,
      title: title || session.title,
      duration,
      trimStart: 0,
      trimEnd: duration || 0,
      transcript: null,
      notes: null,
      userNotes: "",
      chatLog: [],
    });
  }

  async function onDownload(event: FormEvent) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      onError("Paste a YouTube or public Facebook video URL.");
      return;
    }
    onError("");
    setProgress({ phase: "resolving", percent: 0, message: "Looking up the video…" });
    onBusy("Downloading…");
    try {
      const result = await downloadVideoLive(trimmed, setProgress);
      const title = result.info?.title || "Sermon";
      setProgress({ phase: "processing", percent: 100, message: "Reading duration…" });
      await afterPath(result.file_path, title, result.info?.duration, trimmed);
      setProgress(null);
      onBusy("");
    } catch (err) {
      setProgress(null);
      onBusy("");
      onError(err instanceof Error ? err.message : "Download failed.");
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    onError("");
    setProgress({ phase: "uploading", percent: 0, message: "Uploading…" });
    onBusy("Uploading…");
    try {
      const result = await uploadVideo(file, setProgress);
      setProgress({ phase: "processing", percent: 100, message: "Reading duration…" });
      await afterPath(result.file_path, file.name.replace(/\.[^.]+$/, ""));
      setProgress(null);
      onBusy("");
    } catch (err) {
      setProgress(null);
      onBusy("");
      onError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    if (busy) return;
    void onFile(event.dataTransfer.files[0]);
  }

  return (
    <section className="panel import-view">
      <header className="panel-head">
        <p className="eyebrow">Bring a sermon in</p>
        <h2>Import</h2>
        <p className="lede">
          Paste a sermon URL or drop a file. Saved studies stay in the sidebar so you can reopen them anytime.
        </p>
      </header>

      <form className="url-row" onSubmit={onDownload}>
        <label className="field">
          <span>Video URL</span>
          <input
            name="sermon-url"
            type="url"
            placeholder="https://www.youtube.com/watch?v=…"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            autoComplete="off"
          />
        </label>
        <button type="submit" className="btn primary" disabled={Boolean(busy)}>
          Download
        </button>
      </form>

      <label
        className={dragging ? "dropzone is-dragging" : busy ? "dropzone is-busy" : "dropzone"}
        onDragOver={(event) => {
          event.preventDefault();
          if (busy) return;
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          type="file"
          accept="video/*,.mp4,.webm,.mkv,.mov"
          hidden
          disabled={Boolean(busy)}
          onChange={(event) => void onFile(event.target.files?.[0])}
        />
        <strong>Drop a video here</strong>
        <span>or click to choose a file already on disk</span>
      </label>

      {session.sourcePath ? (
        <p className="status ok" data-testid="import-loaded">
          {session.projectId ? `Project saved: ${session.title}` : `Loaded: ${session.title || session.sourcePath}`}
        </p>
      ) : null}
      {progress ? (
        <div className="import-progress" data-testid="import-progress">
          <div className={progress.percent == null ? "progress-track is-indeterminate" : "progress-track"}>
            <div
              className="progress-fill"
              style={progress.percent != null ? { width: `${Math.min(100, Math.max(0, progress.percent))}%` } : undefined}
            />
          </div>
          <p>{progressCopy(progress)}</p>
        </div>
      ) : busy ? (
        <p className="status">{busy}</p>
      ) : null}
      {error ? (
        <p className="status err" role="alert">
          {error}
        </p>
      ) : null}

      <div className="actions">
        <button type="button" className="btn primary" onClick={onContinue} disabled={!session.sourcePath}>
          Continue to trim
        </button>
      </div>
    </section>
  );
}
