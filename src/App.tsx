import { useCallback, useEffect, useRef, useState } from "react";
import {
  captureFrameText,
  createProject,
  deleteAllProjects,
  deleteProject,
  generateNotes,
  getHealth,
  getProject,
  listProjects,
  probeVideo,
  saveUserNotes,
  sendChat,
  stopTranscription,
  transcribeVideoLive,
  trimVideo,
  updateProject,
} from "./api";
import { Stepper } from "./components/Stepper";
import { ProjectSidebar } from "./components/ProjectSidebar";
import { emptySession, sessionFromProject, transcriptResumeAt, type ProjectSummary, type Session, type Step, type TranscriptData } from "./types";
import { ImportView } from "./views/ImportView";
import { TrimStudio } from "./views/TrimStudio";
import { Workspace } from "./views/Workspace";

function whisperShortName(gpu?: string | null) {
  if (!gpu) return "GPU";
  return gpu.replace(/^NVIDIA GeForce\s+/i, "").replace(/^NVIDIA\s+/i, "");
}

function llmShortName(model?: string | null) {
  if (!model) return "";
  return model.split(":")[0];
}

function healthCopy(whisperDevice: string, whisperGpu: string, llmModel: string) {
  const parts = ["API ready"];
  if (whisperDevice === "cuda") parts.push(whisperShortName(whisperGpu));
  else if (whisperDevice === "cpu") parts.push("CPU");
  if (llmModel) parts.push(llmShortName(llmModel));
  return parts.join(" · ");
}

function mergeTranscript(prior: TranscriptData | null | undefined, incoming: TranscriptData): TranscriptData {
  const existing = prior?.segments || [];
  if (!existing.length) return incoming;
  const cutoff = existing[existing.length - 1]?.end ?? 0;
  const extra = (incoming.segments || []).filter((item) => item.start >= cutoff - 0.05);
  const segments = [...existing, ...extra];
  return {
    language: incoming.language ?? prior?.language,
    full_text: segments
      .map((item) => item.text)
      .filter(Boolean)
      .join(" "),
    segments,
  };
}

