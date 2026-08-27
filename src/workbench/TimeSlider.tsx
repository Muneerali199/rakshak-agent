// Time-travel slider — scrub the case graph's time horizon.
// Single-handle model: "show evidence up to this date". As the handle moves from the
// earliest record toward today, the network visibly forms (edges appear as their
// timestamps fall inside the window) — the trafficking-ring demo's cinematic moment.
import { useMemo } from 'react'

const DAY = 86_400_000

function toDay(ts: number): string {
  return new Date(ts).toISOString().slice(0, 10)
}

export default function TimeSlider({
  minTs, maxTs, value, onChange, edgeCount, disabled,
}: {
  minTs: number
  maxTs: number
  value: number            // current end-of-window timestamp (ms)
  onChange: (ts: number) => void
  edgeCount: number
  disabled?: boolean
}) {
  const span = Math.max(1, maxTs - minTs)
  const pct = Math.min(100, Math.max(0, ((value - minTs) / span) * 100))

  const label = useMemo(() => toDay(value), [value])

  return (
    <div className="pointer-events-auto absolute inset-x-0 bottom-0 z-20 border-t border-zinc-800/80 bg-[#07080b]/95 px-4 py-2 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-3">
        <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-500">
          time&nbsp;travel
        </span>
        <span className="hidden font-mono text-[9px] text-zinc-600 sm:inline">{toDay(minTs)}</span>
        <input
          type="range"
          min={minTs}
          max={maxTs}
          step={DAY}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          className="h-1 flex-1 cursor-pointer appearance-none rounded-full bg-zinc-800 accent-[#00f0ff] disabled:opacity-40"
          aria-label="Show evidence up to this date"
        />
        <span className="hidden font-mono text-[9px] text-zinc-600 sm:inline">{toDay(maxTs)}</span>
        <span className="min-w-[10ch] rounded border border-[#00f0ff]/30 bg-[#00f0ff]/5 px-1.5 py-0.5 text-center font-mono text-[10px] text-[#00f0ff]">
          {label}
        </span>
        <span className="hidden font-mono text-[9px] text-zinc-500 md:inline">
          {edgeCount} edges ≤ date
        </span>
        {value < maxTs && (
          <button
            onClick={() => onChange(maxTs)}
            className="rounded border border-zinc-700 px-1.5 py-0.5 font-mono text-[9px] text-zinc-400 transition-colors hover:border-[#00f0ff]/50 hover:text-[#00f0ff]"
          >
            reset
          </button>
        )}
        <div
          className="pointer-events-none absolute bottom-full left-4 h-px bg-gradient-to-r from-transparent via-[#00f0ff]/40 to-transparent"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
