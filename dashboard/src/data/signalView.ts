// Groups ranked signals for the Signals page.
// Dates, markets and focus labels come only from the signal records.

export interface DatedSignal {
  id: string
  market_name: string
  article_date: string
  issue_or_focus: string
  issue_clusters: string[]
}

export interface MarketPlace {
  country: string
  state: string | null
  recordedPart: string
}

export interface PlacedSignal<T extends DatedSignal> {
  signal: T
  articleIso: string | null
  states: string[]
  joint: boolean
  otherMarkets: string[]
}

export interface CountrySection<T extends DatedSignal> {
  id: string
  title: string
  recent: PlacedSignal<T>[]
  earlier: PlacedSignal<T>[]
  earlierSummary: string
  undated: PlacedSignal<T>[]
  afterAsOf: PlacedSignal<T>[]
}

export interface SignalPageModel<T extends DatedSignal> {
  asOf: string
  windowStart: string
  signalCount: number
  recentCount: number
  earlierCount: number
  undatedCount: number
  afterCount: number
  countries: CountrySection<T>[]
  unassigned: CountrySection<T> | null
  countriesWithRecent: number
  summaryOnlyCountries: number
}

const MONTHS: Record<string, number> = {
  january: 1,
  february: 2,
  march: 3,
  april: 4,
  may: 5,
  june: 6,
  july: 7,
  august: 8,
  september: 9,
  october: 10,
  november: 11,
  december: 12,
}

const UNRECORDED_FOCUS = 'Not recorded'
const DASH = /\s*[—–]\s*/

export function calendarIso(year: number, month: number, day: number): string | null {
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null
  if (month < 1 || month > 12 || day < 1) return null
  const date = new Date(Date.UTC(year, month - 1, day))
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

// A reliable article date is a real calendar day. Month-only, year-only and ranges stay undated.
export function parseArticleDate(value: string): string | null {
  const text = value.trim()
  if (!text) return null
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text)
  if (iso) return calendarIso(Number(iso[1]), Number(iso[2]), Number(iso[3]))
  const monthFirst = /^([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})$/.exec(text)
  if (monthFirst) {
    const month = MONTHS[monthFirst[1].toLowerCase()]
    if (!month) return null
    return calendarIso(Number(monthFirst[3]), month, Number(monthFirst[2]))
  }
  const dayFirst = /^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/.exec(text)
  if (dayFirst) {
    const month = MONTHS[dayFirst[2].toLowerCase()]
    if (!month) return null
    return calendarIso(Number(dayFirst[3]), month, Number(dayFirst[1]))
  }
  return null
}

export function shiftIsoDate(iso: string, months: number): string {
  const parsed = parseArticleDate(iso)
  if (!parsed) throw new Error('as-of date is not a full calendar date')
  const [yearText, monthText, dayText] = parsed.split('-')
  const year = Number(yearText)
  const monthIndex = Number(monthText) - 1 + months
  const shiftedYear = year + Math.floor(monthIndex / 12)
  const shiftedMonth = ((monthIndex % 12) + 12) % 12
  const day = Number(dayText)
  const daysInMonth = new Date(Date.UTC(shiftedYear, shiftedMonth + 1, 0)).getUTCDate()
  const shifted = calendarIso(shiftedYear, shiftedMonth + 1, Math.min(day, daysInMonth))
  if (!shifted) throw new Error('shifted date is not a full calendar date')
  return shifted
}

export function marketPlaces(marketName: string): MarketPlace[] {
  const name = marketName.trim()
  if (!name) return []
  const places: MarketPlace[] = []
  for (const part of name.split(',')) {
    const recorded = part.trim()
    if (!recorded) continue
    const bits = recorded.split(DASH)
    if (bits.length === 2 && bits[0].trim() && bits[1].trim()) {
      places.push({
        country: bits[0].trim(),
        state: bits[1].trim(),
        recordedPart: recorded,
      })
    } else {
      places.push({
        country: recorded,
        state: null,
        recordedPart: recorded,
      })
    }
  }
  return places
}

