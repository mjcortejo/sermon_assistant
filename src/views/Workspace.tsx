import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { formatTime, mediaUrl, type Session } from "../types";

type Props = {
  session: Session;
  busy: string;
  error: string;
  transcribing: boolean;
  capturing?: boolean;
  onUserNotes: (value: string) => void;
  onGenerate: () => void;
  onTranscribe: () => void;
  onChat: (message: string) => void;
  onCaptureFrame: (timestamp: number) => void;
};

export function Workspace({
  session,
  busy,
  error,
  transcribing,
  capturing = false,
  onUserNotes,
  onGenerate,
  onTranscribe,
  onChat,
  onCaptureFrame,
}: Props) {
  const [draft, setDraft] = useState("");
  const src = mediaUrl(session.videoPath);
  const notes = session.notes;
  const videoRef = useRef<HTMLVideoElement>(null);
  const cuesRef = useRef<HTMLOListElement>(null);
  const segments = session.transcript?.segments || [];

  function send(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    onChat(text);
  }

  useEffect(() => {
    if (!transcribing) return;
    cuesRef.current?.lastElementChild?.scrollIntoView({ block: "nearest" });
  }, [segments.length, transcribing]);

  return (
    <section className="workspace">
      <div className="workspace-left">
        <div className="player-shell compact">
          {src ? (
            <video ref={videoRef} src={src} controls playsInline data-testid="study-player" />
          ) : (
            <div className="player-empty">No trimmed clip yet.</div>
          )}
          <div className="player-toolbar">
            <button
              type="button"
              className="btn small"
              data-testid="capture-frame"
              onClick={() => {
                const time = videoRef.current?.currentTime ?? 0;
                videoRef.current?.pause();
                onCaptureFrame(time);
              }}
              disabled={!session.videoPath || capturing}
            >
              {capturing ? "Reading text…" : "Capture on-screen text"}
            </button>
            <p className="muted">Pause on a slide or verse, then capture the current frame.</p>
          </div>
        </div>
        <div className="transcript-card">
          <div className="card-head">
            <h3>Transcript {transcribing ? <span className="live-pill">Live</span> : null}</h3>
            <button
              type="button"
              className="btn small"
              onClick={onTranscribe}
              disabled={!session.videoPath || transcribing}
            >
              {transcribing ? "Transcribing…" : session.transcript?.full_text ? "Re-transcribe" : "Transcribe"}
            </button>
          </div>
          {segments.length ? (
            <ol className="cues" ref={cuesRef} data-testid="transcript-cues">
              {segments.map((segment, index) => (
                <li
                  key={`${segment.start}-${segment.end}-${index}`}
                  className={transcribing && index === segments.length - 1 ? "is-live" : undefined}
                >
                  <button
                    type="button"
                    className="cue"
                    onClick={() => {
                      if (videoRef.current) videoRef.current.currentTime = segment.start;
                    }}
                  >
                    <time>{formatTime(segment.start)}</time>
                    <p>{segment.text}</p>
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted" data-testid="transcript-empty">
              {transcribing
                ? "Listening… the first cue will appear in a moment. You can already write your own notes."
                : "Cues appear here as the sermon is transcribed. You can take notes while it runs."}
            </p>
          )}
        </div>
      </div>

      <div className="workspace-right">
        <div className="notes-card">
          <div className="card-head">
            <h3>Sermon notes</h3>
            <button type="button" className="btn small" onClick={onGenerate} disabled={!session.transcript?.full_text}>
              Generate notes
            </button>
          </div>
          {notes ? (
            <div className="notes-body">
              <p className="theme">{notes.main_theme}</p>
              {notes.scriptures.length ? (
                <ul className="scriptures">
                  {notes.scriptures.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              <ul className="takeaways">
                {notes.takeaways.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p>{notes.summary}</p>
            </div>
          ) : (
            <p className="muted">
              {session.transcript?.full_text
                ? "You can generate notes from the transcript so far, or keep studying while more cues arrive."
                : "Generated notes will land here after the local LLM runs."}
            </p>
          )}
          {session.frameCaptures.length ? (
            <div className="screen-texts" data-testid="screen-texts">
              <h4>On-screen text</h4>
              <ul>
                {session.frameCaptures.map((item, index) => (
                  <li key={item.id ?? `${item.timestamp}-${index}`}>
                    <button
                      type="button"
                      className="cue"
                      onClick={() => {
                        if (videoRef.current) videoRef.current.currentTime = item.timestamp;
                      }}
                    >
                      <time>{formatTime(item.timestamp)}</time>
                      <p>{item.text}</p>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="muted">Captured slide and verse text will be listed here and used when you generate notes.</p>
          )}
        </div>

        <label className="user-notes">
          <span>Your notes</span>
          <textarea
            name="user-notes"
            rows={5}
            placeholder="Write what this means for you…"
            value={session.userNotes}
            onChange={(event) => onUserNotes(event.target.value)}
          />
        </label>

        <div className="chat-card">
          <h3>Ask about this sermon</h3>
          <div className="chat-log" data-testid="chat-log">
            {session.chatLog.length ? (
              session.chatLog.map((message, index) => (
                <p key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
                  {message.content}
                </p>
              ))
            ) : (
              <p className="muted">Chat stays on this machine and uses the transcript as context, including cues that have already landed.</p>
            )}
          </div>
          <form className="chat-form" onSubmit={send}>
            <input
              name="chat-message"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="What did the pastor mean by…?"
            />
            <button type="submit" className="btn primary small" disabled={!draft.trim()}>
              Send
            </button>
          </form>
        </div>
      </div>

      {busy ? <p className="status workspace-status">{busy}</p> : null}
      {error ? (
        <p className="status err workspace-status" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
