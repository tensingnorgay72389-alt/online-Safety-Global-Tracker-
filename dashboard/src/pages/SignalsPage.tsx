import { useMemo, useState } from 'react'
import {
  actorLabel,
  actorName,
  actorOptions,
  clusterOptions,
  displayText,
  filterSignals,
  formatReportDate,
  formatWeight,
  marketLabel,
  marketOptions,
  officialSourceCounts,
  signalCounts,
  signals,
  sortSignals,
  weightNote,
  type SignalSortKey,
  type SignalWeightBand,
  type RegulatorySignal,
} from '../data/signals'

const FEATURED = [
  { id: 'mx', label: 'Mexico' },
  { id: 'tr', label: 'Türkiye' },
]

const BANDS: SignalWeightBand[] = ['high', 'medium', 'low']

function weightClass(weight: number): string {
  if (weight >= 0.9) return 'bg-blue-50 text-blue-800 border-blue-200'
  if (weight >= 0.65) return 'bg-amber-50 text-amber-900 border-amber-200'
  if (weight >= 0.5) return 'bg-slate-50 text-slate-700 border-slate-200'
  return 'bg-slate-100 text-slate-600 border-slate-200'
}

export default function SignalsPage() {
  const [search, setSearch] = useState('')
  const [market, setMarket] = useState('all')
  const [bands, setBands] = useState<SignalWeightBand[]>([])
  const [actor, setActor] = useState('all')
  const [cluster, setCluster] = useState('all')
  const [minWeight, setMinWeight] = useState(0)
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [sortKey, setSortKey] = useState<SignalSortKey>('market')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const markets = useMemo(() => marketOptions(signals), [])
  const clusters = useMemo(() => clusterOptions(signals), [])
  const actors = useMemo(() => actorOptions(signals), [])
  const filtered = useMemo(
    () => sortSignals(
      filterSignals(signals, { search, market, bands, actor, cluster, minWeight, from, to }),
      sortKey,
      sortOrder,
    ),
    [actor, bands, cluster, from, market, minWeight, search, sortKey, sortOrder, to],
  )

  const toggleBand = (band: SignalWeightBand) => {
    setBands((current) => current.includes(band) ? current.filter((item) => item !== band) : [...current, band])
  }

  const toggleSort = (key: SignalSortKey) => {
    if (sortKey === key) {
      setSortOrder((current) => current === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortOrder(key === 'market' || key === 'actor' || key === 'focus' ? 'asc' : 'desc')
    }
  }

  const reset = () => {
    setSearch('')
    setMarket('all')
    setBands([])
    setActor('all')
    setCluster('all')
    setMinWeight(0)
    setFrom('')
    setTo('')
  }

  const sortMark = sortKey === 'market' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Regulatory signals</h2>
        <p className="text-sm text-slate-500 max-w-3xl">
          Sourced statements from the 2026 monitoring reports, kept separate from the regulations register.
          A signal on this page does not change a market score and is not added to the instrument list.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <WeightCard weight="0.90" count={signalCounts.weight_0_90} label="High" detail="Incorporated once attributed" />
        <WeightCard weight="0.65" count={signalCounts.weight_0_65} label="Medium" detail="Specific risk or mechanism mentioned" />
        <WeightCard weight="0.50" count={signalCounts.weight_0_50} label="Medium" detail="Review only, not incorporated" />
        <WeightCard weight="0.25" count={signalCounts.weight_0_25} label="Low" detail="NGO statements, low confidence" />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 text-sm text-slate-600 space-y-2">
        <p>
          0.90 covers minister-level officials, heads of government, presidents, European Commissioners and statutory regulator heads.
          Deputy ministers are in this band only when the report shows them speaking as the department.
        </p>
        <p>
          0.65 and 0.50 cover politicians who are not minister-level, together with US state governors or attorneys general and equivalent offices.
          0.65 is used when a specific risk or mechanism is mentioned. 0.50 is review only.
        </p>
        <p>
          Reports from 24 July 2026 name Andy Burnham as Prime Minister. Earlier 2026 reports name Keir Starmer as Prime Minister.
          Both are shown with the date on the row.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-slate-700">Markets</span>
        <button
          type="button"
          onClick={() => setMarket('all')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium ${market === 'all' ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-700'}`}
        >
          All markets
        </button>
        {FEATURED.map((item) => {
          const count = officialSourceCounts[item.id]?.total
          const active = market === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setMarket(active ? 'all' : item.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium ${active ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-700'}`}
            >
              {item.label}
              {count ? <span className={active ? 'text-blue-100' : 'text-slate-400'}> · {count} official sources</span> : null}
            </button>
          )
        })}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search markets, people, offices and evidence"
          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <label className="text-xs text-slate-500">
            Market
            <select value={market} onChange={(event) => setMarket(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800">
              <option value="all">All markets</option>
              {markets.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-500">
            Minimum weight
            <select value={String(minWeight)} onChange={(event) => setMinWeight(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800">
              <option value="0">All weights</option>
              <option value="0.25">0.25 and above</option>
              <option value="0.5">0.50 and above</option>
              <option value="0.65">0.65 and above</option>
              <option value="0.9">0.90 only</option>
            </select>
          </label>
          <label className="text-xs text-slate-500">
            Actor type
            <select value={actor} onChange={(event) => setActor(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800">
              <option value="all">All actor types</option>
              {actors.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-500">
            Issue cluster
            <select value={cluster} onChange={(event) => setCluster(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800">
              <option value="all">All issue clusters</option>
              {clusters.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-500">
            Report date from
            <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800" />
          </label>
          <label className="text-xs text-slate-500">
            Report date to
            <input type="date" value={to} onChange={(event) => setTo(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800" />
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Weight band</span>
          {BANDS.map((band) => {
            const active = bands.includes(band)
            return (
              <button
                key={band}
                type="button"
                onClick={() => toggleBand(band)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize ${active ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
              >
                {band}
              </button>
            )
          })}
          <button type="button" onClick={reset} className="ml-auto text-sm text-slate-500 hover:text-slate-800">
            Reset filters
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-200 text-sm text-slate-600">
          <span className="font-semibold text-slate-900">{filtered.length}</span> signal{filtered.length === 1 ? '' : 's'}
          {filtered.length !== signals.length && <span className="text-slate-400"> of {signals.length}</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <SortHeader label="Market" mark={sortMark} onClick={() => toggleSort('market')} />
                <SortHeader label="Date" mark={sortKey === 'date' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'} onClick={() => toggleSort('date')} />
                <SortHeader label="Weight" mark={sortKey === 'weight' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'} onClick={() => toggleSort('weight')} />
                <SortHeader label="Actor" mark={sortKey === 'actor' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'} onClick={() => toggleSort('actor')} />
                <SortHeader label="Focus" mark={sortKey === 'focus' ? (sortOrder === 'asc' ? '↑' : '↓') : '↕'} onClick={() => toggleSort('focus')} />
                <th className="px-3 py-2">Risk or mechanism</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((signal) => (
                <SignalRow
                  key={signal.id}
                  signal={signal}
                  expanded={expandedId === signal.id}
                  onToggle={() => setExpandedId(expandedId === signal.id ? null : signal.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <p className="px-4 py-10 text-center text-sm text-slate-500">No signals match these filters.</p>
        )}
      </div>
    </div>
  )
}

function WeightCard({ weight, count, label, detail }: { weight: string, count: number, label: string, detail: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{weight}</p>
      <p className="text-sm text-slate-600">{count} signal{count === 1 ? '' : 's'}</p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  )
}

function SortHeader({ label, mark, onClick }: { label: string, mark: string, onClick: () => void }) {
  return (
    <th className="px-3 py-2">
      <button type="button" onClick={onClick} className="inline-flex items-center gap-1 hover:text-slate-800">
        {label}
        <span aria-hidden="true">{mark}</span>
      </button>
    </th>
  )
}

function SignalRow({ signal, expanded, onToggle }: { signal: RegulatorySignal, expanded: boolean, onToggle: () => void }) {
  const focus = signal.issue_or_focus.trim() ? displayText(signal.issue_or_focus) : 'Not recorded'
  const risk = signal.specific_risk_or_mechanism
    ? 'Specific risk or mechanism mentioned'
    : 'No specific risk or mechanism recorded'
  return (
    <>
      <tr className="border-b border-slate-100 align-top hover:bg-slate-50">
        <td className="px-3 py-3">
          <button type="button" onClick={onToggle} className="text-left font-medium text-slate-900">
            {marketLabel(signal)}
          </button>
          {officialSourceCounts[signal.market_id] && (
            <p className="text-xs text-slate-400">{officialSourceCounts[signal.market_id].total} official sources</p>
          )}
        </td>
        <td className="px-3 py-3 whitespace-nowrap text-slate-600">{formatReportDate(signal.report_date)}</td>
        <td className="px-3 py-3">
          <span className={`inline-flex flex-col rounded-lg border px-2 py-1 text-xs font-semibold ${weightClass(signal.weight)}`}>
            <span>{formatWeight(signal.weight)} · {signal.weight_band}</span>
            <span className="font-medium">{weightNote(signal)}</span>
          </span>
        </td>
        <td className="px-3 py-3">
          <p className="font-medium text-slate-900">{actorName(signal)}</p>
          <p className="text-xs text-slate-500">{displayText(signal.office)}</p>
          <p className="text-xs text-slate-400">{actorLabel(signal.actor_class)}</p>
        </td>
        <td className="px-3 py-3 text-slate-700 max-w-xs">{focus}</td>
        <td className="px-3 py-3 text-slate-600 max-w-xs">{signal.weight_band === 'medium' || signal.weight < 0.9 ? risk : 'Attributed official signal'}</td>
      </tr>
      {expanded && (
        <tr className="border-b border-slate-100 bg-slate-50">
          <td colSpan={6} className="px-4 py-4 space-y-3">
            <p className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">{displayText(signal.evidence_extract)}</p>
            {signal.weight_rule && <p className="text-xs text-slate-500">{displayText(signal.weight_rule)}</p>}
            <p className="text-xs text-slate-500">
              Report {signal.source_file} · {formatReportDate(signal.report_date)}
              {signal.article_date ? ` · article date ${displayText(signal.article_date)}` : ''}
              {signal.article_outlet ? ` · ${displayText(signal.article_outlet)}` : ''}
            </p>
            {signal.article_url && (
              <a href={signal.article_url} target="_blank" rel="noreferrer" className="text-sm text-blue-700 hover:text-blue-900 break-all">
                {displayText(signal.article_title || signal.article_url)}
              </a>
            )}
          </td>
        </tr>
      )}
    </>
  )
}
