import { useMemo, useState } from 'react'
import { useData } from '../context/DataContext'
import { verifiedRegisterCounts } from '../data/dataset'
import type { NewsItem, Regulation, RegulationStatus } from '../types'
import { SERVICE_TYPE_META, STATUS_META } from '../types'
import StatusBadge from '../components/common/StatusBadge'
import ObligationTag from '../components/common/ObligationTag'
import ServiceTypeTag from '../components/common/ServiceTypeTag'

type RegisterView = 'instruments' | 'news'
type SortKey = 'name' | 'jurisdiction' | 'year' | 'status'

function formatWhen(iso: string | undefined) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso.slice(0, 10)
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function humanise(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function RegisterPage() {
  const { regulations, newsItems, data } = useData()
  const [view, setView] = useState<RegisterView>('instruments')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<RegulationStatus | 'all'>('all')
  const [kind, setKind] = useState('all')
  const [service, setService] = useState('all')
  const [sortKey, setSortKey] = useState<SortKey>('jurisdiction')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const kinds = useMemo(() => {
    return Array.from(new Set(regulations.map((r) => r.instrument_kind).filter(Boolean) as string[])).sort()
  }, [regulations])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    const rows = regulations.filter((r) => {
      if (status !== 'all' && r.status !== status) return false
      if (kind !== 'all' && r.instrument_kind !== kind) return false
      if (service !== 'all' && !r.service_type_ids.includes(service as Regulation['service_type_ids'][number])) return false
      if (!q) return true
      const hay = [
        r.name,
        r.official_title,
        r.summary,
        r.id,
        r.jurisdiction_id,
        r.jurisdiction_name,
      ].filter(Boolean).join(' ').toLowerCase()
      return hay.includes(q)
    })
    const jurisdictionName = (r: Regulation) =>
      r.jurisdiction_name
      || data.jurisdictions.find((j) => j.id === r.jurisdiction_id)?.name
      || r.jurisdiction_id
    rows.sort((a, b) => {
      if (sortKey === 'name') return a.name.localeCompare(b.name, 'en-GB')
      if (sortKey === 'year') return (b.year || 0) - (a.year || 0) || a.name.localeCompare(b.name, 'en-GB')
      if (sortKey === 'status') {
        return (STATUS_META[a.status]?.order ?? 99) - (STATUS_META[b.status]?.order ?? 99)
      }
      return jurisdictionName(a).localeCompare(jurisdictionName(b), 'en-GB') || a.name.localeCompare(b.name, 'en-GB')
    })
    return rows
  }, [data.jurisdictions, kind, regulations, search, service, sortKey, status])

  const news = useMemo(() => {
    const q = search.trim().toLowerCase()
    return [...newsItems]
      .filter((item) => {
        if (!q) return true
        return [item.title, item.snippet, item.source, item.classification?.summary, item.classification?.regulation_id]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(q)
      })
      .sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''))
  }, [newsItems, search])

  const showInstrument = (id: string) => {
    setView('instruments')
    setSearch(id)
    setExpandedId(id)
    setStatus('all')
    setKind('all')
    setService('all')
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Regulations Register</h2>
        <p className="text-sm text-slate-500 max-w-3xl">
          Instruments and monitoring items, including the verified 27 November 2026 register
          ({verifiedRegisterCounts.regulations} regulations, {verifiedRegisterCounts.obligations} obligations, {verifiedRegisterCounts.milestones} milestones).
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setView('instruments')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium ${view === 'instruments' ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-700'}`}
        >
          Instruments ({regulations.length})
        </button>
        <button
          type="button"
          onClick={() => setView('news')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium ${view === 'news' ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-700'}`}
        >
          Monitoring news ({newsItems.length})
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={view === 'news' ? 'Search monitoring items…' : 'Search instruments by name, jurisdiction or summary…'}
          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {view === 'instruments' && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <label className="text-xs text-slate-500">
              Status
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as RegulationStatus | 'all')}
                className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800"
              >
                <option value="all">All statuses</option>
                {(Object.keys(STATUS_META) as RegulationStatus[]).map((key) => (
                  <option key={key} value={key}>{STATUS_META[key].label}</option>
                ))}
              </select>
            </label>
            <label className="text-xs text-slate-500">
              Instrument kind
              <select
                value={kind}
                onChange={(e) => setKind(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800"
              >
                <option value="all">All kinds</option>
                {kinds.map((item) => (
                  <option key={item} value={item}>{humanise(item)}</option>
                ))}
              </select>
            </label>
            <label className="text-xs text-slate-500">
              Service
              <select
                value={service}
                onChange={(e) => setService(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800"
              >
                <option value="all">All services</option>
                {Object.entries(SERVICE_TYPE_META).map(([id, meta]) => (
                  <option key={id} value={id}>{meta.label}</option>
                ))}
              </select>
            </label>
            <label className="text-xs text-slate-500">
              Sort
              <select
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as SortKey)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-2 py-2 text-sm text-slate-800"
              >
                <option value="jurisdiction">Jurisdiction</option>
                <option value="name">Name</option>
                <option value="year">Year</option>
                <option value="status">Status</option>
              </select>
            </label>
          </div>
        )}
      </div>

      {view === 'instruments' ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-200 text-sm text-slate-600">
            <span className="font-semibold text-slate-900">{filtered.length}</span> instrument{filtered.length === 1 ? '' : 's'}
          </div>
          <div className="divide-y divide-slate-100">
            {filtered.map((reg) => (
              <InstrumentRow
                key={reg.id}
                regulation={reg}
                expanded={expandedId === reg.id}
                onToggle={() => setExpandedId(expandedId === reg.id ? null : reg.id)}
                newsItems={newsItems.filter((item) => item.classification?.regulation_id === reg.id)}
              />
            ))}
            {filtered.length === 0 && (
              <p className="px-4 py-10 text-center text-sm text-slate-500">No instruments match these filters.</p>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {news.map((item) => (
            <NewsCard key={item.id} item={item} onShowInstrument={showInstrument} />
          ))}
          {news.length === 0 && (
            <p className="text-sm text-slate-500">No monitoring items match this search.</p>
          )}
        </div>
      )}
    </div>
  )
}

function InstrumentRow({
  regulation: reg,
  expanded,
  onToggle,
  newsItems,
}: {
  regulation: Regulation
  expanded: boolean
  onToggle: () => void
  newsItems: NewsItem[]
}) {
  const place = reg.jurisdiction_name || reg.jurisdiction_id
  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        className="w-full text-left px-4 py-3 hover:bg-slate-50"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-medium text-slate-900">{reg.name}</p>
            <p className="text-xs text-slate-500 mt-0.5">
              {place} · {reg.year || 'Year not recorded'} · {reg.id}
              {reg.instrument_kind ? ` · ${humanise(reg.instrument_kind)}` : ''}
            </p>
          </div>
          <StatusBadge status={reg.status} />
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-4 bg-slate-50 border-t border-slate-100">
          {reg.official_title && (
            <p className="text-sm text-slate-600 pt-3">{reg.official_title}</p>
          )}
          <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{reg.summary}</p>
          <div className="flex flex-wrap gap-1.5">
            {reg.service_type_ids.map((id) => (
              <ServiceTypeTag key={id} id={id as keyof typeof SERVICE_TYPE_META} />
            ))}
          </div>
          {reg.effective_date && (
            <p className="text-xs text-slate-500">Effective date: {formatWhen(reg.effective_date)}</p>
          )}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Obligations ({reg.obligations.length})
            </h4>
            <div className="space-y-1.5">
              {reg.obligations.map((ob) => (
                <div key={ob.id} className="text-sm text-slate-700">
                  <ObligationTag type={ob.type} thresholdLabel={ob.threshold_label} />
                  <span className="ml-2">{ob.description}</span>
                </div>
              ))}
              {reg.obligations.length === 0 && <p className="text-xs text-slate-400">No itemised obligation text on this record.</p>}
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Milestones ({reg.milestones.length})
            </h4>
            <ol className="space-y-1.5">
              {reg.milestones.map((ms) => (
                <li key={ms.id} className="text-sm text-slate-700">
                  <span className="text-slate-500">{formatWhen(ms.date) || 'Date not recorded'}</span>
                  {' · '}
                  <span className="font-medium">{humanise(ms.type)}</span>
                  {' — '}
                  {ms.description}
                </li>
              ))}
              {reg.milestones.length === 0 && <li className="text-xs text-slate-400">No milestones recorded.</li>}
            </ol>
          </div>
          {reg.litigations.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Litigation</h4>
              <ul className="space-y-1">
                {reg.litigations.map((item) => (
                  <li key={item.id} className="text-sm text-slate-700">
                    {item.name} · {humanise(item.status)}
                    {item.description ? ` — ${item.description}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {newsItems.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Related monitoring</h4>
              <ul className="space-y-1">
                {newsItems.map((item) => (
                  <li key={item.id}>
                    <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-700 hover:underline">
                      {item.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {reg.source_url && (
            <a href={reg.source_url} target="_blank" rel="noopener noreferrer" className="inline-block text-sm text-blue-700 hover:underline break-all">
              Official source
            </a>
          )}
        </div>
      )}
    </div>
  )
}

function NewsCard({ item, onShowInstrument }: { item: NewsItem; onShowInstrument: (id: string) => void }) {
  const classification = item.classification
  return (
    <article className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-2">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-medium text-slate-900">
          <a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-700">
            {item.title}
          </a>
        </h3>
        <time className="text-xs text-slate-500 whitespace-nowrap">{formatWhen(item.published_at)}</time>
      </div>
      <p className="text-xs text-slate-500">{item.source}</p>
      <p className="text-sm text-slate-700">{item.snippet}</p>
      {classification?.summary && (
        <p className="text-sm text-slate-600">{classification.summary}</p>
      )}
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {classification?.action_type && <span className="rounded-full bg-slate-100 px-2 py-0.5">{humanise(classification.action_type)}</span>}
        {classification?.confidence != null && <span>Confidence {Math.round(classification.confidence * 100)}%</span>}
        {classification?.regulation_id && (
          <button
            type="button"
            onClick={() => onShowInstrument(classification.regulation_id as string)}
            className="text-blue-700 hover:underline"
          >
            Instrument {classification.regulation_id}
          </button>
        )}
      </div>
    </article>
  )
}
