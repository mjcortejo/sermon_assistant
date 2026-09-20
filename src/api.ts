import type { FrameCapture, ImportProgress, ProjectDetail, ProjectSummary, SermonNotes, TranscriptData } from "./types";

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail ?? body);
  } catch {
    return response.statusText;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json() as Promise<T>;
}

export type HealthStatus = {
  status: string;
  whisper?: {
    device: string;
    compute_type: string;
    gpu?: string | null;
  };
  llm?: {
    backend?: string;
    model?: string;
    available?: boolean;
  };
};

export function getHealth() {
  return request<HealthStatus>("/health");
}

export function downloadVideo(url: string, outputName?: string) {
  return request<{ file_path: string; info?: { title?: string; duration?: number } }>(
    "/media/download",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, output_name: outputName }),
    },
  );
}

function progressFromPayload(data: Record<string, unknown>): ImportProgress {
  return {
    phase: typeof data.phase === "string" ? data.phase : "downloading",
    percent: typeof data.percent === "number" ? data.percent : null,
    downloaded_bytes: typeof data.downloaded_bytes === "number" ? data.downloaded_bytes : null,
    total_bytes: typeof data.total_bytes === "number" ? data.total_bytes : null,
    speed: typeof data.speed === "number" ? data.speed : null,
    eta: typeof data.eta === "number" ? data.eta : null,
    message: typeof data.message === "string" ? data.message : undefined,
    filename: typeof data.filename === "string" ? data.filename : undefined,
  };
}

export async function downloadVideoLive(
  url: string,
  onProgress: (progress: ImportProgress) => void,
  outputName?: string,
  signal?: AbortSignal,
): Promise<{ file_path: string; info?: { title?: string; duration?: number } }> {
  const response = await fetch("/media/download/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ url, output_name: outputName }),
    signal,
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  if (!response.body) {
    throw new Error("Download stream was empty.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: { file_path: string; info?: { title?: string; duration?: number } } | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const parsed = parseSseBlock(chunk.trim());
      if (!parsed) continue;
      if (parsed.event === "error") {
        throw new Error(String(parsed.data.detail || "Download failed."));
      }
      if (parsed.event === "progress") {
        onProgress(progressFromPayload(parsed.data));
      }
      if (parsed.event === "done") {
        const filePath = String(parsed.data.file_path || "");
        result = {
          file_path: filePath,
          info: parsed.data.info as { title?: string; duration?: number } | undefined,
        };
      }
    }
  }

  if (!result?.file_path) {
    throw new Error("Download finished without a file path.");
  }
  return result;
}

export async function uploadVideo(file: File, onProgress?: (progress: ImportProgress) => void) {
  return new Promise<{ file_path: string }>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/media/upload");
    xhr.upload.onprogress = (event) => {
      if (!onProgress || !event.lengthComputable) return;
      onProgress({
        phase: "uploading",
        percent: (event.loaded / event.total) * 100,
        downloaded_bytes: event.loaded,
        total_bytes: event.total,
        message: "Uploading…",
      });
    };
    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText || "{}") as { file_path?: string; detail?: unknown };
        if (xhr.status >= 200 && xhr.status < 300 && body.file_path) {
          resolve({ file_path: body.file_path });
          return;
        }
        const detail = body.detail;
        reject(new Error(typeof detail === "string" ? detail : xhr.statusText || "Upload failed."));
      } catch {
        reject(new Error(xhr.statusText || "Upload failed."));
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed."));
    xhr.onabort = () => reject(new DOMException("Aborted", "AbortError"));
    const data = new FormData();
    data.append("file", file);
    xhr.send(data);
  });
}

export function probeVideo(path: string) {
  return request<{ duration: number }>(`/media/probe?path=${encodeURIComponent(path)}`);
}

export function trimVideo(inputPath: string, start: number, end: number, outputName?: string) {
  return request<{ output_path: string }>("/media/trim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      input_path: inputPath,
      start_time: start,
      end_time: end,
      output_name: outputName,
    }),
  });
}

export function transcribeVideo(filePath: string, modelSize = "base") {
  return request<{ data: TranscriptData; transcript_path: string }>("/media/transcribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path: filePath, model_size: modelSize }),
  });
}

function parseSseBlock(block: string): { event: string; data: Record<string, unknown> } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) as Record<string, unknown> };
  } catch {
    return null;
  }
}

function transcriptFromPayload(data: Record<string, unknown>, fallback?: TranscriptData): TranscriptData {
  const segments = Array.isArray(data.segments) ? (data.segments as TranscriptData["segments"]) : fallback?.segments || [];
  return {
    language: (data.language as string | null | undefined) ?? fallback?.language,
    full_text: typeof data.full_text === "string" ? data.full_text : fallback?.full_text || "",
    segments,
  };
}

export async function transcribeVideoLive(
  filePath: string,
  onUpdate: (data: TranscriptData, done: boolean) => void,
  modelSize = "base",
  signal?: AbortSignal,
): Promise<{ data: TranscriptData; transcript_path?: string }> {
  const response = await fetch("/media/transcribe/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ file_path: filePath, model_size: modelSize }),
    signal,
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  if (!response.body) {
    throw new Error("Transcript stream was empty.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let latest: TranscriptData = { full_text: "", segments: [] };
  let transcriptPath = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const parsed = parseSseBlock(chunk.trim());
      if (!parsed) continue;
      if (parsed.event === "error") {
        throw new Error(String(parsed.data.detail || "Transcription failed."));
      }
      latest = transcriptFromPayload(parsed.data, latest);
      onUpdate(latest, parsed.event === "done");
      if (typeof parsed.data.transcript_path === "string") {
        transcriptPath = parsed.data.transcript_path;
      }
    }
  }

  return { data: latest, transcript_path: transcriptPath };
}

export function captureFrameText(filePath: string, timestamp: number, projectId?: number | null) {
  return request<{
    timestamp: number;
    text: string;
    lines: string[];
    confidence?: number | null;
    frame_path: string;
    capture?: FrameCapture | null;
    captures: FrameCapture[];
  }>("/media/ocr", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_path: filePath,
      timestamp,
      project_id: projectId ?? undefined,
    }),
  });
}

export function generateNotes(projectId: number, transcript: string, title?: string) {
  return request<{ project_id: number; notes: SermonNotes }>("/notes/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, transcript, title }),
  });
}

export function saveUserNotes(projectId: number, userNotes: string) {
  return request<{ notes: SermonNotes }>(`/notes/${projectId}/user`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_notes: userNotes }),
  });
}

export function sendChat(projectId: number, message: string) {
  return request<{ reply: string; history: { role: string; content: string }[] }>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, message }),
  });
}

export function getModelStatus() {
  return request<{ exists: boolean; path: string; loaded: boolean }>("/notes/model");
}

export function listProjects() {
  return request<{ projects: ProjectSummary[] }>("/projects");
}

export function createProject(body: {
  title?: string;
  source_url?: string;
  source_path: string;
  video_path: string;
  duration?: number;
  trim_start?: number;
  trim_end?: number;
  current_step?: string;
}) {
  return request<{ project: ProjectDetail }>("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getProject(id: number) {
  return request<{ project: ProjectDetail }>(`/projects/${id}`);
}

export function updateProject(id: number, body: Record<string, unknown>) {
  return request<{ project: ProjectDetail }>(`/projects/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function deleteProject(id: number) {
  return request<{ status: string; id: number }>(`/projects/${id}`, { method: "DELETE" });
}
