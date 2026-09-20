import { formatTime, type ProjectSummary } from "../types";

type Props = {
  projects: ProjectSummary[];
  currentId: number | null;
  onOpen: (id: number) => void;
  onDelete: (id: number) => void;
  onDeleteAll: () => void;
  onNew: () => void;
};

function projectMeta(project: ProjectSummary): string {
  const status = project.has_notes
    ? "Notes"
    : project.has_transcript
      ? "Transcript"
      : project.current_step === "study"
        ? "Study"
        : project.current_step === "trim"
          ? "Trim"
          : "Import";
  return project.duration ? `${status} · ${formatTime(project.duration)}` : status;
}

export function ProjectSidebar({ projects, currentId, onOpen, onDelete, onDeleteAll, onNew }: Props) {
  return (
    <aside className="sidebar" data-testid="project-sidebar">
      <div className="sidebar-brand">
        <p className="brand-kicker">Local study</p>
        <h1>Sermon Assistant</h1>
      </div>
      <button type="button" className="btn primary sidebar-new" onClick={onNew}>
        New project
      </button>
      <p className="sidebar-label">Projects</p>
      {projects.length ? (
        <ul className="sidebar-list">
          {projects.map((project) => (
            <li key={project.id} className={project.id === currentId ? "is-current" : ""}>
              <button type="button" className="sidebar-open" onClick={() => onOpen(project.id)}>
                <strong>{project.title || "Untitled sermon"}</strong>
                <span>{projectMeta(project)}</span>
              </button>
              <button
                type="button"
                className="sidebar-delete"
                aria-label={`Delete ${project.title || "project"}`}
                onClick={() => onDelete(project.id)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted sidebar-empty">Saved studies will appear here.</p>
      )}
      {projects.length ? (
        <button type="button" className="btn small sidebar-delete-all" data-testid="delete-all-projects" onClick={onDeleteAll}>
          Delete all projects
        </button>
      ) : null}
    </aside>
  );
}
