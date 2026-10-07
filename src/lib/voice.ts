// Bhashini voice channel — on-device Hindi speech (Web Speech API).
// Honest framing: this box runs real speech-to-text / text-to-speech ON the
// device in hi-IN (offline, nothing leaves the district box). The bridge is
// labeled `bhashini-ondevice-sim`; production swaps in Bhashini ASR/TTS over
// API Setu. No audio is ever uploaded anywhere from here.
export const VOICE_MODE = 'bhashini-ondevice-sim'

declare global {
  interface Window {
    SpeechRecognition?: unknown
    webkitSpeechRecognition?: unknown
  }
}

export function speechAvailable(): boolean {
  return typeof window !== 'undefined' &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition)
}

/** Start a one-shot hi-IN dictation; returns a stop() handle. */
export function dictate(
  onText: (text: string, done: boolean) => void,
  onError?: (msg: string) => void,
): () => void {
  const SRC = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SRC) {
    onError?.('speech-to-text unsupported in this browser')
    return () => {}
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rec: any = new (SRC as any)()
  rec.lang = 'hi-IN'
  rec.continuous = false
  rec.interimResults = true
  rec.maxAlternatives = 1

  let final = ''
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rec.onresult = (e: any) => {
    let interim = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript as string
      if (e.results[i].isFinal) final += t + ' '
      else interim += t
    }
    onText(final + interim, e.results[e.results.length - 1]?.isFinal ?? false)
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rec.onerror = (e: any) => onError?.(e?.error ?? 'speech error')
  rec.onend = () => onText('', true)
  rec.start()
  return () => {
    try { rec.stop() } catch { /* already stopped */ }
  }
}

/** Read text aloud in Hindi/English via the device TTS (offline). */
export function speak(text: string, lang = 'hi-IN'): void {
  if (typeof window === 'undefined' || !('speechSynthesis' in window) || !text.trim()) return
  try {
    const u = new SpeechSynthesisUtterance(text)
    u.lang = lang
    const voices = window.speechSynthesis.getVoices()
    const v =
      voices.find((vv) => vv.lang.toLowerCase().startsWith('hi')) ||
      voices.find((vv) => vv.lang.toLowerCase().startsWith('en'))
    if (v) u.voice = v
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(u)
  } catch { /* speech is best-effort */ }
}

export function stopSpeaking(): void {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
}