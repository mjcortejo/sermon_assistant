export type Step = "import" | "trim" | "study";

export type TranscriptSegment = {
  start: number;
  end: number;
  text: string;
};

export type TranscriptData = {
  language?: string | null;
  full_text: string;
  segments: TranscriptSegment[];
};

export type SermonNotes = {
  main_theme: string;
  scriptures: string[];
  takeaways: string[];
  summary: string;
  user_notes: string;
};

export type FrameCapture = {
  id?: number | null;
  timestamp: number;
  text: string;
  confidence?: number | null;
  frame_path?: string | null;
};

export type ProjectSummary = {
  id: number;
  title: string;
  source_url?: string | null;
  video_path: string;
  duration: number;
  current_step: Step | string;
  has_transcript: boolean;
  has_notes: boolean;
  updated_at?: string | null;
};

export type ProjectDetail = ProjectSummary & {
  source_path: string;
  trim_start: number;
  trim_end: number;
  transcript: TranscriptData | null;
  user_notes: string;
  notes: SermonNotes | null;
  chat: { id: number; role: "user" | "assistant" | string; content: string }[];
  captures?: FrameCapture[];
};

export type Session = {
  projectId: number | null;
  sourcePath: string;
  sourceUrl: string;
  videoPath: string;
  title: string;
  duration: number;
  trimStart: number;
  trimEnd: number;
  transcript: TranscriptData | null;
  notes: SermonNotes | null;
  userNotes: string;
  chatLog: { role: "user" | "assistant"; content: string }[];
  frameCaptures: FrameCapture[];
};

export const emptySession: Session = {
  projectId: null,
  sourcePath: "",
  sourceUrl: "",
  videoPath: "",
  title: "",
  duration: 0,
  trimStart: 0,
  trimEnd: 0,
  transcript: null,
  notes: null,
  userNotes: "",
  chatLog: [],
  frameCaptures: [],
};

export function sessionFromProject(project: ProjectDetail): Session {
  return {
    projectId: project.id,
    sourcePath: project.source_path,
    sourceUrl: project.source_url || "",
    videoPath: project.video_path || project.source_path,
    title: project.title,
    duration: project.duration,
    trimStart: project.trim_start,
    trimEnd: project.trim_end || project.duration,
    transcript: project.transcript,
    notes: project.notes,
    userNotes: project.user_notes || "",
    chatLog: project.chat.map((item) => ({
      role: item.role === "assistant" ? "assistant" : "user",
      content: item.content,
    })),
    frameCaptures: project.captures || [],
  };
}

export function transcriptResumeAt(
  transcript: TranscriptData | null | undefined,
  duration = 0,
): number | null {
  const segments = transcript?.segments || [];
  if (!segments.length) return null;
  const last = segments[segments.length - 1]?.end ?? 0;
  if (duration > 0 && last >= duration - 0.4) return null;
  return last > 0 ? last : null;
}

export function mediaUrl(filePath: string): string {
  if (!filePath) return "";
  return `/media/file?path=${encodeURIComponent(filePath)}`;
}

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Parse m:ss, h:mm:ss, or a raw second count. Returns null if the text is not a time. */
export function parseClockTime(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^\d+(\.\d+)?$/.test(trimmed)) {
    const seconds = Number(trimmed);
    return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
  }
  const parts = trimmed.split(":");
  if (parts.length < 2 || parts.length > 3) return null;
  const nums = parts.map((part) => Number(part));
  if (nums.some((part) => !Number.isFinite(part) || part < 0)) return null;
  if (parts.length === 2) {
    const [minutes, seconds] = nums;
    if (seconds >= 60) return null;
    return minutes * 60 + seconds;
  }
  const [hours, minutes, seconds] = nums;
  if (minutes >= 60 || seconds >= 60) return null;
  return hours * 3600 + minutes * 60 + seconds;
}

export type ImportProgress = {
  phase: string;
  percent?: number | null;
  downloaded_bytes?: number | null;
  total_bytes?: number | null;
  speed?: number | null;
  eta?: number | null;
  message?: string;
  filename?: string;
};

export function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  const digits = size >= 10 || unit === 0 ? 0 : 1;
  return `${size.toFixed(digits)} ${units[unit]}`;
}

export function formatEta(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "";
  return formatTime(seconds);
}
