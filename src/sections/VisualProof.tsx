import { useEffect, useRef, useState } from 'react'
import { motion, useInView, animate } from 'framer-motion'

function Counter({ to, suffix = '' }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!inView) return
    const controls = animate(0, to, {
      duration: 2.2,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setVal(Math.round(v)),
    })
    return () => controls.stop()
  }, [inView, to])
  return (
    <span ref={ref}>
      {val.toLocaleString('en-IN')}
      {suffix}
    </span>
  )
}

const ALERTS = [
  { level: 'HIGH', color: '#ff2d55', text: 'Anomalous fund flow — Jamtara cluster flagged' },
  { level: 'MED', color: '#00f0ff', text: 'Chatter spike detected — 3 districts, Bengali + Hindi' },
  { level: 'HIGH', color: '#ff2d55', text: 'Vehicle of interest matched — NH-48 toll, Jaipur' },
  { level: 'LOW', color: '#8b93a7', text: 'CCTV node 4471 re-linked to identity graph' },
  { level: 'MED', color: '#00f0ff', text: 'Encrypted channel pattern — new signature learned' },
]

export default function VisualProof() {
  const sectionRef = useRef<HTMLElement>(null)

  return (
    <section
      id="command-center"
      ref={sectionRef}
      className="relative overflow-hidden bg-[#050505] py-32 md:py-44"
    >
      {/* Ambient */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[50rem] w-[70rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#00f0ff]/[0.04] blur-[140px]" />

      <div className="relative z-10 mx-auto max-w-6xl px-6">
        <div className="mb-20 text-center">
          <p className="font-mono-tech mb-4 text-[10px] tracking-[0.5em] text-[#00f0ff] md:text-xs">
            03 — VISUAL PROOF
          </p>
          <h2 className="font-serif-display text-4xl font-bold text-white md:text-6xl">
            The Command Center, <span className="italic text-[#00f0ff]">live.</span>
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-sm font-light leading-relaxed text-neutral-400 md:text-base">
            Every signal, every entity, every district — rendered on a single pane of glass.
          </p>
        </div>

        {/* Floating MacBook mockup */}
        <motion.div
          initial={{ opacity: 0, y: 90, rotateX: 14 }}
          whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 1.3, ease: [0.16, 1, 0.3, 1] }}
          style={{ perspective: 1200 }}
          className="mx-auto max-w-4xl"
        >
          <motion.div
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          >
            {/* Screen */}
            <div className="relative rounded-t-2xl border border-white/15 bg-[#0b0d12] p-2 shadow-[0_40px_120px_-20px_rgba(0,240,255,0.15),0_60px_160px_-40px_rgba(0,0,0,0.9)] md:p-3">
              {/* camera */}
              <div className="absolute left-1/2 top-2 z-20 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-white/20" />
              <div className="relative aspect-[16/10] overflow-hidden rounded-lg bg-[#060a12]">
                {/* scanline */}
                <div className="scanline pointer-events-none absolute inset-x-0 top-0 z-10 h-1/4 bg-gradient-to-b from-transparent via-[#00f0ff]/[0.05] to-transparent" />

                {/* ===== Live dashboard mockup (swap for screen recording later) ===== */}
                <div className="flex h-full flex-col p-3 md:p-5">
                  {/* dash header */}
                  <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-2">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-[#00f0ff]" />
                      <span className="font-cinzel text-[8px] font-bold tracking-[0.3em] text-white md:text-[10px]">
                        RAKSHAK COMMAND CENTER
                      </span>
                    </div>
                    <div className="font-mono-tech flex items-center gap-1.5 text-[7px] text-neutral-500 md:text-[9px]">
                      <span className="blink-dot h-1 w-1 rounded-full bg-[#ff2d55]" />
                      LIVE FEED
                    </div>
                  </div>

                  {/* stats row */}
                  <div className="mb-3 grid grid-cols-3 gap-2 md:gap-3">
                    {[
                      { label: 'ACTIVE CASES', value: 1284, color: '#ffffff' },
                      { label: 'SIGNALS / SEC', value: 48392, color: '#00f0ff' },
                      { label: 'THREATS FLAGGED', value: 37, color: '#ff2d55' },
                    ].map((s) => (
                      <div
                        key={s.label}
                        className="rounded-md border border-white/10 bg-white/[0.04] p-2 backdrop-blur-sm md:p-3"
                      >
                        <div
                          className="font-mono-tech text-sm font-medium md:text-xl"
                          style={{ color: s.color }}
                        >
                          <Counter to={s.value} />
                        </div>
                        <div className="font-mono-tech mt-1 text-[6px] tracking-[0.2em] text-neutral-500 md:text-[8px]">
                          {s.label}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* middle: waveform + graph */}
                  <div className="mb-3 grid flex-1 grid-cols-5 gap-2 md:gap-3">
                    {/* waveform bars */}
                    <div className="col-span-3 flex items-end justify-between gap-1 rounded-md border border-white/10 bg-white/[0.03] p-2 md:p-3">
                      {Array.from({ length: 28 }).map((_, i) => (
                        <motion.span
                          key={i}
                          className="w-full rounded-sm bg-gradient-to-t from-[#00f0ff]/20 to-[#00f0ff]"
                          animate={{ height: ['18%', `${22 + Math.abs(Math.sin(i * 1.7)) * 70}%`, '18%'] }}
                          transition={{
                            duration: 1.6 + (i % 5) * 0.22,
                            repeat: Infinity,
                            ease: 'easeInOut',
                            delay: i * 0.06,
                          }}
                          style={{ maxWidth: 6 }}
                        />
                      ))}
                    </div>
                    {/* threat ticker */}
                    <div className="col-span-2 overflow-hidden rounded-md border border-white/10 bg-white/[0.03] p-2 md:p-3">
                      <div className="font-mono-tech mb-2 text-[6px] tracking-[0.25em] text-neutral-500 md:text-[8px]">
                        PRIORITY QUEUE
                      </div>
                      <motion.div
                        animate={{ y: ['0%', '-50%'] }}
                        transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
                        className="space-y-2"
                      >
                        {[...ALERTS, ...ALERTS].map((a, i) => (
                          <div key={i} className="flex items-start gap-1.5">
                            <span
                              className="font-mono-tech shrink-0 rounded-sm px-1 text-[6px] md:text-[7px]"
                              style={{ color: a.color, border: `1px solid ${a.color}55` }}
                            >
                              {a.level}
                            </span>
                            <span className="text-[7px] leading-snug text-neutral-400 md:text-[9px]">
                              {a.text}
                            </span>
                          </div>
                        ))}
                      </motion.div>
                    </div>
                  </div>

                  {/* bottom bar */}
                  <div className="flex items-center justify-between border-t border-white/10 pt-2">
                    <span className="font-mono-tech text-[6px] tracking-[0.25em] text-neutral-600 md:text-[8px]">
                      GRID: NATIONAL · 28 STATES · 8 UTs
                    </span>
                    <span className="font-mono-tech text-[6px] tracking-[0.25em] text-[#00f0ff]/70 md:text-[8px]">
                      IDENTITY GRAPH: 1.4B NODES
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Laptop base */}
            <div className="relative">
              <div className="h-3 rounded-b-2xl bg-gradient-to-b from-[#1a1d24] to-[#0b0d12] md:h-4" />
              <div className="mx-auto h-1 w-24 rounded-b-lg bg-black/60 md:w-32" />
              {/* glow under laptop */}
              <div className="mx-auto mt-6 h-8 w-3/4 rounded-[100%] bg-[#00f0ff]/10 blur-2xl" />
            </div>
          </motion.div>
        </motion.div>

        <p className="font-mono-tech mt-14 text-center text-[9px] tracking-[0.35em] text-neutral-600">
          [ LIVE MODULE — REPLACE WITH YOUR SCREEN RECORDING ]
        </p>
      </div>
    </section>
  )
}
