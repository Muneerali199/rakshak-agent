import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

// Offline English→Hindi demo layer. Transliteration is rule-based on the
// backend (engine builtin-hindi-rules-v1); we only cache + fan out here.

const TRANSLIT_CACHE = new Map<string, string>()

export const LANE_LABEL_HI: Record<string, string> = {
  CDR: 'कॉल-विवरण',
  BANK: 'बैंक-लेनदेन',
  FIN: 'वित्तीय-नेटवर्क',
  RTO: 'वाहन-रजिस्ट्रार',
  GOVT: 'सरकारी-रिकॉर्ड',
  FIR: 'प्राथमिकी',
  IP: 'इंटरनेट-रिकॉर्ड',
}

export const EDGE_COLOR_LABEL_HI: Record<string, string> = {
  CONTACTED: 'संपर्क किया',
  CALLED: 'कॉल किया',
  TRANSFER: 'स्थानांतरण',
  OWNS: 'स्वामित्व',
  BELONGS_TO: 'संबंधित',
  IN_MESH: 'मेश-लिंक',
}

export function useHiLabels(lang: 'en' | 'hi', labels: string[]): Record<string, string> {
  const [map, setMap] = useState<Record<string, string>>({})
  const key = labels.join('\u0002')

  useEffect(() => {
    if (lang !== 'hi') {
      setMap({})
      return
    }
    const uniq = Array.from(new Set(labels.filter((l) => l && l.trim())))
    if (!uniq.length) {
      setMap({})
      return
    }
    const missing = uniq.filter((l) => !TRANSLIT_CACHE.has(l))
    const apply = () =>
      setMap(Object.fromEntries(uniq.map((l) => [l, TRANSLIT_CACHE.get(l) ?? l])))
    if (!missing.length) {
      apply()
      return
    }
    let cancelled = false
    api
      .hindiTransliterate(missing)
      .then(({ hindi }) => {
        missing.forEach((l, i) => TRANSLIT_CACHE.set(l, hindi[i] ?? l))
        if (!cancelled) apply()
      })
      .catch(() => {
        if (!cancelled) apply()
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, key])

  return map
}