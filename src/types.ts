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

export type Session = {
  sourcePath: string;
  videoPath: string;
  title: string;
  duration: number;
  trimStart: number;
  trimEnd: number;
  transcript: TranscriptData | null;
  notes: SermonNotes | null;
  userNotes: string;
  sermonId: number | null;
  chatLog: { role: "user" | "assistant"; content: string }[];
};

export const emptySession: Session = {
  sourcePath: "",
  videoPath: "",
  title: "",
  duration: 0,
  trimStart: 0,
  trimEnd: 0,
  transcript: null,
  notes: null,
  userNotes: "",
  sermonId: null,
  chatLog: [],
};

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
