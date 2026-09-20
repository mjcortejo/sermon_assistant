type Props = {
  min: number;
  max: number;
  start: number;
  end: number;
  onChange: (start: number, end: number) => void;
};

export function DualRange({ min, max, start, end, onChange }: Props) {
  const span = Math.max(max - min, 0.001);
  const startPct = ((start - min) / span) * 100;
  const endPct = ((end - min) / span) * 100;

  return (
    <div className="dual-range" role="group" aria-label="Trim range">
      <div className="dual-range-track">
        <div
          className="dual-range-fill"
          style={{ left: `${startPct}%`, width: `${Math.max(endPct - startPct, 0)}%` }}
        />
      </div>
      <input
        className="dual-range-input"
        type="range"
        min={min}
        max={max}
        step={0.1}
        value={start}
        aria-label="Trim start"
        onChange={(event) => {
          const next = Number(event.target.value);
          onChange(Math.min(next, end - 0.1), end);
        }}
      />
      <input
        className="dual-range-input"
        type="range"
        min={min}
        max={max}
        step={0.1}
        value={end}
        aria-label="Trim end"
        onChange={(event) => {
          const next = Number(event.target.value);
          onChange(start, Math.max(next, start + 0.1));
        }}
      />
    </div>
  );
}