export default function App() {
  const [step, setStep] = useState<Step>("import");
  const [session, setSession] = useState<Session>(emptySession);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");
  const [whisperDevice, setWhisperDevice] = useState("");
  const [whisperGpu, setWhisperGpu] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [transcribing, setTranscribing] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const sessionRef = useRef(session);
  sessionRef.current = session;
  const transcribeBusy =
    whisperDevice === "cuda"
      ? `Transcribing on ${whisperShortName(whisperGpu)}… cues will appear as they are ready.`
      : "Transcribing… cues will appear as they are ready.";
  const transcribeAbort = useRef<AbortController | null>(null);
  const persistTimer = useRef<number | undefined>(undefined);

  const patch = useCallback((next: Partial<Session>) => {
    setSession((current) => ({ ...current, ...next }));
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      const result = await listProjects();
      setProjects(result.projects);
    } catch {
      // Library is optional if the API is down.
    }
  }, []);

  useEffect(() => {
    getHealth()
      .then((payload) => {
        setHealth("ok");
        setWhisperDevice(payload.whisper?.device || "");
        setWhisperGpu(payload.whisper?.gpu || "");
        setLlmModel(payload.llm?.available ? payload.llm.model || "" : "");
      })
      .catch(() => setHealth("down"));
    void refreshProjects();
  }, [refreshProjects]);

  async function persist(partial: Partial<Session> = {}, currentStep = step) {
    const next = { ...sessionRef.current, ...partial };
    if (!next.projectId) return;
    await updateProject(next.projectId, {
      title: next.title,
      source_url: next.sourceUrl || null,
      source_path: next.sourcePath,
      video_path: next.videoPath,
      duration: next.duration,
      trim_start: next.trimStart,
      trim_end: next.trimEnd,
      current_step: currentStep,
      user_notes: next.userNotes,
      transcript: next.transcript,
    });
    await refreshProjects();
  }

  function persistTranscriptSoon(data: Session["transcript"]) {
    window.clearTimeout(persistTimer.current);
    persistTimer.current = window.setTimeout(() => {
      void persist({ transcript: data }, "study").catch(() => {
        // Keep showing live cues even if a mid-stream save fails.
      });
    }, 700);
  }

  useEffect(() => {
    return () => {
      transcribeAbort.current?.abort();
      window.clearTimeout(persistTimer.current);
    };
  }, []);

  async function goTo(nextStep: Step) {
    setStep(nextStep);
    try {
      await persist({}, nextStep);
    } catch {
      // Keep navigating even if save fails.
    }
  }

  async function handleLoaded(next: Partial<Session>) {
    setError("");
    try {
      const created = await createProject({
        title: next.title,
        source_url: next.sourceUrl,
        source_path: next.sourcePath || "",
        video_path: next.videoPath || next.sourcePath || "",
        duration: next.duration,
        trim_start: next.trimStart,
        trim_end: next.trimEnd,
        current_step: "import",
      });
      patch({ ...next, projectId: created.project.id });
      await refreshProjects();
    } catch (err) {
      patch(next);
      setError(err instanceof Error ? err.message : "Could not save project.");
    }
  }

  async function openProject(id: number) {
    transcribeAbort.current?.abort();
    setTranscribing(false);
    setBusy("");
    setError("");
    try {
      const result = await getProject(id);
      const restored = sessionFromProject(result.project);
      setSession(restored);
      const restoredStep = (result.project.current_step as Step) || "study";
      setStep(restoredStep === "import" || restoredStep === "trim" || restoredStep === "study" ? restoredStep : "study");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open project.");
    }
  }

  async function removeProject(id: number) {
    const project = projects.find((item) => item.id === id);
    const title = project?.title || "this project";
    if (!window.confirm(`Delete “${title}”? This cannot be undone.`)) return;
    try {
      await deleteProject(id);
      if (session.projectId === id) {
        transcribeAbort.current?.abort();
        setTranscribing(false);
        setSession(emptySession);
        setStep("import");
      }
      await refreshProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete project.");
    }
  }

  async function removeAllProjects() {
    if (!projects.length) return;
    if (!window.confirm(`Delete all ${projects.length} projects? This cannot be undone.`)) return;
    try {
      transcribeAbort.current?.abort();
      setTranscribing(false);
      await deleteAllProjects();
      setSession(emptySession);
      setStep("import");
      await refreshProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete projects.");
    }
  }

  async function runTrim() {
    const source = session.sourcePath || session.videoPath;
    if (!source) {
      setError("Import a video before trimming.");
      return;
    }
    setError("");
    setBusy("Trimming…");
    try {
      const sourceInfo = await probeVideo(source);
      const sourceDuration = sourceInfo.duration || session.duration;
      const start = session.trimStart || 0;
      const end = session.trimEnd || sourceDuration;
      const isFullClip = start <= 0.15 && end >= sourceDuration - 0.15;
      let videoPath = source;
      let clipDuration = sourceDuration;
      if (!isFullClip) {
        const result = await trimVideo(source, start, end);
        videoPath = result.output_path;
        const clipInfo = await probeVideo(videoPath);
        clipDuration = clipInfo.duration || Math.max(end - start, 0);
      }
      patch({ videoPath, duration: clipDuration, trimStart: start, trimEnd: end });
      await persist(
        { videoPath, duration: clipDuration, sourcePath: session.sourcePath || source, trimStart: start, trimEnd: end },
        "study",
      );
      setBusy("");
      setStep("study");
    } catch (err) {
      setBusy("");
      setError(err instanceof Error ? err.message : "Trim failed.");
    }
  }

  async function runTranscribe(resume = false) {
    if (!session.videoPath) return;
    transcribeAbort.current?.abort();
    const controller = new AbortController();
    transcribeAbort.current = controller;
    const prior = resume ? sessionRef.current.transcript : { full_text: "", segments: [] as TranscriptData["segments"] };
    const startTime = resume ? transcriptResumeAt(prior, sessionRef.current.duration) || 0 : 0;
    setError("");
    setTranscribing(true);
    setBusy(resume ? "Continuing transcription from the last cue…" : transcribeBusy);
    if (!resume) {
      patch({ transcript: { full_text: "", segments: [] } });
    }
    try {
      const result = await transcribeVideoLive(
        session.videoPath,
        (data, done) => {
          const merged = resume ? mergeTranscript(prior, data) : data;
          patch({ transcript: merged });
          if (done) return;
          persistTranscriptSoon(merged);
        },
        "base",
        controller.signal,
        startTime,
      );
      window.clearTimeout(persistTimer.current);
      const merged = resume ? mergeTranscript(prior, result.data) : result.data;
      patch({ transcript: merged });
      await persist({ transcript: merged }, "study");
      setBusy("");
      setTranscribing(false);
    } catch (err) {
      if (controller.signal.aborted) {
        window.clearTimeout(persistTimer.current);
        setTranscribing(false);
        setBusy("");
        try {
          await persist({ transcript: sessionRef.current.transcript }, "study");
        } catch {
          // Keep the cues already on screen.
        }
        return;
      }
      setBusy("");
      setTranscribing(false);
      setError(err instanceof Error ? err.message : "Transcription failed.");
    }
  }

  async function stopTranscribe() {
    setBusy("Stopping transcription…");
    try {
      await stopTranscription();
    } catch {
      // Still abort the client stream if the stop route is unreachable.
    }
    transcribeAbort.current?.abort();
    window.clearTimeout(persistTimer.current);
    setTranscribing(false);
    setBusy("");
    try {
      await persist({ transcript: sessionRef.current.transcript }, "study");
    } catch {
      // Keep the partial transcript locally.
    }
  }

  async function runNotes() {
    const text = session.transcript?.full_text;
    if (!text) {
      setError("Transcribe the clip before generating notes.");
      return;
    }
    if (!session.projectId) {
      setError("Save this sermon as a project first.");
      return;
    }
    setError("");
    setBusy("Generating notes…");
    try {
      const result = await generateNotes(session.projectId, text, session.title);
      patch({ notes: result.notes, projectId: result.project_id });
      await persist({ notes: result.notes }, "study");
      setBusy(transcribing ? transcribeBusy : "");
    } catch (err) {
      setBusy(transcribing ? transcribeBusy : "");
      setError(err instanceof Error ? err.message : "Note generation failed.");
    }
  }

  async function persistUserNotes(value: string) {
    patch({ userNotes: value });
    if (session.projectId) {
      try {
        await saveUserNotes(session.projectId, value);
        await refreshProjects();
      } catch {
        // Keep the local draft even if the API is unavailable.
      }
    }
  }

  async function runCaptureFrame(timestamp: number) {
    if (!session.videoPath) {
      setError("Import a video before capturing on-screen text.");
      return;
    }
    setError("");
    setCapturing(true);
    setBusy("Reading on-screen text…");
    try {
      const result = await captureFrameText(session.videoPath, timestamp, session.projectId);
      patch({ frameCaptures: result.captures || [] });
      await refreshProjects();
      setBusy(transcribing ? transcribeBusy : "");
      setCapturing(false);
    } catch (err) {
      setBusy(transcribing ? transcribeBusy : "");
      setCapturing(false);
      setError(err instanceof Error ? err.message : "Could not read text from this frame.");
    }
  }

  async function runChat(message: string) {
    patch({ chatLog: [...session.chatLog, { role: "user", content: message }] });
    if (!session.projectId) {
      setError("Save this sermon as a project first.");
      return;
    }
    if (!sessionRef.current.transcript?.full_text) {
      setError("Wait for the first transcript cue before chatting.");
      return;
    }
    setBusy(transcribing ? "Thinking… using the transcript so far." : "Thinking…");
    try {
      window.clearTimeout(persistTimer.current);
      await persist({ transcript: sessionRef.current.transcript }, "study");
      const result = await sendChat(session.projectId, message);
      patch({
        chatLog: result.history.map((item) => ({
          role: item.role === "assistant" ? "assistant" : "user",
          content: item.content,
        })),
      });
      await refreshProjects();
      setBusy(transcribing ? transcribeBusy : "");
    } catch (err) {
      setBusy(transcribing ? transcribeBusy : "");
      setError(err instanceof Error ? err.message : "Chat failed.");
    }
  }

  function startNewProject() {
    transcribeAbort.current?.abort();
    setTranscribing(false);
    setSession(emptySession);
    setStep("import");
    setError("");
    setBusy("");
  }

  return (
    <div className="app-shell">
      <ProjectSidebar
        projects={projects}
        currentId={session.projectId}
        onOpen={(id) => void openProject(id)}
        onDelete={(id) => void removeProject(id)}
        onDeleteAll={() => void removeAllProjects()}
        onNew={startNewProject}
      />
      <div className="app-main">
      <header className="topbar">
        <div>
          <p className="brand-kicker">{step === "import" ? "Import" : step === "trim" ? "Trim" : "Study"}</p>
          <h1>{session.title || "New study"}</h1>
        </div>
        <Stepper current={step} onChange={(next) => void goTo(next)} />
        <p className={`health is-${health}`} data-testid="api-health">
          {health === "ok"
            ? healthCopy(whisperDevice, whisperGpu, llmModel)
            : health === "down"
              ? "API offline"
              : "Checking API…"}
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
            onLoaded={(next) => void handleLoaded(next)}
            onContinue={() => void goTo("trim")}
          />
        ) : null}
        {step === "trim" ? (
          <TrimStudio
            session={session}
            busy={busy}
            error={error}
            onChange={patch}
            onTrim={() => void runTrim()}
            onContinue={() => void runTrim()}
          />
        ) : null}
        {step === "study" ? (
          <Workspace
            session={session}
            busy={busy}
            error={error}
            onUserNotes={(value) => void persistUserNotes(value)}
            onGenerate={() => void runNotes()}
            onTranscribe={() => void runTranscribe(false)}
            onStopTranscribe={() => void stopTranscribe()}
            onContinueTranscribe={() => void runTranscribe(true)}
            onChat={(message) => void runChat(message)}
            onCaptureFrame={(time) => void runCaptureFrame(time)}
            transcribing={transcribing}
            capturing={capturing}
          />
        ) : null}
      </main>
      </div>
    </div>
  );
}