export function recordedMarketLabel(marketName: string): string {
  return marketPlaces(marketName).map((part) => (
    part.state ? `${part.country} - ${part.state}` : part.country
  )).join(', ')
}

export function focusLabels(signal: DatedSignal): string[] {
  const seen = new Set<string>()
  const labels: string[] = []
  for (const raw of signal.issue_clusters) {
    const label = raw.trim()
    if (!label || label === UNRECORDED_FOCUS || seen.has(label)) continue
    seen.add(label)
    labels.push(label)
  }
  return labels
}

export function joinAnd(items: readonly string[]): string {
  if (items.length === 0) return ''
  if (items.length === 1) return items[0]
  if (items.length === 2) return `${items[0]} and ${items[1]}`
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
}

export function recordedFocus(signal: DatedSignal): string {
  const focus = signal.issue_or_focus.trim()
  if (focus) return focus
  return joinAnd(focusLabels(signal))
}

export function sectionId(title: string): string {
  const slug = title
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return `market-${slug || 'blank'}`
}

function uniqueCountries(marketName: string): string[] {
  const countries: string[] = []
  const seen = new Set<string>()
  for (const part of marketPlaces(marketName)) {
    if (seen.has(part.country)) continue
    seen.add(part.country)
    countries.push(part.country)
  }
  return countries
}

function placeSignal<T extends DatedSignal>(signal: T, articleIso: string | null, country: string): PlacedSignal<T> {
  const parts = marketPlaces(signal.market_name)
  const countries = uniqueCountries(signal.market_name)
  const states: string[] = []
  const seenStates = new Set<string>()
  for (const part of parts) {
    if (part.country !== country || !part.state || seenStates.has(part.state)) continue
    seenStates.add(part.state)
    states.push(part.state)
  }
  return {
    signal,
    articleIso,
    states,
    joint: countries.length > 1,
    otherMarkets: countries.filter((item) => item !== country),
  }
}

function countSentence(total: number, count: number, singular: string, plural: string): string | null {
  if (count === 0) return null
  if (total === 1) return `It ${singular}.`
  if (count === 1) return `1 of them ${singular}.`
  return `${count} of them ${plural}.`
}

export function earlierSummary<T extends DatedSignal>(items: readonly PlacedSignal<T>[]): string {
  const total = items.length
  if (total === 0) return ''
  const sentences = [`${total} earlier ${total === 1 ? 'signal is' : 'signals are'} on file.`]
  const stateSentence = countSentence(
    total,
    items.filter((item) => item.states.length > 0).length,
    'is recorded against a named state',
    'are recorded against a named state',
  )
  const jointSentence = countSentence(
    total,
    items.filter((item) => item.joint).length,
    'names more than one market',
    'name more than one market',
  )
  if (stateSentence) sentences.push(stateSentence)
  if (jointSentence) sentences.push(jointSentence)

  if (total === 1) {
    const focus = items[0].signal.issue_or_focus.trim()
    const labels = focusLabels(items[0].signal)
    if (focus) sentences.push(`The recorded focus is ${focus}.`)
    else if (labels.length) sentences.push(`The recorded focus is ${joinAnd(labels)}.`)
    else sentences.push('It does not record a focus.')
    return sentences.join(' ')
  }

  const labelCounts = new Map<string, number>()
  let noFocus = 0
  for (const item of items) {
    const labels = focusLabels(item.signal)
    if (labels.length === 0) noFocus += 1
    for (const label of labels) labelCounts.set(label, (labelCounts.get(label) ?? 0) + 1)
  }
  const ranked = [...labelCounts.entries()].sort((left, right) => (
    right[1] - left[1] || left[0].localeCompare(right[0], 'en-GB')
  ))

  if (noFocus === total) {
    sentences.push(total === 1 ? 'It does not record a focus.' : 'None of them records a focus.')
  } else if (noFocus > 0) {
    const missing = countSentence(total, noFocus, 'does not record a focus', 'do not record a focus')
    if (missing) sentences.push(missing)
  }

  if (ranked.length === 1 && noFocus === 0) {
    sentences.push(`The recorded focus is ${ranked[0][0]}.`)
  } else if (ranked.length > 0) {
    const listed = joinAnd(ranked.map(([label, count]) => `${label} (${count})`))
    sentences.push(`Where a focus is recorded, the ${ranked.length === 1 ? 'label is' : 'labels are'} ${listed}.`)
  }

  return sentences.join(' ')
}

