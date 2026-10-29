import { useEffect, useId, useRef, useState } from "react";
import { dateLabel, number, timeLabel } from "../format";

export interface PlotPoint {
  time: string;
  value: number | null;
}
export interface Series {
  label: string;
  color: string;
  points: PlotPoint[];
  dashed?: boolean;
}
interface Props {
  title: string;
  description: string;
  series: Series[];
  targets: string[];
  signed?: boolean;
  inspect: (index: number) => { title: string; items: { label: string; value: string }[] };
}
export function linePath(
  points: PlotPoint[],
  x: (value: number) => number,
  y: (value: number) => number,
) {
  let connected = false;
  return points
    .map((point) => {
      if (point.value === null) {
        connected = false;
        return "";
      }
      const segment = `${connected ? "L" : "M"}${x(Date.parse(point.time)).toFixed(2)},${y(point.value).toFixed(2)}`;
      connected = true;
      return segment;
    })
    .join(" ");
}
export function Chart({ title, description, series, targets, signed = false, inspect }: Props) {
  const id = useId();
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(900);
  const [selected, setSelected] = useState(0);
  useEffect(() => {
    if (!frame.current || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(300, entry.contentRect.width)),
    );
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);
  const values = series.flatMap((item) =>
    item.points.flatMap((point) => (point.value === null ? [] : [point.value])),
  );
  if (!values.length)
    return (
      <div className="chart-empty">
        <strong>No valid points to plot</strong>
        <p>Missing and invalid targets remain in the coverage ledger and data table.</p>
      </div>
    );
  const first = Date.parse(targets[0]);
  const last = Math.max(
    ...series.flatMap((item) => item.points.map((point) => Date.parse(point.time))),
    Date.parse(targets.at(-1) ?? targets[0]),
  );
  const min = signed ? Math.min(-1000, Math.floor(Math.min(...values) / 1000) * 1000) : 0;
  const max = Math.max(
    signed ? 1000 : 4000,
    Math.ceil(Math.max(...values) / (signed ? 1000 : 4000)) * (signed ? 1000 : 4000),
  );
  const left = 48,
    right = width - 18,
    top = 22,
    bottom = 226;
  const x = (instant: number) =>
    left + ((instant - first) / Math.max(1, last - first)) * (right - left);
  const y = (value: number) => bottom - ((value - min) / (max - min)) * (bottom - top);
  const active = Math.min(selected, targets.length - 1);
  const detail = inspect(active);
  const selectedX = x(Date.parse(targets[active]));
  const longRange = last - first > 36 * 3_600_000;
  return (
    <figure className="chart-figure" aria-labelledby={`${id}-title`}>
      <figcaption className="sr-only" id={`${id}-title`}>
        {title}. {description}
      </figcaption>
      <div className="plot-legend">
        {series.map((item) => (
          <span key={item.label}>
            <i style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
        <span className="axis-unit">{signed ? "Error" : "Generation"} · GW</span>
      </div>
      <div ref={frame} className="plot-frame">
        <svg
          viewBox={`0 0 ${width} 270`}
          role="img"
          aria-labelledby={`${id}-svg-title ${id}-desc`}
          onPointerMove={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect();
            const position = ((event.clientX - bounds.left) * width) / bounds.width;
            const instant = first + ((position - left) / (right - left)) * (last - first);
            setSelected(
              Math.max(
                0,
                Math.min(
                  targets.length - 1,
                  Math.round(
                    ((instant - first) / (Date.parse(targets.at(-1) ?? targets[0]) - first)) *
                      (targets.length - 1),
                  ),
                ),
              ),
            );
          }}
        >
          <title id={`${id}-svg-title`}>{title}</title>
          <desc id={`${id}-desc`}>
            {description} Use the target slider below or the data table for exact values.
          </desc>
          {[0, 1, 2, 3, 4].map((tick) => {
            const value = min + ((max - min) * tick) / 4;
            return (
              <g key={tick}>
                <line x1={left} x2={right} y1={y(value)} y2={y(value)} className="grid-line" />
                <text x={left - 10} y={y(value) + 4} textAnchor="end">
                  {number(value / 1000, 1)}
                </text>
              </g>
            );
          })}
          {[0, 1, 2, 3].map((tick) => {
            const instant = Date.parse(targets[Math.round(((targets.length - 1) * tick) / 3)]);
            const value = new Date(instant).toISOString();
            return (
              <text
                key={tick}
                x={x(instant)}
                y={251}
                textAnchor={tick === 0 ? "start" : tick === 3 ? "end" : "middle"}
              >
                {longRange ? dateLabel(value.slice(0, 10)) : timeLabel(value)}
              </text>
            );
          })}
          {signed && <line x1={left} x2={right} y1={y(0)} y2={y(0)} className="zero-line" />}
          {series.map((item) =>
            signed ? (
              <g key={item.label}>
                {item.points.map((point) =>
                  point.value === null ? null : (
                    <line
                      key={point.time}
                      x1={x(Date.parse(point.time))}
                      x2={x(Date.parse(point.time))}
                      y1={y(0)}
                      y2={y(point.value)}
                      stroke={point.value >= 0 ? "#b85f43" : "#1a8277"}
                      strokeWidth={Math.max(1.4, ((right - left) / targets.length) * 0.55)}
                    />
                  ),
                )}
              </g>
            ) : (
              <path
                key={item.label}
                d={linePath(item.points, x, y)}
                fill="none"
                stroke={item.color}
                strokeWidth={2}
                strokeDasharray={item.dashed ? "5 4" : undefined}
                vectorEffect="non-scaling-stroke"
              />
            ),
          )}
          <line x1={selectedX} x2={selectedX} y1={top} y2={bottom} className="selection-line" />
          {!signed &&
            series.map((item) => {
              const point = item.points.find((point) => point.time === targets[active]);
              return point?.value != null ? (
                <circle
                  key={item.label}
                  cx={selectedX}
                  cy={y(point.value)}
                  r={4.5}
                  fill={item.color}
                  stroke="white"
                  strokeWidth={2}
                />
              ) : null;
            })}
        </svg>
      </div>
      <div className="chart-inspector">
        <div className="inspector-heading">
          <strong>
            {detail.title} <span className="chart-zone">GMT</span>
          </strong>
          <span className="target-count">
            Target {active + 1} / {targets.length}
          </span>
        </div>
        <dl>
          {detail.items.map((item) => (
            <div key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="chart-controls">
        <label htmlFor={`${id}-target`}>Inspect {signed ? "signed error" : "wind"} target</label>
        <input
          id={`${id}-target`}
          type="range"
          min={0}
          max={targets.length - 1}
          value={active}
          aria-valuetext={`${detail.title}. ${detail.items.map((item) => `${item.label}: ${item.value}`).join(". ")}`}
          onChange={(event) => setSelected(Number(event.target.value))}
        />
        <span>← → keys</span>
      </div>
    </figure>
  );
}
