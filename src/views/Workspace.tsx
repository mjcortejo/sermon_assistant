import { useState } from "react";
import type { FormEvent } from "react";
import { formatTime, mediaUrl, type Session } from "../types";

type Props = {
  session: Session;
  busy: string;
  error: string;
  onUserNotes: (value: string) => void;
  onGenerate: () => void;
  onTranscribe: () => void;
  onChat: (message: string) => void;
};

export function Workspace({
  session,
  busy,
  error,
  onUserNotes,
  onGenerate,
  onTranscribe,
  onChat,
}: Props) {
  const [draft, setDraft] = useState("");
  const src = mediaUrl(session.videoPath);
  const notes = session.notes;

  function send(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    onChat(text);
  }

  return (
    <section className="workspace">
      <div className="workspace-left">
        <div className="player-shell compact">
          {src ? (
            <video src={src} controls playsInline data-testid="study-player" />
          ) : (
            <div className="player-empty">No trimmed clip yet.</div>
          )}
        </div>
        <div className="transcript-card">
          <div className="card-head">
            <h3>Transcript</h3>
            <button type="button" className="btn small" onClick={onTranscribe} disabled={!session.videoPath}>
              Transcribe
            </button>
          </div>
          {session.transcript?.segments.length ? (
            <ol className="cues">
              {session.transcript.segments.map((segment) => (
                <li key={`${segment.start}-${segment.end}`}>
                  <time>{formatTime(segment.start)}</time>
                  <p>{segment.text}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="muted" data-testid="transcript-empty">
              {session.transcript?.full_text ||
                "Transcript will appear here after transcription. You can still inspect the study layout."}
            </p>
          )}
        </div>
      </div>

      <div className="workspace-right">
        <div className="notes-card">
          <div className="card-head">
            <h3>Sermon notes</h3>
            <button type="button" className="btn small" onClick={onGenerate} disabled={!session.transcript}>
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
            <p className="muted">Generated notes will land here after the local LLM runs.</p>
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
              <p className="muted">Chat stays on this machine and uses the transcript as context.</p>
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
