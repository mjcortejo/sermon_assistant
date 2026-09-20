import { useState } from "react";
import type { DragEvent, FormEvent } from "react";
import { downloadVideo, probeVideo, uploadVideo } from "../api";
import type { Session } from "../types";

type Props = {
  session: Session;
  busy: string;
  error: string;
  onBusy: (value: string) => void;
  onError: (value: string) => void;
  onLoaded: (patch: Partial<Session>) => void;
  onContinue: () => void;
};

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

  async function afterPath(filePath: string, title: string, durationHint?: number) {
    let duration = durationHint ?? 0;
    try {
      const probed = await probeVideo(filePath);
      duration = probed.duration || duration;
    } catch {
      // Probe needs FFmpeg; the trim studio can still read duration from the video element.
    }
    onLoaded({
      sourcePath: filePath,
      videoPath: filePath,
      title: title || session.title,
      duration,
      trimStart: 0,
      trimEnd: duration || session.trimEnd,
      transcript: null,
      notes: null,
      sermonId: null,
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
    onBusy("Downloading…");
    try {
      const result = await downloadVideo(trimmed);
      const title = result.info?.title || "Sermon";
      await afterPath(result.file_path, title, result.info?.duration);
      onBusy("");
    } catch (err) {
      onBusy("");
      onError(err instanceof Error ? err.message : "Download failed.");
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    onError("");
    onBusy("Uploading…");
    try {
      const result = await uploadVideo(file);
      await afterPath(result.file_path, file.name.replace(/\.[^.]+$/, ""));
      onBusy("");
    } catch (err) {
      onBusy("");
      onError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    void onFile(event.dataTransfer.files[0]);
  }

  return (
    <section className="panel import-view">
      <header className="panel-head">
        <p className="eyebrow">Bring a sermon in</p>
        <h2>Import</h2>
        <p className="lede">
          Paste a public video URL, or drop a file from this computer. Everything stays on this
          machine.
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
        className={dragging ? "dropzone is-dragging" : "dropzone"}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          type="file"
          accept="video/*,.mp4,.webm,.mkv,.mov"
          hidden
          onChange={(event) => void onFile(event.target.files?.[0])}
        />
        <strong>Drop a video here</strong>
        <span>or click to choose a file already on disk</span>
      </label>

      {session.sourcePath ? (
        <p className="status ok" data-testid="import-loaded">
          Loaded: {session.title || session.sourcePath}
        </p>
      ) : null}
      {busy ? <p className="status">{busy}</p> : null}
      {error ? (
        <p className="status err" role="alert">
          {error}
        </p>
      ) : null}

      <div className="actions">
        <button type="button" className="btn primary" onClick={onContinue}>
          Continue to trim
        </button>
      </div>
    </section>
  );
}
