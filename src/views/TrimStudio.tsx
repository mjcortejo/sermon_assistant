import { useEffect, useRef } from "react";
import { DualRange } from "../components/DualRange";
import { formatTime, mediaUrl, type Session } from "../types";

type Props = {
  session: Session;
  busy: string;
  error: string;
  onChange: (patch: Partial<Session>) => void;
  onTrim: () => void;
  onContinue: () => void;
};

export function TrimStudio({ session, busy, error, onChange, onTrim, onContinue }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const src = mediaUrl(session.videoPath);
  const hasClip = session.duration > 0;
  const max = hasClip ? session.duration : 1;
  const start = hasClip ? session.trimStart : 0;
  const end = hasClip ? session.trimEnd || max : 0;

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onMeta = () => {
      if (!session.duration && Number.isFinite(video.duration)) {
        onChange({ duration: video.duration, trimEnd: video.duration });
      }
    };
    video.addEventListener("loadedmetadata", onMeta);
    return () => video.removeEventListener("loadedmetadata", onMeta);
  }, [session.duration, src, onChange]);

  return (
    <section className="panel trim-view">
      <header className="panel-head">
        <p className="eyebrow">Choose the portion to study</p>
        <h2>Trim studio</h2>
        <p className="lede">
          Drag both handles to keep only the sermon, then trim. Lossless cut runs locally through
          FFmpeg.
        </p>
      </header>

      <div className="player-shell">
        {src ? (
          <video
            ref={videoRef}
            src={src}
            controls
            playsInline
            data-testid="trim-player"
          />
        ) : (
          <div className="player-empty" data-testid="trim-empty">
            No video loaded yet. Import a sermon first, or inspect the trim controls below.
          </div>
        )}
      </div>

      <div className="trim-controls">
        <div className="trim-times">
          <span>
            Start <strong>{formatTime(start)}</strong>
          </span>
          <span>
            End <strong>{formatTime(end)}</strong>
          </span>
        </div>
        <DualRange
          min={0}
          max={max}
          start={start}
          end={end}
          onChange={(nextStart, nextEnd) => onChange({ trimStart: nextStart, trimEnd: nextEnd })}
        />
        <div className="actions">
          <button type="button" className="btn" onClick={onTrim} disabled={!session.videoPath || Boolean(busy)}>
            Trim selection
          </button>
          <button type="button" className="btn primary" onClick={onContinue}>
            Continue to study
          </button>
        </div>
      </div>

      {busy ? <p className="status">{busy}</p> : null}
      {error ? (
        <p className="status err" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
