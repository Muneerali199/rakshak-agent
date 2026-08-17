import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const MODULES = [
  {
    index: '01',
    title: 'Identity Resolution',
    tag: 'ENTITY ENGINE',
    accent: '#00f0ff',
    desc: 'Fuse faces, voices, phone numbers, vehicles, devices and digital footprints into one verified identity graph — across every database, every district, every alias.',
    points: ['Cross-database entity linking', 'Facial + voice biometrics', 'Alias & shell-network detection'],
  },
  {
    index: '02',
    title: 'Indian Language NLP',
    tag: 'SIGNAL INTELLIGENCE',
    accent: '#00f0ff',
    desc: 'Read the country as it speaks. Rakshak parses threat chatter, FIR narratives and open-source signals across 22 scheduled languages and hundreds of dialects — in real time.',
    points: ['22 languages, native-grade', 'Code-mixed & slang aware', 'Sentiment + threat scoring'],
  },
  {
    index: '03',
    title: 'RakshakAI Security',
    tag: 'CYBER DEFENSE',
    accent: '#ff2d55',
    desc: 'A hardened cyber perimeter for critical police infrastructure. Zero-trust architecture, anomaly detection and autonomous response — built to defence-grade standards.',
    points: ['Zero-trust core architecture', 'Autonomous threat response', 'End-to-end encrypted grid'],
  },
]

export default function Solution() {
  const sectionRef = useRef<HTMLElement>(null)
  const trackRef = useRef<HTMLDivElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const track = trackRef.current!
      const getScrollAmount = () => track.scrollWidth - window.innerWidth

      // Vertical scroll drives horizontal motion (pinned)
      gsap.to(track, {
        x: () => -getScrollAmount(),
        ease: 'none',
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top top',
          end: () => `+=${getScrollAmount()}`,
          pin: true,
          scrub: 1,
          anticipatePin: 1,
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            if (progressRef.current) {
              progressRef.current.style.transform = `scaleX(${self.progress})`
            }
          },
        },
      })
    }, sectionRef)
    return () => ctx.revert()
  }, [])

  return (
    <section ref={sectionRef} className="relative h-screen overflow-hidden bg-[#0a0f1c]">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute left-1/4 top-0 h-[40rem] w-[40rem] -translate-y-1/2 rounded-full bg-[#00f0ff]/[0.05] blur-[120px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[30rem] w-[30rem] translate-y-1/2 rounded-full bg-[#ff2d55]/[0.04] blur-[120px]" />

      {/* Heading */}
      <div className="absolute left-6 top-10 z-20 md:left-12 md:top-14">
        <p className="font-mono-tech mb-3 text-[10px] tracking-[0.5em] text-[#00f0ff] md:text-xs">
          02 — THE SOLUTION
        </p>
        <h2 className="font-serif-display text-4xl font-bold text-white md:text-6xl">
          One platform. <span className="italic text-[#00f0ff]">Total clarity.</span>
        </h2>
      </div>

      {/* Horizontal track */}
      <div
        ref={trackRef}
        className="flex h-full items-center gap-8 pl-6 pr-[12vw] pt-24 md:gap-14 md:pl-12 will-change-transform"
        style={{ width: 'max-content' }}
      >
        {MODULES.map((m) => (
          <article
            key={m.index}
            className="group relative flex h-[62vh] w-[82vw] flex-col justify-between overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur-xl transition-colors duration-500 hover:border-[#00f0ff]/30 md:h-[64vh] md:w-[42rem] md:p-12"
          >
            {/* card glow on hover */}
            <div
              className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-0 blur-[100px] transition-opacity duration-700 group-hover:opacity-25"
              style={{ background: m.accent }}
            />

            <div className="flex items-start justify-between">
              <span className="font-serif-display text-7xl font-black text-white/[0.07] md:text-8xl">
                {m.index}
              </span>
              <span
                className="font-mono-tech rounded-full border px-4 py-1.5 text-[9px] tracking-[0.3em]"
                style={{ borderColor: `${m.accent}40`, color: m.accent }}
              >
                {m.tag}
              </span>
            </div>

            <div>
              <h3 className="font-serif-display mb-5 text-3xl font-bold text-white md:text-5xl">
                {m.title}
              </h3>
              <p className="max-w-md text-sm font-light leading-relaxed text-neutral-300 md:text-base">
                {m.desc}
              </p>
            </div>

            <ul className="space-y-3 border-t border-white/10 pt-6">
              {m.points.map((p) => (
                <li key={p} className="flex items-center gap-3 text-xs text-neutral-400 md:text-sm">
                  <span
                    className="h-1 w-1 rounded-full"
                    style={{ background: m.accent, boxShadow: `0 0 8px ${m.accent}` }}
                  />
                  {p}
                </li>
              ))}
            </ul>
          </article>
        ))}

        {/* End cap */}
        <div className="flex h-[62vh] w-[60vw] items-center justify-center md:w-[30rem]">
          <p className="font-serif-display max-w-xs text-center text-3xl font-bold italic leading-snug text-white/40 md:text-4xl">
            Built for the shield of the nation.
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="absolute bottom-10 left-1/2 z-20 h-px w-48 -translate-x-1/2 overflow-hidden bg-white/10">
        <div ref={progressRef} className="h-full w-full origin-left scale-x-0 bg-[#00f0ff]" />
      </div>
    </section>
  )
}
