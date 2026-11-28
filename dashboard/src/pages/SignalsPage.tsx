import { useEffect, useMemo, useState } from 'react'
import {
  actorLabel,
  actorName,
  displayText,
  formatReportDate,
  formatWeight,
  signals,
  signalsAsOf,
  type RegulatorySignal,
} from '../data/signals'
import {
  buildSignalPage,
  recordedFocus,
  recordedMarketLabel,
  type CountrySection,
  type PlacedSignal,
} from '../data/signalView'

type Placed = PlacedSignal<RegulatorySignal>
type Section = CountrySection<RegulatorySignal>

function normalise(value: string): string {
  return value.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
}

function scrollToSection(id: string) {
  const node = document.getElementById(id)
  if (!node) return
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  node.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#${id}`)
}

function countryQuery(section: Section): string {
  return normalise([
    section.title,
    section.title === 'Türkiye' ? 'turkey' : '',
    section.earlierSummary,
  ].join(' '))
}

function entryQuery(item: Placed): string {
  const signal = item.signal
  return normalise([
    actorName(signal),
    signal.office,
    signal.organisation,
    signal.actor_class,
    actorLabel(signal.actor_class),
    recordedFocus(signal),
    signal.evidence_extract,
    signal.article_title,
    signal.article_outlet,
    item.articleIso ?? '',
    item.articleIso ? formatReportDate(item.articleIso) : '',
    item.states.join(' '),
    recordedMarketLabel(signal.market_name),
  ].join(' '))
}

function undatedQuery(item: Placed): string {
  const signal = item.signal
  return normalise([
    actorName(signal),
    signal.office,
    signal.organisation,
    signal.article_date,
    actorLabel(signal.actor_class),
  ].join(' '))
}

function officeLine(signal: RegulatorySignal): string {
  const name = actorName(signal)
  const office = displayText(signal.office.trim())
  const actor = actorLabel(signal.actor_class)
  const parts = [name]
  if (office && office !== name) parts.push(office)
  const actorAlreadyShown = office.toLowerCase().includes(actor.toLowerCase()) || name.toLowerCase().includes(actor.toLowerCase())
  if (actor && !actorAlreadyShown) parts.push(actor)
  return parts.join(', ')
}

function focusLine(signal: RegulatorySignal): string {
  return displayText(recordedFocus(signal)) || 'No focus recorded'
}

