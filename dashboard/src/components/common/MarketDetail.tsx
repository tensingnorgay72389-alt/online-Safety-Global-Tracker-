import { Link } from 'react-router-dom'
import type { Market } from '../../types'
import { OBLIGATION_TYPE_META, PRIORITY_THEME_META } from '../../types'
import { useData } from '../../context/DataContext'
import ServiceTypeTag from './ServiceTypeTag'
import ObligationTag from './ObligationTag'
import StatusBadge from './StatusBadge'

export default function MarketDetail({ market: m }: { market: Market }) {
  const { data } = useData()
  const jurisdiction = data.jurisdictions.find((j) => j.id === m.jurisdiction_id)
  const themes = Array.from(
    new Set(m.obligation_ids.map((o) => OBLIGATION_TYPE_META[o]?.priority).filter(Boolean)),
  )

  return (
    <div className="bg-slate-50 border-t border-slate-200 px-6 py-5">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            {jurisdiction?.flag_emoji ? `${jurisdiction.flag_emoji} ` : ''}{m.country}
          </h3>
          <p className="text-xs text-slate-500">
            {jurisdiction?.region ? `${jurisdiction.region} · ` : ''}{m.id}
            {m.locally_edited ? ' · local edit' : ''}
          </p>
        </div>
        <Link
          to={`/editor?market=${m.id}`}
          className="inline-flex items-center rounded-lg bg-white border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          Edit
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Regulatory status</h4>
            <StatusBadge status={m.regulatory_status} label={m.regulatory_status_label} />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Assessment</h4>
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
              {m.assessment_note || 'No assessment note recorded.'}
            </p>
          </div>

          {m.china_sentiment_trigger && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                China sentiment trigger
              </h4>
              <p className="text-sm text-slate-700 leading-relaxed">{m.china_sentiment_trigger}</p>
            </div>
          )}

          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              All obligations ({m.obligation_ids.length})
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {m.obligation_ids.map((o) => (
                <ObligationTag key={o} type={o} />
              ))}
              {m.obligation_ids.length === 0 && (
                <span className="text-xs text-slate-400">None recorded</span>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Scope / service types
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {m.service_type_ids.map((st) => (
                <ServiceTypeTag key={st} id={st} />
              ))}
              {m.service_type_ids.length === 0 && (
                <span className="text-xs text-slate-400">Not specified</span>
              )}
            </div>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Priority themes
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {themes.map((t) => {
                const meta = PRIORITY_THEME_META[t]
                return (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1 rounded-md text-xs font-medium px-2 py-0.5"
                    style={{ backgroundColor: `${meta.color}14`, color: meta.color }}
                  >
                    {meta.icon} {meta.label}
                  </span>
                )
              })}
              {themes.length === 0 && <span className="text-xs text-slate-400">None recorded</span>}
            </div>
          </div>

          {m.source_url && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Reference</h4>
              <a
                href={m.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline break-all"
              >
                Source
              </a>
            </div>
          )}

          {m.updated_at && (
            <p className="text-xs text-slate-400">Updated {m.updated_at.slice(0, 10)}</p>
          )}
        </div>
      </div>
    </div>
  )
}
