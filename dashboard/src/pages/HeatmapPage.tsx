import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useData } from '../context/DataContext'
import { useFilters } from '../context/FilterContext'
import { calculateRiskScores } from '../data/loader'
import type { ServiceTypeId, HeatmapMetric, ObligationType } from '../types'
import {
  SERVICE_TYPE_META, STATUS_META, BAND_META, PRIORITY_THEME_META,
  OBLIGATION_TYPE_META, bandFromScore,
} from '../types'
import { useNavigate } from 'react-router-dom'
import MarketDetail from '../components/common/MarketDetail'

const HeatmapChart = lazy(() => import('../components/heatmap/HeatmapChart'))

const METRIC_LABEL: Record<HeatmapMetric, string> = {
  regulatory_severity: 'Regulatory Severity',
  china_sentiment: 'China Sentiment',
}

export default function HeatmapPage() {
  const { data } = useData()
  const { dispatch } = useFilters()
  const navigate = useNavigate()
  const [serviceTypeFilter, setServiceTypeFilter] = useState<ServiceTypeId | 'all'>('all')
  const [obligationFilter, setObligationFilter] = useState<ObligationType | 'all'>('all')
  const [metric, setMetric] = useState<HeatmapMetric>('regulatory_severity')
  const [inspectedId, setInspectedId] = useState<string | null>(null)

  const riskScores = useMemo(
    () => calculateRiskScores(data.markets, metric, serviceTypeFilter, obligationFilter),
    [data.markets, metric, serviceTypeFilter, obligationFilter],
  )

  const scopedMarkets = useMemo(
    () => data.markets.filter(
      (m) =>
        (serviceTypeFilter === 'all' || m.service_type_ids.includes(serviceTypeFilter)) &&
        (obligationFilter === 'all' || m.obligation_ids.includes(obligationFilter)),
    ),
    [data.markets, serviceTypeFilter, obligationFilter],
  )

  useEffect(() => {
    if (inspectedId && !scopedMarkets.some((m) => m.id === inspectedId)) {
      setInspectedId(null)
    }
  }, [inspectedId, scopedMarkets])

  const priorityCoverage = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const m of scopedMarkets) {
      const themes = new Set(
        m.obligation_ids.map((o: ObligationType) => OBLIGATION_TYPE_META[o]?.priority).filter(Boolean),
      )
      for (const t of themes) counts[t as string] = (counts[t as string] || 0) + 1
    }
    return counts
  }, [scopedMarkets])

  const inspected = scopedMarkets.find((m) => m.id === inspectedId) ?? null

  const openInDatabase = (jurisdictionId: string) => {
    dispatch({ type: 'SET_JURISDICTION', value: [jurisdictionId] })
    navigate('/database')
  }

  const onChartClick = (params: unknown) => {
    const id = (params as { data?: { rawData?: { jurisdiction_id?: string } } }).data?.rawData?.jurisdiction_id
    if (!id) return
    setInspectedId(id)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-700 mr-1">View by:</span>
        {(Object.keys(METRIC_LABEL) as HeatmapMetric[]).map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              metric === m ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {METRIC_LABEL[m]}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-700 mr-2">Affected service type:</span>
        <button
          onClick={() => setServiceTypeFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            serviceTypeFilter === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          All
        </button>
        {(Object.keys(SERVICE_TYPE_META) as ServiceTypeId[])
          .filter((stid) => stid !== 'pornography')
          .map((stid) => {
          const meta = SERVICE_TYPE_META[stid]
          return (
            <button
              key={stid}
              onClick={() => setServiceTypeFilter(stid)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                serviceTypeFilter === stid
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {meta.icon} {meta.label}
            </button>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-700 mr-2">Key obligation:</span>
        <button
          onClick={() => setObligationFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            obligationFilter === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          All
        </button>
        {(Object.keys(OBLIGATION_TYPE_META) as ObligationType[]).map((oid) => {
          const meta = OBLIGATION_TYPE_META[oid]
          const active = obligationFilter === oid
          return (
            <button
              key={oid}
              onClick={() => setObligationFilter(oid)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                active ? 'text-white shadow-sm' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
              style={active ? { backgroundColor: meta.color } : {}}
            >
              {meta.label}
            </button>
          )
        })}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">
            Global Trust and Safety {METRIC_LABEL[metric]} heatmap
          </h2>
          <p className="text-sm text-slate-500">
            {metric === 'regulatory_severity'
              ? 'Regulatory severity (0–100) across 158 markets. Select a market to inspect its assessment.'
              : 'China sentiment (0–100) across 158 markets. Select a market to inspect its assessment.'}
          </p>
        </div>
        <div style={{ height: '600px' }}>
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-full text-slate-500">
                Loading heatmap…
              </div>
            }
          >
            <HeatmapChart riskScores={riskScores} metric={metric} onChartClick={onChartClick} />
          </Suspense>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {inspected ? (
          <div>
            <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-slate-900">Market detail</h3>
              <button
                type="button"
                onClick={() => openInDatabase(inspected.id)}
                className="text-sm text-blue-700 hover:text-blue-900"
              >
                Open in database
              </button>
            </div>
            <MarketDetail market={inspected} />
          </div>
        ) : (
          <p className="px-4 py-4 text-sm text-slate-500">
            Select a market on the map, or one of the top five, to inspect its scores, status and assessment.
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Severity bands</h3>
          <div className="space-y-2">
            {(['severe', 'high', 'moderate', 'low', 'minimal'] as const).map((b) => {
              const item = BAND_META[b]
              const count = riskScores.filter((rs) => bandFromScore(rs.risk_score) === b).length
              return (
                <div key={b} className="flex items-center gap-2 text-sm">
                  <div className="w-8 h-4 rounded" style={{ backgroundColor: item.color }} />
                  <span className="text-slate-700">{item.label}</span>
                  <span className="text-slate-400 text-xs">({item.range})</span>
                  <span className="ml-auto text-xs font-semibold text-slate-600">{count}</span>
                </div>
              )
            })}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Top 5 — {METRIC_LABEL[metric]}</h3>
          <div className="space-y-2">
            {riskScores.slice(0, 5).map((rs, i) => (
              <button
                type="button"
                key={rs.jurisdiction_id}
                className="flex w-full items-center justify-between text-sm cursor-pointer hover:bg-slate-50 rounded-lg px-2 py-1 text-left"
                onClick={() => setInspectedId(rs.jurisdiction_id)}
              >
                <span className="flex items-center gap-2">
                  <span className="text-slate-400 text-xs w-4">{i + 1}</span>
                  {rs.country_name}
                </span>
                <span className="font-semibold" style={{ color: BAND_META[bandFromScore(rs.risk_score)].color }}>
                  {rs.risk_score}
                </span>
              </button>
            ))}
            {riskScores.length === 0 && <p className="text-sm text-slate-400">No data</p>}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Status distribution</h3>
          <div className="space-y-1.5">
            {Object.entries(STATUS_META).map(([status, meta]) => {
              const count = scopedMarkets.filter((m) => m.regulatory_status === status).length
              if (count === 0) return null
              return (
                <div key={status} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ backgroundColor: meta.color }} />
                    {meta.label}
                  </span>
                  <span className="font-semibold text-slate-700">{count}</span>
                </div>
              )
            })}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Priority theme coverage</h3>
          <div className="space-y-1.5">
            {Object.entries(PRIORITY_THEME_META).map(([key, meta]) => {
              const count = priorityCoverage[key] || 0
              return (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span>{meta.icon}</span>
                    {meta.label}
                  </span>
                  <span className="font-semibold" style={{ color: meta.color }}>{count}</span>
                </div>
              )
            })}
            <p className="text-xs text-slate-400 pt-1">Markets addressing each priority theme.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
