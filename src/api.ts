import type { SermonNotes, TranscriptData } from "./types";

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

export function getHealth() {
  return request<{ status: string }>("/health");
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

export async function uploadVideo(file: File) {
  const data = new FormData();
  data.append("file", file);
  return request<{ file_path: string }>("/media/upload", { method: "POST", body: data });
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

export function generateNotes(transcript: string, title?: string) {
  return request<{ sermon_id: number; notes: SermonNotes }>("/notes/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript, title }),
  });
}

export function saveUserNotes(sermonId: number, userNotes: string) {
  return request<{ notes: SermonNotes }>(`/notes/${sermonId}/user`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_notes: userNotes }),
  });
}

export function sendChat(sermonId: number, message: string) {
  return request<{ reply: string; history: { role: string; content: string }[] }>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sermon_id: sermonId, message }),
  });
}

export function getModelStatus() {
  return request<{ exists: boolean; path: string; loaded: boolean }>("/notes/model");
}