function countLabel(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`
}

export default function SignalsPage() {
  const model = useMemo(() => buildSignalPage(signals, signalsAsOf), [])
  const [search, setSearch] = useState('')
  const [openIds, setOpenIds] = useState<Set<string>>(() => new Set())

  useEffect(() => {
    const id = window.location.hash.replace(/^#/, '')
    if (!id || id.startsWith('/')) return
    scrollToSection(id)
  }, [])

  const query = normalise(search.trim())
  const sections = useMemo(() => {
    const all = model.unassigned ? [...model.countries, model.unassigned] : model.countries
    if (!query) {
      return all.map((section) => ({
        section,
        recent: section.recent,
        undated: section.undated,
        afterAsOf: section.afterAsOf,
      }))
    }
    return all.flatMap((section) => {
      const countryHit = countryQuery(section).includes(query)
      const recent = countryHit ? section.recent : section.recent.filter((item) => entryQuery(item).includes(query))
      const undated = countryHit ? section.undated : section.undated.filter((item) => undatedQuery(item).includes(query))
      const afterAsOf = countryHit ? section.afterAsOf : section.afterAsOf.filter((item) => entryQuery(item).includes(query))
      if (!countryHit && recent.length === 0 && undated.length === 0 && afterAsOf.length === 0) return []
      return [{ section, recent, undated, afterAsOf }]
    })
  }, [model, query])

  const toggle = (id: string) => {
    setOpenIds((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const asOfLabel = formatReportDate(model.asOf)
  const windowLabel = formatReportDate(model.windowStart)

  return (
    <div className="space-y-6" data-testid="signals-page">
      <div className="max-w-3xl space-y-3">
        <h2 className="text-xl font-bold text-slate-900">Signals</h2>
        <p className="text-sm text-slate-600">
          Each country has one section. Open a recent entry to read the recorded extract.
          A signal that names more than one market is listed under each of those markets.
        </p>
        <p className="text-sm text-slate-600">
          As of {asOfLabel}, an entry opens only when its article date falls on or between {windowLabel} and {asOfLabel}.
          The date used for this window is the article date recorded on the signal. An open entry also shows the monitoring report date.
          A signal with no full calendar article date is marked undated and stays closed.
          These records do not change a market score and are not added to the instrument list.
        </p>
        <p className="text-sm font-medium text-slate-800">
          {model.countries.length} countries and recorded markets. {model.countriesWithRecent} have a recent entry. {model.summaryOnlyCountries} have earlier signals only.
        </p>
        {model.unassigned && (
          <p className="text-sm text-slate-600">{unassignedNote(model.unassigned)}</p>
        )}
        {model.undatedCount > 0 && (
          <p className="text-sm text-slate-700">
            {countLabel(model.undatedCount, 'signal has', 'signals have')} no reliable article date.
            Undated signals are marked in their section and stay closed.
          </p>
        )}
      </div>

      <div className="space-y-3" id="market-index" data-testid="market-index">
        <label className="block text-sm font-medium text-slate-700" htmlFor="signal-search">
          Find a country
        </label>
        <input
          id="signal-search"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search countries and recent entries"
          className="w-full max-w-xl px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="text-xs text-slate-500">
          A blue chip has an entry in the last three months. A grey chip has earlier signals only.
        </p>
        {sections.length === 0 ? (
          <p className="text-sm text-slate-500">No market matches this search.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {sections.map(({ section, recent }) => {
              const hasRecent = recent.length > 0
              return (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => scrollToSection(section.id)}
                  className={`text-left rounded-lg border px-3 py-2 max-w-xs ${
                    hasRecent
                      ? 'bg-blue-50 border-blue-200 hover:border-blue-400'
                      : 'bg-slate-50 border-slate-200 hover:border-slate-400'
                  }`}
                >
                  <span className="block text-sm font-medium text-slate-900">{displayText(section.title)}</span>
                  <span className="block text-xs text-slate-500">
                    {hasRecent ? countLabel(recent.length, 'recent entry', 'recent entries') : 'Earlier only'}
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </div>

      <div className="space-y-4">
        {sections.map(({ section, recent, undated, afterAsOf }) => (
          <section
            key={section.id}
            id={section.id}
            data-testid="market-section"
            className="bg-white rounded-xl border border-slate-200 shadow-sm scroll-mt-36"
          >
            <div className="px-4 py-4 border-b border-slate-100 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">{displayText(section.title)}</h3>
                <p className="text-sm text-slate-500">
                  {query && recent.length !== section.recent.length
                    ? `Showing ${countLabel(recent.length, 'matching recent entry', 'matching recent entries')}`
                    : sectionMeta(section)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => scrollToSection('market-index')}
                className="text-xs font-medium text-blue-700 hover:text-blue-900"
              >
                Back to countries
              </button>
            </div>

            <div className="px-4 py-4 space-y-4">
              {recent.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recent entries</h4>
                  <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg">
                    {recent.map((item) => {
                      const entryId = `${section.id}:${item.signal.id}`
                      return (
                        <RecentEntry
                          key={entryId}
                          item={item}
                          panelId={entryId}
                          open={openIds.has(entryId)}
                          onToggle={() => toggle(entryId)}
                        />
                      )
                    })}
                  </div>
                </div>
              )}

              {section.earlierSummary && (
                <div data-testid="earlier-summary">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Earlier signals</h4>
                  <p className="mt-1 text-sm text-slate-700 leading-relaxed">{section.earlierSummary}</p>
                </div>
              )}

              {undated.length > 0 && (
                <UndatedList items={undated} />
              )}

              {afterAsOf.length > 0 && (
                <div data-testid="after-as-of">
                  <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">After the as-of date</h4>
                  <p className="mt-1 text-sm text-slate-700">
                    These signals have an article date after {asOfLabel}. They are not opened as recent entries.
                  </p>
                  <ul className="mt-2 space-y-1">
                    {afterAsOf.map((item) => (
                      <li key={item.signal.id} className="text-sm text-slate-700">
                        {officeLine(item.signal)}. Article date {item.articleIso ? formatReportDate(item.articleIso) : displayText(item.signal.article_date)}.
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {recent.length === 0 && !section.earlierSummary && undated.length === 0 && afterAsOf.length === 0 && (
                <p className="text-sm text-slate-500">No signals are listed for this market.</p>
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}

function unassignedNote(section: Section): string {
  const total = section.recent.length + section.earlier.length + section.undated.length + section.afterAsOf.length
  const sentences = [
    `${total} ${total === 1 ? 'signal does' : 'signals do'} not name a market.`,
  ]
  if (section.recent.length) {
    sentences.push(`${section.recent.length} of those ${section.recent.length === 1 ? 'has' : 'have'} an article date in this window.`)
  }
  if (section.earlier.length) {
    sentences.push(`${section.earlier.length} of those ${section.earlier.length === 1 ? 'is' : 'are'} earlier.`)
  }
  if (section.undated.length) {
    sentences.push(`${section.undated.length} of those ${section.undated.length === 1 ? 'has' : 'have'} no reliable article date.`)
  }
  sentences.push(total === 1
    ? 'It sits under Market not recorded and is not assigned to a country.'
    : 'They sit under Market not recorded and are not assigned to a country.')
  return sentences.join(' ')
}

function sectionMeta(section: Section): string {
  const parts = [
    section.recent.length
      ? countLabel(section.recent.length, 'recent entry', 'recent entries')
      : 'No recent entries',
  ]
  if (section.earlier.length) parts.push(countLabel(section.earlier.length, 'earlier signal', 'earlier signals'))
  if (section.undated.length) parts.push(countLabel(section.undated.length, 'undated signal', 'undated signals'))
  if (section.afterAsOf.length) parts.push(countLabel(section.afterAsOf.length, 'signal after the as-of date', 'signals after the as-of date'))
  return parts.join(' · ')
}

function RecentEntry({ item, open, onToggle, panelId }: { item: Placed, open: boolean, onToggle: () => void, panelId: string }) {
  const signal = item.signal
  const panelDomId = `signal-panel-${panelId.replace(/[^a-z0-9:-]+/gi, '-')}`
  const dateLabel = item.articleIso ? formatReportDate(item.articleIso) : ''
  const showMarket = item.joint || item.states.length > 0
  return (
    <div data-testid="recent-entry">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelDomId}
        onClick={onToggle}
        className="w-full text-left px-3 py-3 hover:bg-slate-50"
      >
        <span className="flex items-start justify-between gap-3">
          <span className="min-w-0">
            <span className="block text-sm font-medium text-slate-900">{officeLine(signal)}</span>
            <span className="block text-sm text-slate-600">{dateLabel}</span>
            <span className="block text-sm text-slate-500">{focusLine(signal)}</span>
            {showMarket && (
              <span className="block text-xs text-slate-500 mt-1">
                Recorded market: {displayText(recordedMarketLabel(signal.market_name))}
              </span>
            )}
          </span>
          <span className="shrink-0 text-xs font-semibold uppercase tracking-wide text-blue-700">
            {open ? 'Hide' : 'Show'}
          </span>
        </span>
      </button>
      {open && (
        <div id={panelDomId} className="px-3 pb-4 space-y-2 bg-slate-50">
          <p className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed">{displayText(signal.evidence_extract)}</p>
          <p className="text-xs text-slate-500">
            Article date {dateLabel}. Weight {formatWeight(signal.weight)} ({signal.weight_band}).
          </p>
          {signal.weight_rule.trim() && (
            <p className="text-xs text-slate-500">{displayText(signal.weight_rule)}</p>
          )}
          <p className="text-xs text-slate-500">
            Monitoring report {signal.source_file}. Report date {formatReportDate(signal.report_date)}.
            {signal.article_outlet.trim() ? ` Outlet ${displayText(signal.article_outlet)}.` : ''}
          </p>
          {signal.article_url.trim() && (
            <a href={signal.article_url} target="_blank" rel="noreferrer" className="block text-sm text-blue-700 hover:text-blue-900 [overflow-wrap:break-word]">
              {displayText(signal.article_title.trim() || 'Source article')}
            </a>
          )}
        </div>
      )}
    </div>
  )
}

function UndatedList({ items }: { items: Placed[] }) {
  return (
    <div data-testid="undated-signals">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Undated signals</h4>
      <p className="mt-1 text-sm text-slate-700">
        These signals have no reliable article date. They are not opened and they are not part of the earlier summary.
      </p>
      <ul className="mt-2 space-y-1">
        {items.map((item) => {
          const raw = item.signal.article_date.trim()
          const dateNote = raw
            ? `Article date on file is not a full calendar date: ${displayText(raw)}.`
            : 'Article date not recorded.'
          return (
            <li key={item.signal.id} className="text-sm text-slate-700">
              {officeLine(item.signal)}. {dateNote}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
