import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Market, MarketEdit, MergedData, NewsItem, Regulation } from '../types'
import { bandFromScore } from '../types'
import {
  baselineMarkets,
  jurisdictions,
  lastUpdated,
  newsItems,
  regulations,
  registerMeta,
  serviceTypes,
} from '../data/dataset'

const STORAGE_KEY = 'gts-dashboard-score-wording-edits-v1'

type EditMap = Record<string, MarketEdit>

interface DataContextValue {
  data: MergedData
  baselineMarkets: Market[]
  regulations: Regulation[]
  newsItems: NewsItem[]
  loading: boolean
  error: string | null
  lastUpdated: string | null
  edits: EditMap
  editedCount: number
  updateMarket: (id: string, patch: MarketEdit) => void
  resetMarket: (id: string) => void
  resetAll: () => void
  exportEdits: () => string
}

const DataContext = createContext<DataContextValue | undefined>(undefined)

function readEdits(): EditMap {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return {}
    const parsed = JSON.parse(stored) as EditMap
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function clampScore(value: number) {
  if (!Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, Math.round(value)))
}

function pruneEdit(base: Market, edit: MarketEdit): MarketEdit | null {
  const next: MarketEdit = {}
  if (edit.regulatory_severity != null && clampScore(edit.regulatory_severity) !== base.regulatory_severity) {
    next.regulatory_severity = clampScore(edit.regulatory_severity)
  }
  if (edit.china_sentiment != null && clampScore(edit.china_sentiment) !== base.china_sentiment) {
    next.china_sentiment = clampScore(edit.china_sentiment)
  }
  if (edit.regulatory_status && edit.regulatory_status !== base.regulatory_status) {
    next.regulatory_status = edit.regulatory_status
  }
  if (edit.regulatory_status_label != null && edit.regulatory_status_label !== base.regulatory_status_label) {
    next.regulatory_status_label = edit.regulatory_status_label
  }
  if (edit.assessment_note != null && edit.assessment_note !== base.assessment_note) {
    next.assessment_note = edit.assessment_note
  }
  return Object.keys(next).length ? next : null
}

export function applyMarketEdit(base: Market, edit: MarketEdit | undefined): Market {
  if (!edit) return { ...base, locally_edited: false }
  const severity = edit.regulatory_severity != null ? clampScore(edit.regulatory_severity) : base.regulatory_severity
  const sentiment = edit.china_sentiment != null ? clampScore(edit.china_sentiment) : base.china_sentiment
  return {
    ...base,
    regulatory_severity: severity,
    regulatory_severity_band: bandFromScore(severity),
    china_sentiment: sentiment,
    china_sentiment_band: bandFromScore(sentiment),
    regulatory_status: edit.regulatory_status ?? base.regulatory_status,
    regulatory_status_label: edit.regulatory_status_label ?? base.regulatory_status_label,
    assessment_note: edit.assessment_note ?? base.assessment_note,
    locally_edited: true,
  }
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [edits, setEdits] = useState<EditMap>(() => readEdits())

  const writeEdits = useCallback((next: EditMap) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Ignore quota and private-mode failures; the in-memory edit still applies.
    }
    return next
  }, [])

  const updateMarket = useCallback((id: string, patch: MarketEdit) => {
    setEdits((current) => {
      const base = baselineMarkets.find((m) => m.id === id)
      if (!base) return current
      const pruned = pruneEdit(base, { ...current[id], ...patch })
      const next = { ...current }
      if (pruned) next[id] = pruned
      else delete next[id]
      return writeEdits(next)
    })
  }, [writeEdits])

  const resetMarket = useCallback((id: string) => {
    setEdits((current) => {
      if (!current[id]) return current
      const next = { ...current }
      delete next[id]
      return writeEdits(next)
    })
  }, [writeEdits])

  const resetAll = useCallback(() => {
    setEdits(() => writeEdits({}))
  }, [writeEdits])

  const markets = useMemo(
    () => baselineMarkets.map((market) => applyMarketEdit(market, edits[market.id])),
    [edits],
  )

  const data = useMemo<MergedData>(() => ({
    version: '2026-11-27',
    last_updated: lastUpdated,
    markets,
    regulations,
    jurisdictions,
    service_types: serviceTypes,
  }), [markets])

  const exportEdits = useCallback(() => {
    const changes = Object.entries(edits).flatMap(([id, edit]) => {
      const base = baselineMarkets.find((m) => m.id === id)
      if (!base) return []
      const edited = applyMarketEdit(base, edit)
      return [{
        id,
        country: base.country,
        fields: Object.keys(edit),
        baseline: {
          regulatory_severity: base.regulatory_severity,
          regulatory_severity_band: base.regulatory_severity_band,
          china_sentiment: base.china_sentiment,
          china_sentiment_band: base.china_sentiment_band,
          regulatory_status: base.regulatory_status,
          regulatory_status_label: base.regulatory_status_label,
          assessment_note: base.assessment_note,
        },
        edited: {
          regulatory_severity: edited.regulatory_severity,
          regulatory_severity_band: edited.regulatory_severity_band,
          china_sentiment: edited.china_sentiment,
          china_sentiment_band: edited.china_sentiment_band,
          regulatory_status: edited.regulatory_status,
          regulatory_status_label: edited.regulatory_status_label,
          assessment_note: edited.assessment_note,
        },
      }]
    })
    return JSON.stringify({
      schema: 'global-trust-and-safety-dashboard.score-wording-edits',
      exported_at: new Date().toISOString(),
      market_count: baselineMarkets.length,
      edited_market_count: changes.length,
      changes,
    }, null, 2)
  }, [edits])

  const value = useMemo<DataContextValue>(() => ({
    data,
    baselineMarkets,
    regulations,
    newsItems,
    loading: false,
    error: null,
    lastUpdated,
    edits,
    editedCount: Object.keys(edits).length,
    updateMarket,
    resetMarket,
    resetAll,
    exportEdits,
  }), [data, edits, exportEdits, resetAll, resetMarket, updateMarket])

  return (
    <DataContext.Provider value={value}>
      {children}
    </DataContext.Provider>
  )
}

export function useData() {
  const ctx = useContext(DataContext)
  if (!ctx) throw new Error('useData must be used within DataProvider')
  return ctx
}

export { registerMeta }
