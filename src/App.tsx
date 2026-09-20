import { useCallback, useEffect, useState } from "react";
import { generateNotes, getHealth, saveUserNotes, sendChat, transcribeVideo, trimVideo } from "./api";
import { Stepper } from "./components/Stepper";
import { emptySession, type Session, type Step } from "./types";
import { ImportView } from "./views/ImportView";
import { TrimStudio } from "./views/TrimStudio";
import { Workspace } from "./views/Workspace";

export default function App() {
  const [step, setStep] = useState<Step>("import");
  const [session, setSession] = useState<Session>(emptySession);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");

  const patch = useCallback((next: Partial<Session>) => {
    setSession((current) => ({ ...current, ...next }));
  }, []);

  useEffect(() => {
    getHealth()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));
  }, []);

  async function runTrim() {
    if (!session.videoPath) {
      setError("Import a video before trimming.");
      return;
    }
    setError("");
    setBusy("Trimming…");
    try {
      const result = await trimVideo(session.videoPath, session.trimStart, session.trimEnd || session.duration);
      patch({ videoPath: result.output_path });
      setBusy("");
      setStep("study");
    } catch (err) {
      setBusy("");
      setError(err instanceof Error ? err.message : "Trim failed.");
    }
  }

  async function runTranscribe() {
    if (!session.videoPath) return;
    setError("");
    setBusy("Transcribing…");
    try {
      const result = await transcribeVideo(session.videoPath, "base");
      patch({ transcript: result.data });
      setBusy("");
    } catch (err) {
      setBusy("");
      setError(err instanceof Error ? err.message : "Transcription failed.");
    }
  }

  async function runNotes() {
    const text = session.transcript?.full_text;
    if (!text) {
      setError("Transcribe the clip before generating notes.");
      return;
    }
    setError("");
    setBusy("Generating notes…");
    try {
      const result = await generateNotes(text, session.title);
      patch({ notes: result.notes, sermonId: result.sermon_id });
      setBusy("");
    } catch (err) {
      setBusy("");
      setError(err instanceof Error ? err.message : "Note generation failed.");
    }
  }

  async function persistUserNotes(value: string) {
    patch({ userNotes: value });
    if (session.sermonId) {
      try {
        await saveUserNotes(session.sermonId, value);
      } catch {
        // Keep the local draft even if the API is unavailable.
      }
    }
  }

  async function runChat(message: string) {
    patch({ chatLog: [...session.chatLog, { role: "user", content: message }] });
    if (!session.sermonId) {
      setError("Generate notes before chatting so the model has sermon context.");
      return;
    }
    setBusy("Thinking…");
    try {
      const result = await sendChat(session.sermonId, message);
      patch({
        chatLog: result.history.map((item) => ({
          role: item.role as "user" | "assistant",
          content: item.content,
        })),
      });
      setBusy("");
    } catch (err) {
      setBusy("");
      setError(err instanceof Error ? err.message : "Chat failed.");
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="brand-kicker">Local study</p>
          <h1>Sermon Assistant</h1>
        </div>
        <Stepper current={step} onChange={setStep} />
        <p className={`health is-${health}`} data-testid="api-health">
          {health === "ok" ? "API ready" : health === "down" ? "API offline" : "Checking API…"}
        </p>
      </header>

      <main>
        {step === "import" ? (
          <ImportView
            session={session}
            busy={busy}
            error={error}
            onBusy={setBusy}
            onError={setError}
            onLoaded={(next) => {
              patch(next);
              setError("");
            }}
            onContinue={() => setStep("trim")}
          />
        ) : null}
        {step === "trim" ? (
          <TrimStudio
            session={session}
            busy={busy}
            error={error}
            onChange={patch}
            onTrim={() => void runTrim()}
            onContinue={() => setStep("study")}
          />
        ) : null}
        {step === "study" ? (
          <Workspace
            session={session}
            busy={busy}
            error={error}
            onUserNotes={(value) => void persistUserNotes(value)}
            onGenerate={() => void runNotes()}
            onTranscribe={() => void runTranscribe()}
            onChat={(message) => void runChat(message)}
          />
        ) : null}
      </main>
    </div>
  );
}
