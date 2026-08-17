import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

function Cyan({ children }: { children: React.ReactNode }) {
  return <span className="text-[#00f0ff]">{children}</span>
}
function Red({ children }: { children: React.ReactNode }) {
  return <span className="text-[#ff2d55]">{children}</span>
}

export default function Problem() {
  const sectionRef = useRef<HTMLElement>(null)
  const bgRef = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      // Parallax: background moves slower than foreground text
      gsap.fromTo(
        bgRef.current,
        { yPercent: -18 },
        {
          yPercent: 18,
          ease: 'none',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top bottom',
            end: 'bottom top',
            scrub: 1,
          },
        }
      )

      // Text block reveal — slashes into view as the user scrolls
      gsap.utils.toArray<HTMLElement>('.problem-line').forEach((el) => {
        gsap.fromTo(
          el,
          { y: 80, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 1,
            ease: 'power4.out',
            scrollTrigger: {
              trigger: el,
              start: 'top 85%',
              end: 'top 55%',
              scrub: 1,
            },
          }
        )
      })
    }, sectionRef)
    return () => ctx.revert()
  }, [])

  return (
    <section ref={sectionRef} className="relative overflow-hidden bg-[#050505] py-40 md:py-56">
      {/* Parallax background — blurred fiber-optic chaos, moves slower than text */}
      <div ref={bgRef} className="absolute -inset-y-[25%] inset-x-0 will-change-transform">
        <video
          className="video-cinematic-heavy h-full w-full object-cover opacity-70"
          src="/videos/fiber-cables.mp4"
          autoPlay
          muted
          loop
          playsInline
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#050505] via-[#050505]/55 to-[#050505]" />
      </div>

      {/* Foreground — centered narrow column */}
      <div className="relative z-10 mx-auto max-w-3xl px-6">
        <p className="problem-line font-mono-tech mb-10 text-[10px] tracking-[0.5em] text-[#ff2d55] md:text-xs">
          01 — THE PROBLEM
        </p>

        <h2 className="problem-line font-serif-display text-4xl font-bold leading-[1.1] text-white md:text-6xl">
          India's police forces are drowning in <Cyan>data</Cyan> — and starving for{' '}
          <Cyan>intelligence</Cyan>.
        </h2>

        <div className="mt-14 space-y-8 text-lg font-light leading-relaxed text-neutral-300 md:text-xl">
          <p className="problem-line">
            Every investigation generates thousands of signals: call records, CCTV feeds, social
            media chatter, financial trails, FIRs filed in <Cyan>22 official languages</Cyan>. The
            evidence is almost always there.
          </p>
          <p className="problem-line">
            But it sits in <Cyan>siloed systems</Cyan>, scattered across districts, locked in
            formats no single analyst can connect in time. Meanwhile,{' '}
            <Red>threats move at machine speed</Red> — coordinated, encrypted, borderless.
          </p>
          <p className="problem-line">
            The gap between <Cyan>signal</Cyan> and <Cyan>truth</Cyan> is where cases go cold, where
            patterns go unseen, where the next attack hides in plain sight.
          </p>
        </div>

        <div className="problem-line mt-16 flex items-center gap-4">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[#ff2d55]/60 to-transparent" />
          <span className="font-mono-tech text-[10px] tracking-[0.4em] text-neutral-500">
            THE COST OF NOISE
          </span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[#ff2d55]/60 to-transparent" />
        </div>
      </div>
    </section>
  )
}
