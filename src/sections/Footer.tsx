import { useLayoutEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export default function Footer() {
  const sectionRef = useRef<HTMLElement>(null)

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.footer-massive',
        { opacity: 0, y: 100, letterSpacing: '0.3em' },
        {
          opacity: 1,
          y: 0,
          letterSpacing: '0.02em',
          ease: 'power3.out',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 80%',
            end: 'top 30%',
            scrub: 1,
          },
        }
      )
      gsap.fromTo(
        '.footer-sub',
        { opacity: 0 },
        {
          opacity: 1,
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top 40%',
            end: 'top 15%',
            scrub: 1,
          },
        }
      )
    }, sectionRef)
    return () => ctx.revert()
  }, [])

  return (
    <footer
      ref={sectionRef}
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-[#050505] via-[#0a0f1c] to-[#050505] px-6"
    >
      {/* Cyan horizon glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[30rem] w-[90vw] -translate-x-1/2 -translate-y-1/2 rounded-[100%] bg-[#00f0ff]/[0.06] blur-[110px]" />

      <p className="footer-sub font-mono-tech mb-8 text-[10px] tracking-[0.6em] text-[#00f0ff] opacity-0 md:text-xs">
        RAKSHAK · AI POLICE INTELLIGENCE
      </p>

      <h2 className="footer-massive font-cinzel text-glow-cyan text-center text-[13vw] font-black leading-[1.05] text-white md:text-[9rem]">
        SECURE
        <br />
        THE NATION.
      </h2>

      <div className="footer-sub mt-16 flex flex-col items-center gap-6 opacity-0">
        <div className="h-px w-40 bg-gradient-to-r from-transparent via-[#00f0ff]/60 to-transparent" />
        <div className="font-mono-tech flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-[9px] tracking-[0.3em] text-neutral-500 md:text-[10px]">
          <span>CLASSIFIED — AUTHORIZED PERSONNEL ONLY</span>
          <span className="hidden h-1 w-1 rounded-full bg-neutral-700 md:block" />
          <span>© {new Date().getFullYear()} RAKSHAK SYSTEMS</span>
        </div>
      </div>
    </footer>
  )
}
