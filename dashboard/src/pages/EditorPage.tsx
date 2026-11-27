import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useData } from '../context/DataContext'
import type { Market, RegulationStatus } from '../types'
import { BAND_META, STATUS_META, bandFromScore } from '../types'

const LAST_MARKET_KEY = 'gts-dashboard-last-editor-market'

function scoreValue(market: Market, field: 'regulatory_severity' | 'china_sentiment') {
  return market[field]
}

function initialMarketId(requested: string | null, markets: { id: string }[]) {
  const known = new Set(markets.map((m) => m.id))
  if (requested && known.has(requested)) return requested
  try {
    const stored = sessionStorage.getItem(LAST_MARKET_KEY)
    if (stored && known.has(stored)) return stored
  } catch {
    // sessionStorage can be blocked; fall through to the first market.
  }
  return markets[0]?.id || 'AU'
}

export default function EditorPage() {
  const { data, baselineMarkets, edits, updateMarket, resetMarket, resetAll, exportEdits } = useData()
  const [params, setParams] = useSearchParams()
  const requested = params.get('market')
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string>(() => initialMarketId(requested, data.markets))
  const [copied, setCopied] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (requested && data.markets.some((m) => m.id === requested)) {
      setSelectedId(requested)
    }
  }, [data.markets, requested])

  useEffect(() => {
    if (!selectedId) return
    try {
      sessionStorage.setItem(LAST_MARKET_KEY, selectedId)
    } catch {
      // Ignore storage failures.
    }
  }, [selectedId])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return data.markets.filter((m) => {
      if (!q) return true
      return m.country.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)
    })
  }, [data.markets, query])

  const market = data.markets.find((m) => m.id === selectedId) ?? data.markets[0]
  const baseline = baselineMarkets.find((m) => m.id === market?.id)

  const selectMarket = (id: string) => {
    setSelectedId(id)
    setParams({ market: id })
    setCopied(false)
    setNotice('')
  }

  const copyOrDownload = async () => {
    const json = exportEdits()
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'score-wording-changes.json'
    link.click()
    URL.revokeObjectURL(url)
    try {
      await navigator.clipboard.writeText(json)
      setCopied(true)
      setNotice('Changes JSON copied and downloaded')
    } catch {
      setCopied(false)
      setNotice('Changes JSON downloaded')
    }
  }

  if (!market || !baseline) return null

  const severityBand = bandFromScore(market.regulatory_severity)
  const sentimentBand = bandFromScore(market.china_sentiment)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Edit Scores &amp; Wording</h2>
          <p className="text-sm text-slate-500 max-w-3xl">
            Adjust any of the 158 markets. Severity and China sentiment bands update immediately on the heatmap, legend, top five and market table. Edits stay in this browser until you reset them.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => { void copyOrDownload() }} className="px-3 py-2 rounded-lg border border-slate-300 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50">
            {copied ? 'Copied' : 'Copy / Download Changes JSON'}
          </button>
          <button
            type="button"
            onClick={() => {
              if (Object.keys(edits).length === 0) return
              if (window.confirm('Reset every local score and wording edit?')) {
                resetAll()
                setNotice('All local edits reset')
              }
            }}
            className="px-3 py-2 rounded-lg border border-red-200 bg-white text-sm font-medium text-red-700 hover:bg-red-50"
          >
            Reset all edits
          </button>
        </div>
      </div>
      {notice && <p className="text-sm text-slate-600">{notice}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find a market…"
            className="w-full mb-2 px-3 py-2 text-sm border border-slate-300 rounded-lg"
          />
          <div className="h-[32rem] overflow-y-auto space-y-1">
            {visible.map((m) => {
              const active = m.id === market.id
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => selectMarket(m.id)}
                  className={`w-full text-left rounded-lg px-2.5 py-2 text-sm ${
                    active ? 'bg-blue-600 text-white' : 'hover:bg-slate-50 text-slate-800'
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span>{m.country}</span>
                    <span className={`text-xs ${active ? 'text-blue-100' : 'text-slate-400'}`}>
                      {m.regulatory_severity}
                      {edits[m.id] ? ' · edited' : ''}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <form
          className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-5"
          onSubmit={(e) => e.preventDefault()}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">{market.country}</h3>
              <p className="text-sm text-slate-500">{market.id}{market.locally_edited ? ' · local edit' : ''}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                resetMarket(market.id)
                setNotice(`Reset ${market.country}`)
              }}
              disabled={!edits[market.id]}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-sm text-slate-700 disabled:opacity-40"
            >
              Reset this market
            </button>
          </div>

          <ScoreField
            label="Regulatory severity"
            value={scoreValue(market, 'regulatory_severity')}
            baseline={baseline.regulatory_severity}
            bandLabel={`${BAND_META[severityBand].label} (${BAND_META[severityBand].range})`}
            bandColour={BAND_META[severityBand].color}
            onChange={(value) => updateMarket(market.id, { regulatory_severity: value })}
          />
          <ScoreField
            label="China sentiment"
            value={scoreValue(market, 'china_sentiment')}
            baseline={baseline.china_sentiment}
            bandLabel={`${BAND_META[sentimentBand].label} (${BAND_META[sentimentBand].range})`}
            bandColour={BAND_META[sentimentBand].color}
            onChange={(value) => updateMarket(market.id, { china_sentiment: value })}
          />

          <label className="block text-sm">
            <span className="font-medium text-slate-800">Regulatory status</span>
            <select
              value={market.regulatory_status}
              onChange={(e) => {
                const regulatory_status = e.target.value as RegulationStatus
                updateMarket(market.id, {
                  regulatory_status,
                  regulatory_status_label: STATUS_META[regulatory_status].label,
                })
              }}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              {(Object.keys(STATUS_META) as RegulationStatus[]).map((key) => (
                <option key={key} value={key}>{STATUS_META[key].label}</option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-800">Regulatory status label</span>
            <input
              type="text"
              value={market.regulatory_status_label}
              onChange={(e) => updateMarket(market.id, { regulatory_status_label: e.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            />
            <span className="mt-1 block text-xs text-slate-400">Baseline label: {baseline.regulatory_status_label}</span>
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-800">Assessment note</span>
            <textarea
              value={market.assessment_note}
              onChange={(e) => updateMarket(market.id, { assessment_note: e.target.value })}
              rows={8}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 leading-relaxed"
            />
          </label>
        </form>
      </div>
    </div>
  )
}

function ScoreField({
  label,
  value,
  baseline,
  bandLabel,
  bandColour,
  onChange,
}: {
  label: string
  value: number
  baseline: number
  bandLabel: string
  bandColour: string
  onChange: (value: number) => void
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-medium text-slate-800">{label}</label>
        <span className="text-sm font-semibold" style={{ color: bandColour }}>{bandLabel}</span>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <input
          type="range"
          min={0}
          max={100}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1"
          aria-label={label}
        />
        <input
          type="number"
          min={0}
          max={100}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-20 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
        />
      </div>
      <p className="mt-1 text-xs text-slate-400">Baseline score: {baseline}</p>
    </div>
  )
}
