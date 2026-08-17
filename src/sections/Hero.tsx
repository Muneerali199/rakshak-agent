import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const HEADLINE_LINES = [
  ['Silence', 'the', 'Noise.'],
  ['Surface', 'the', 'Truth.'],
]

export default function Hero() {
  const sectionRef = useRef<HTMLElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      // Masked word reveal on load — words slide up from behind a mask, 0.1s stagger
      gsap.to('.hero-word', {
        y: 0,
        opacity: 1,
        stagger: 0.1,
        duration: 1.1,
        ease: 'power4.out',
        delay: 0.35,
      })
      gsap.fromTo(
        '.hero-fade',
        { opacity: 0, y: 24 },
        { opacity: 1, y: 0, stagger: 0.12, duration: 1, ease: 'power3.out', delay: 1.15 }
      )

      // Cinematic scroll-out: content drifts up + fades, video scales subtly
      gsap.to(contentRef.current, {
        y: -120,
        opacity: 0,
        ease: 'none',
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: 1,
        },
      })
      gsap.to(videoRef.current, {
        scale: 1.12,
        ease: 'none',
        scrollTrigger: {
          trigger: sectionRef.current,
          start: 'top top',
          end: 'bottom top',
          scrub: 1,
        },
      })
    }, sectionRef)
    return () => ctx.revert()
  }, [])

  return (
    <section ref={sectionRef} className="relative h-screen w-full overflow-hidden">
      {/* Background video */}
      <video
        ref={videoRef}
        className="video-cinematic absolute inset-0 h-full w-full object-cover"
        src="/videos/hero-city.mp4"
        autoPlay
        muted
        loop
        playsInline
      />
      {/* Heavy dark gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-black/20 to-[#050505]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(5,5,5,0.45)_100%)]" />

      {/* Top bar */}
      <header className="hero-fade absolute inset-x-0 top-0 z-20 flex items-center justify-between px-6 py-6 opacity-0 md:px-12">
        <div className="flex items-center gap-3">
          <div className="h-2 w-2 rounded-full bg-[#00f0ff] shadow-[0_0_12px_rgba(0,240,255,0.9)]" />
          <span className="font-cinzel text-sm font-bold tracking-[0.35em] text-white">RAKSHAK</span>
        </div>
        <div className="font-mono-tech hidden items-center gap-2 text-[10px] tracking-[0.25em] text-neutral-400 md:flex">
          <span className="blink-dot h-1.5 w-1.5 rounded-full bg-[#ff2d55]" />
          SYSTEM ONLINE — 24/7 SURVEILLANCE GRID
        </div>
      </header>

      {/* Centered content */}
      <div ref={contentRef} className="relative z-10 flex h-full flex-col items-center justify-center px-6 text-center">
        <p className="hero-fade font-mono-tech mb-8 text-[10px] tracking-[0.5em] text-[#00f0ff] opacity-0 md:text-xs">
          AI-POWERED POLICE INTELLIGENCE & CYBERSECURITY
        </p>

        <h1 className="font-serif-display max-w-6xl text-[13vw] font-bold leading-[0.95] text-white sm:text-7xl md:text-8xl lg:text-[8rem]">
          {HEADLINE_LINES.map((line, li) => (
            <span key={li} className="block">
              {line.map((word, wi) => (
                <span key={wi} className="inline-block overflow-hidden pb-[0.12em] align-bottom">
                  <span
                    className="hero-word inline-block translate-y-[110%] opacity-0"
                    style={{ willChange: 'transform' }}
                  >
                    {word}
                    {wi < line.length - 1 ? ' ' : ''}
                  </span>
                </span>
              ))}
            </span>
          ))}
        </h1>

        <p className="hero-fade mt-8 max-w-xl text-base font-light leading-relaxed text-neutral-300 opacity-0 md:text-lg">
          Rakshak fuses fragmented signals into one intelligence fabric — built for the forces
          that protect a billion people.
        </p>

        <a
          href="#command-center"
          className="hero-fade cta-pulse group mt-12 inline-flex items-center gap-3 rounded-full border border-[#00f0ff]/50 bg-[#00f0ff]/10 px-8 py-4 text-sm font-medium tracking-[0.2em] text-[#00f0ff] backdrop-blur-md transition-all duration-300 hover:bg-[#00f0ff]/20 hover:text-white opacity-0"
        >
          ENTER THE COMMAND CENTER
          <span className="transition-transform duration-300 group-hover:translate-x-1.5">→</span>
        </a>
      </div>

      {/* Scroll cue */}
      <div className="hero-fade absolute bottom-8 left-1/2 z-10 -translate-x-1/2 opacity-0">
        <div className="flex flex-col items-center gap-2">
          <span className="font-mono-tech text-[9px] tracking-[0.4em] text-neutral-500">SCROLL</span>
          <div className="h-12 w-px bg-gradient-to-b from-[#00f0ff]/70 to-transparent" />
        </div>
      </div>
    </section>
  )
}
