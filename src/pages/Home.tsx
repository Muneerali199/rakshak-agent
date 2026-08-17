import Hero from '../sections/Hero'
import Problem from '../sections/Problem'
import Solution from '../sections/Solution'
import VisualProof from '../sections/VisualProof'
import Footer from '../sections/Footer'

export default function Home() {
  return (
    <main className="relative bg-[#050505]">
      <Hero />
      <Problem />
      <Solution />
      <VisualProof />
      <Footer />
      {/* Cinematic film-grain overlay over the whole page */}
      <div className="film-grain" aria-hidden="true" />
    </main>
  )
}
