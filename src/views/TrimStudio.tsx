import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { DualRange } from "../components/DualRange";
import { formatTime, mediaUrl, parseClockTime, type Session } from "../types";

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
  const src = mediaUrl(session.sourcePath || session.videoPath);
  const [sourceDuration, setSourceDuration] = useState(0);
  const hasClip = sourceDuration > 0 || session.duration > 0;
  const max = sourceDuration || (hasClip ? session.duration : 1) || 1;
  const start = hasClip ? session.trimStart : 0;
  const end = hasClip ? session.trimEnd || max : 0;
  const [startText, setStartText] = useState(formatTime(start));
  const [endText, setEndText] = useState(formatTime(end));

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onMeta = () => {
      if (!Number.isFinite(video.duration) || video.duration <= 0) return;
      setSourceDuration(video.duration);
      if (!session.trimEnd) {
        onChange({ trimEnd: video.duration });
      }
    };
    video.addEventListener("loadedmetadata", onMeta);
    return () => video.removeEventListener("loadedmetadata", onMeta);
  }, [session.trimEnd, src, onChange]);

  useEffect(() => {
    setStartText(formatTime(start));
  }, [start]);

  useEffect(() => {
    setEndText(formatTime(end));
  }, [end]);

  function seekTo(seconds: number) {
    if (videoRef.current) videoRef.current.currentTime = seconds;
  }

  function commitStart() {
    const parsed = parseClockTime(startText);
    if (parsed == null) {
      setStartText(formatTime(start));
      return;
    }
    const next = Math.min(Math.max(0, parsed), Math.max(end - 0.1, 0));
    onChange({ trimStart: next, trimEnd: end });
    seekTo(next);
  }

  function commitEnd() {
    const parsed = parseClockTime(endText);
    if (parsed == null) {
      setEndText(formatTime(end));
      return;
    }
    const next = Math.max(Math.min(parsed, max), start + 0.1);
    onChange({ trimStart: start, trimEnd: next });
    seekTo(next);
  }

  function onClockKey(event: KeyboardEvent<HTMLInputElement>, which: "start" | "end") {
    if (event.key === "Enter") {
      event.preventDefault();
      if (which === "start") commitStart();
      else commitEnd();
      event.currentTarget.blur();
    }
  }

  return (
    <section className="panel trim-view">
      <header className="panel-head">
        <p className="eyebrow">Choose the portion to study</p>
        <h2>Trim studio</h2>
        <p className="lede">
          Type an exact start and end time, or drag the handles. Then continue — the study step plays
          that cut, not the full download.
        </p>
      </header>

      <div className="player-shell">
        {src ? (
          <video ref={videoRef} src={src} controls playsInline data-testid="trim-player" />
        ) : (
          <div className="player-empty" data-testid="trim-empty">
            No video loaded yet. Import a sermon first, or inspect the trim controls below.
          </div>
        )}
      </div>

      <div className="trim-controls">
        <div className="trim-times">
          <label className="trim-clock">
            <span>Start</span>
            <input
              type="text"
              inputMode="text"
              name="trim-start"
              data-testid="trim-start-input"
              aria-label="Trim start time"
              placeholder="m:ss"
              value={startText}
              onChange={(event) => setStartText(event.target.value)}
              onBlur={commitStart}
              onKeyDown={(event) => onClockKey(event, "start")}
            />
          </label>
          <label className="trim-clock">
            <span>End</span>
            <input
              type="text"
              inputMode="text"
              name="trim-end"
              data-testid="trim-end-input"
              aria-label="Trim end time"
              placeholder="h:mm:ss or m:ss"
              value={endText}
              onChange={(event) => setEndText(event.target.value)}
              onBlur={commitEnd}
              onKeyDown={(event) => onClockKey(event, "end")}
            />
          </label>
        </div>
        <DualRange
          min={0}
          max={max}
          start={start}
          end={end}
          onChange={(nextStart, nextEnd) => onChange({ trimStart: nextStart, trimEnd: nextEnd })}
        />
        <div className="actions">
          <button type="button" className="btn" onClick={onTrim} disabled={!src || Boolean(busy)}>
            Trim selection
          </button>
          <button type="button" className="btn primary" onClick={onContinue} disabled={!src || Boolean(busy)}>
            Trim and continue
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
