import type { Step } from "../types";

const STEPS: { id: Step; label: string; n: string }[] = [
  { id: "import", label: "Import", n: "1" },
  { id: "trim", label: "Trim", n: "2" },
  { id: "study", label: "Study", n: "3" },
];

type Props = {
  current: Step;
  onChange: (step: Step) => void;
};

export function Stepper({ current, onChange }: Props) {
  return (
    <nav className="stepper" aria-label="Sermon workflow">
      {STEPS.map((step, index) => {
        const active = step.id === current;
        return (
          <span key={step.id} className="stepper-item">
            {index > 0 ? <span className="stepper-rule" aria-hidden="true" /> : null}
            <button
              type="button"
              className={active ? "step is-active" : "step"}
              aria-current={active ? "step" : undefined}
              onClick={() => onChange(step.id)}
            >
              <span className="step-num">{step.n}</span>
              {step.label}
            </button>
          </span>
        );
      })}
    </nav>
  );
}
