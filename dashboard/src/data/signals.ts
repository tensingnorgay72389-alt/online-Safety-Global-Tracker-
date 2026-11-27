import signalsFile from '../../data/signals.json'

export type SignalWeightBand = 'high' | 'medium' | 'low'

export interface RegulatorySignal {
  id: string
  weight: number
  weight_band: SignalWeightBand
  weight_rule: string
  person_name: string
  office: string
  organisation: string
  actor_class: string
  market_id: string
  market_name: string
  issue_or_focus: string
  issue_clusters: string[]
  specific_risk_or_mechanism: boolean
  evidence_extract: string
  source_file: string
  report_date: string
  article_date: string
  article_title: string
  article_outlet: string
  article_url: string
  mention_count: number
}

export interface OfficialSourceCount {
  market_name: string
  total: number
}

export type SignalSortKey = 'market' | 'date' | 'weight' | 'actor' | 'focus'

export const signals = signalsFile.signals as RegulatorySignal[]
export const signalCounts = signalsFile.counts
export const officialSourceCounts = signalsFile.official_source_counts as Record<string, OfficialSourceCount>

export const ACTOR_LABELS: Record<string, string> = {
  minister: 'Minister',
  legislator: 'Legislator',
  'head of government or president': 'Head of government or president',
  'attorney general': 'Attorney general',
  'ngo or civil society organisation': 'NGO or civil society organisation',
  'ngo or civil society actor': 'NGO or civil society actor',
  'committee or body chair': 'Committee or body chair',
  'us state governor': 'US state governor',
  'official or politician': 'Official or politician',
  'regulator head': 'Regulator head',
  'european commissioner': 'European Commissioner',
  'law-enforcement head': 'Law-enforcement head',
  'statutory regulator': 'Statutory regulator',
  'former official': 'Former official',
  'local official': 'Local official',
}

export function displayText(value: string): string {
  return value.replaceAll('\u2014', ' - ').replaceAll('\u2013', ' - ')
}

export function marketLabel(signal: RegulatorySignal): string {
  const name = signal.market_name.trim()
  return name ? displayText(name) : 'Not recorded'
}

export function marketKey(signal: RegulatorySignal): string {
  return signal.market_id.trim() || `unrecorded:${marketLabel(signal)}`
}

export function actorLabel(actorClass: string): string {
  return ACTOR_LABELS[actorClass] ?? actorClass
}

export function actorName(signal: RegulatorySignal): string {
  return displayText(signal.person_name.trim() || signal.organisation.trim() || signal.office.trim() || 'Name not recorded')
}

export function formatWeight(weight: number): string {
  return weight.toFixed(2)
}

export function formatReportDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (!match) return iso
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])))
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

export function weightNote(signal: RegulatorySignal): string {
  if (signal.weight >= 0.9) return 'Incorporated'
  if (signal.weight >= 0.65) return 'Risk or mechanism mentioned'
  if (signal.weight >= 0.5) return 'Review only'
  return 'Low confidence'
}

function normalise(value: string): string {
  return value.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
}

export interface SignalQuery {
  search: string
  market: string
  bands: SignalWeightBand[]
  actor: string
  cluster: string
  minWeight: number
  from: string
  to: string
}

export function filterSignals(rows: RegulatorySignal[], query: SignalQuery): RegulatorySignal[] {
  const search = normalise(query.search.trim())
  return rows.filter((signal) => {
    if (query.market !== 'all' && marketKey(signal) !== query.market) return false
    if (query.bands.length && !query.bands.includes(signal.weight_band)) return false
    if (query.actor !== 'all' && signal.actor_class !== query.actor) return false
    if (query.cluster !== 'all' && !signal.issue_clusters.includes(query.cluster)) return false
    if (Number(signal.weight.toFixed(2)) < Number(query.minWeight.toFixed(2))) return false
    if (query.from && signal.report_date < query.from) return false
    if (query.to && signal.report_date > query.to) return false
    if (!search) return true
    const haystack = normalise([
      marketLabel(signal),
      signal.market_id,
      signal.market_id === 'tr' ? 'turkey turkiye' : '',
      actorName(signal),
      signal.office,
      signal.organisation,
      signal.evidence_extract,
      signal.issue_or_focus,
      actorLabel(signal.actor_class),
      signal.article_title,
      signal.article_outlet,
    ].join(' '))
    return haystack.includes(search)
  })
}

const WEIGHT_RANK: Record<SignalWeightBand, number> = { high: 0, medium: 1, low: 2 }

export function sortSignals(
  rows: RegulatorySignal[],
  sortKey: SignalSortKey,
  sortOrder: 'asc' | 'desc',
): RegulatorySignal[] {
  const direction = sortOrder === 'asc' ? 1 : -1
  return [...rows].sort((left, right) => {
    const primary = sortKey === 'market'
      ? marketLabel(left).localeCompare(marketLabel(right), 'en-GB')
      : sortKey === 'date'
        ? left.report_date.localeCompare(right.report_date)
        : sortKey === 'weight'
          ? left.weight - right.weight || WEIGHT_RANK[left.weight_band] - WEIGHT_RANK[right.weight_band]
          : sortKey === 'actor'
            ? actorName(left).localeCompare(actorName(right), 'en-GB')
            : (left.issue_or_focus || 'Not recorded').localeCompare(right.issue_or_focus || 'Not recorded', 'en-GB')
    const tie = marketLabel(left).localeCompare(marketLabel(right), 'en-GB') || right.report_date.localeCompare(left.report_date)
    return (primary || tie) * direction
  })
}

export function marketOptions(rows: RegulatorySignal[]): { id: string, label: string }[] {
  const byId = new Map<string, string>()
  for (const signal of rows) byId.set(marketKey(signal), marketLabel(signal))
  return [...byId.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((left, right) => {
      if (left.label === 'Not recorded') return 1
      if (right.label === 'Not recorded') return -1
      return left.label.localeCompare(right.label, 'en-GB')
    })
}

export function clusterOptions(rows: RegulatorySignal[]): string[] {
  const values = new Set<string>()
  for (const signal of rows) {
    for (const cluster of signal.issue_clusters) values.add(cluster)
  }
  return [...values].sort((left, right) => {
    if (left === 'Not recorded') return 1
    if (right === 'Not recorded') return -1
    return left.localeCompare(right, 'en-GB')
  })
}

export function actorOptions(rows: RegulatorySignal[]): { id: string, label: string }[] {
  const values = new Set(rows.map((signal) => signal.actor_class).filter(Boolean))
  return [...values]
    .map((id) => ({ id, label: actorLabel(id) }))
    .sort((left, right) => left.label.localeCompare(right.label, 'en-GB'))
}