type Timing = 'recent' | 'earlier' | 'undated' | 'after'

function timingOf(articleIso: string | null, windowStart: string, asOf: string): Timing {
  if (!articleIso) return 'undated'
  if (articleIso > asOf) return 'after'
  if (articleIso >= windowStart) return 'recent'
  return 'earlier'
}

function toSection<T extends DatedSignal>(
  title: string,
  items: PlacedSignal<T>[],
  windowStart: string,
  asOf: string,
): CountrySection<T> {
  const recent: PlacedSignal<T>[] = []
  const earlier: PlacedSignal<T>[] = []
  const undated: PlacedSignal<T>[] = []
  const afterAsOf: PlacedSignal<T>[] = []
  for (const item of items) {
    const timing = timingOf(item.articleIso, windowStart, asOf)
    if (timing === 'recent') recent.push(item)
    else if (timing === 'earlier') earlier.push(item)
    else if (timing === 'undated') undated.push(item)
    else afterAsOf.push(item)
  }
  recent.sort((left, right) => (
    (right.articleIso ?? '').localeCompare(left.articleIso ?? '') || left.signal.id.localeCompare(right.signal.id)
  ))
  earlier.sort((left, right) => (
    (right.articleIso ?? '').localeCompare(left.articleIso ?? '') || left.signal.id.localeCompare(right.signal.id)
  ))
  undated.sort((left, right) => left.signal.id.localeCompare(right.signal.id))
  afterAsOf.sort((left, right) => (
    (right.articleIso ?? '').localeCompare(left.articleIso ?? '') || left.signal.id.localeCompare(right.signal.id)
  ))
  return {
    id: sectionId(title),
    title,
    recent,
    earlier,
    earlierSummary: earlierSummary(earlier),
    undated,
    afterAsOf,
  }
}

export function buildSignalPage<T extends DatedSignal>(rows: readonly T[], asOf: string): SignalPageModel<T> {
  const asOfIso = parseArticleDate(asOf)
  if (!asOfIso) throw new Error('as-of date is not a full calendar date')
  const windowStart = shiftIsoDate(asOfIso, -3)
  const buckets = new Map<string, Map<string, PlacedSignal<T>>>()
  const unassigned = new Map<string, PlacedSignal<T>>()
  let recentCount = 0
  let earlierCount = 0
  let undatedCount = 0
  let afterCount = 0

  for (const signal of rows) {
    const articleIso = parseArticleDate(signal.article_date)
    const timing = timingOf(articleIso, windowStart, asOfIso)
    if (timing === 'recent') recentCount += 1
    else if (timing === 'earlier') earlierCount += 1
    else if (timing === 'undated') undatedCount += 1
    else afterCount += 1

    const countries = uniqueCountries(signal.market_name)
    if (countries.length === 0) {
      unassigned.set(signal.id, placeSignal(signal, articleIso, ''))
      continue
    }
    for (const country of countries) {
      let bucket = buckets.get(country)
      if (!bucket) {
        bucket = new Map()
        buckets.set(country, bucket)
      }
      bucket.set(signal.id, placeSignal(signal, articleIso, country))
    }
  }

  const countries = [...buckets.entries()]
    .map(([title, bucket]) => toSection(title, [...bucket.values()], windowStart, asOfIso))
    .sort((left, right) => left.title.localeCompare(right.title, 'en-GB'))

  return {
    asOf: asOfIso,
    windowStart,
    signalCount: rows.length,
    recentCount,
    earlierCount,
    undatedCount,
    afterCount,
    countries,
    unassigned: unassigned.size ? toSection('Market not recorded', [...unassigned.values()], windowStart, asOfIso) : null,
    countriesWithRecent: countries.filter((section) => section.recent.length > 0).length,
    summaryOnlyCountries: countries.filter((section) => section.recent.length === 0 && section.earlier.length > 0).length,
  }
}
