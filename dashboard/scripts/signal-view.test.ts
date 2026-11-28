import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  buildSignalPage,
  earlierSummary,
  parseArticleDate,
  recordedMarketLabel,
  shiftIsoDate,
  type DatedSignal,
} from '../src/data/signalView.ts'

const root = dirname(fileURLToPath(import.meta.url))
const payload = JSON.parse(readFileSync(resolve(root, '../data/signals.json'), 'utf8')) as {
  as_of: string
  signals: DatedSignal[]
}

const pageSource = readFileSync(resolve(root, '../src/pages/SignalsPage.tsx'), 'utf8')
const appSource = readFileSync(resolve(root, '../src/App.tsx'), 'utf8')
const fallbackSource = readFileSync(resolve(root, '../public/404.html'), 'utf8')
const indexSource = readFileSync(resolve(root, '../index.html'), 'utf8')

function assertNoInventedPunctuation(text: string, label: string) {
  assert.equal(text.includes(';'), false, `${label} contains a semicolon`)
  assert.equal(text.includes('—'), false, `${label} contains an em dash`)
  assert.equal(text.includes('–'), false, `${label} contains an en dash`)
  assert.equal(text.includes(', and '), false, `${label} contains an Oxford comma`)
}

assert.equal(parseArticleDate(''), null)
assert.equal(parseArticleDate('October 2026'), null)
assert.equal(parseArticleDate('2026'), null)
assert.equal(parseArticleDate('October 25-26, 2026'), null)
assert.equal(parseArticleDate('2026-02-31'), null)
assert.equal(parseArticleDate('31 February 2026'), null)
assert.equal(parseArticleDate('October 25, 2026'), '2026-10-25')
assert.equal(parseArticleDate('2026-08-28'), '2026-08-28')
assert.equal(parseArticleDate('8 October 2026'), '2026-10-08')
assert.equal(shiftIsoDate('2026-11-28', -3), '2026-08-28')
assert.equal(shiftIsoDate('2026-03-31', -1), '2026-02-28')
assert.equal(recordedMarketLabel('United States — California,United States — New York'), 'United States - California, United States - New York')

const model = buildSignalPage(payload.signals, payload.as_of)
assert.equal(payload.as_of, '2026-11-28')
assert.equal(model.asOf, '2026-11-28')
assert.equal(model.windowStart, '2026-08-28')
assert.equal(model.signalCount, 218)
assert.equal(model.recentCount, 80)
assert.equal(model.earlierCount, 138)
assert.equal(model.undatedCount, 0)
assert.equal(model.afterCount, 0)
assert.equal(model.countries.length, 38)
assert.equal(model.countriesWithRecent, 25)
assert.equal(model.summaryOnlyCountries, 13)
assert.ok(model.unassigned)
assert.equal(model.unassigned.recent.length, 16)
assert.equal(model.unassigned.earlier.length, 28)
assert.equal(model.unassigned.undated.length, 0)

const byTitle = new Map(model.countries.map((section) => [section.title, section]))
const recentTitles = model.countries.filter((section) => section.recent.length > 0).map((section) => section.title)
const summaryTitles = model.countries.filter((section) => section.recent.length === 0 && section.earlier.length > 0).map((section) => section.title)
assert.deepEqual(recentTitles, [
  'Australia',
  'Austria',
  'Brazil',
  'Cambodia',
  'Canada',
  'China',
  'European Union',
  'France',
  'Gabon (not in the original 147-market registry)',
  'Georgia',
  'Greece',
  'Indonesia',
  'Iran',
  'Italy',
  'Japan',
  'Mexico',
  'Norway',
  'Philippines',
  'Poland',
  'Romania',
  'Russia',
  'Singapore',
  'Spain',
  'United Kingdom',
  'United States',
])
assert.deepEqual(summaryTitles, [
  'Bangladesh',
  'Denmark',
  'Germany',
  'Hong Kong',
  'India',
  'Ireland',
  'Malaysia',
  'New Zealand',
  'Pakistan',
  'Slovenia',
  'South Korea',
  'Thailand',
  'Türkiye',
])

assert.equal(byTitle.get('United States')?.recent.length, 24)
assert.equal(byTitle.get('United States')?.earlier.length, 24)
assert.equal(byTitle.get('United Kingdom')?.recent.length, 10)
assert.equal(byTitle.get('India')?.recent.length, 0)
assert.equal(byTitle.get('India')?.earlier.length, 5)
assert.equal(byTitle.get('Australia')?.recent.length, 5)
assert.equal(byTitle.get('Australia')?.earlier.length, 6)

const placedIds = new Set<string>()
for (const section of model.countries) {
  const ids = new Set<string>()
  for (const item of [...section.recent, ...section.earlier, ...section.undated, ...section.afterAsOf]) {
    assert.equal(ids.has(item.signal.id), false, `${section.title} repeats ${item.signal.id}`)
    ids.add(item.signal.id)
    placedIds.add(item.signal.id)
  }
  for (const item of section.recent) {
    assert.ok(item.articleIso)
    assert.ok(item.articleIso >= model.windowStart && item.articleIso <= model.asOf)
  }
  for (const item of section.earlier) {
    assert.ok(item.articleIso)
    assert.ok(item.articleIso < model.windowStart)
  }
  assertNoInventedPunctuation(section.earlierSummary, section.title)
  for (const item of section.earlier) {
    const extract = item.signal.evidence_extract.trim()
    if (extract.length >= 40) assert.equal(section.earlierSummary.includes(extract.slice(0, 40)), false)
  }
}

assert.equal(byTitle.get('India')?.earlierSummary, '5 earlier signals are on file. None of them records a focus.')
assert.equal(byTitle.get('Denmark')?.earlierSummary, '1 earlier signal is on file. The recorded focus is AI safety or frontier AI.')
assert.equal(
  byTitle.get('Türkiye')?.earlierSummary,
  '1 earlier signal is on file. The recorded focus is under-16 social media ban / age restriction.',
)
assert.equal(
  byTitle.get('Hong Kong')?.earlierSummary,
  '1 earlier signal is on file. It names more than one market. It does not record a focus.',
)

assert.equal(byTitle.get('Gabon (not in the original 147-market registry)')?.recent.some((item) => item.signal.id === 'signal-001'), true)
assert.equal(byTitle.get('Australia')?.recent.some((item) => item.signal.id === 'signal-003'), true)
assert.equal(byTitle.get('Australia')?.earlier.some((item) => item.signal.id === 'signal-004'), true)
assert.equal(byTitle.get('Australia')?.recent.some((item) => item.signal.id === 'signal-004'), false)

for (const title of ['China', 'Iran', 'Russia', 'United States']) {
  assert.equal(byTitle.get(title)?.recent.some((item) => item.signal.id === 'signal-139'), true, title)
}
const usWarner = byTitle.get('United States')?.recent.find((item) => item.signal.id === 'signal-139')
assert.equal(usWarner?.joint, true)

const ellison = [...(byTitle.get('United States')?.recent ?? []), ...(byTitle.get('United States')?.earlier ?? [])]
  .filter((item) => item.signal.id === 'signal-175')
assert.equal(ellison.length, 1)
assert.deepEqual(ellison[0]?.states, ['Minnesota'])

assert.equal(model.unassigned.recent.some((item) => item.signal.id === 'signal-092') || model.unassigned.earlier.some((item) => item.signal.id === 'signal-092'), true)
for (const section of model.countries) {
  assert.equal(section.recent.some((item) => item.signal.id === 'signal-092'), false)
  assert.equal(section.earlier.some((item) => item.signal.id === 'signal-092'), false)
}

const undated = buildSignalPage([
  {
    id: 'blank-date',
    market_name: 'Norway',
    article_date: '',
    issue_or_focus: '',
    issue_clusters: ['Not recorded'],
    evidence_extract: 'A quotation that must stay closed.',
  },
  {
    id: 'month-only',
    market_name: 'Norway',
    article_date: 'October 2026',
    issue_or_focus: 'age restriction',
    issue_clusters: ['age restriction'],
    evidence_extract: 'Month only is not a calendar day.',
  },
  {
    id: 'boundary',
    market_name: 'Norway',
    article_date: 'August 28, 2026',
    issue_or_focus: '',
    issue_clusters: ['Not recorded'],
    evidence_extract: 'On the window start.',
  },
  {
    id: 'day-before',
    market_name: 'Norway',
    article_date: 'August 27, 2026',
    issue_or_focus: '',
    issue_clusters: ['Not recorded'],
    evidence_extract: 'The day before the window.',
  },
  {
    id: 'after',
    market_name: 'Norway',
    article_date: 'November 29, 2026',
    issue_or_focus: '',
    issue_clusters: ['Not recorded'],
    evidence_extract: 'After the as-of date.',
  },
], '2026-11-28')
const norway = undated.countries.find((section) => section.title === 'Norway')
assert.ok(norway)
assert.deepEqual(norway.recent.map((item) => item.signal.id), ['boundary'])
assert.deepEqual(norway.earlier.map((item) => item.signal.id), ['day-before'])
assert.deepEqual(norway.undated.map((item) => item.signal.id), ['blank-date', 'month-only'])
assert.deepEqual(norway.afterAsOf.map((item) => item.signal.id), ['after'])
assert.equal(norway.earlierSummary.includes('A quotation'), false)
assert.equal(norway.earlierSummary.includes('The day before'), false)
assert.equal(undated.undatedCount, 2)
assert.equal(undated.afterCount, 1)

const reportDated = buildSignalPage([
  {
    id: 'report-only',
    market_name: 'Ireland',
    article_date: '',
    issue_or_focus: '',
    issue_clusters: ['Not recorded'],
    evidence_extract: 'Report date must not place this in the window.',
    report_date: '2026-11-01',
  } as DatedSignal & { report_date: string },
], '2026-11-28')
assert.equal(reportDated.recentCount, 0)
assert.equal(reportDated.undatedCount, 1)
assert.equal(reportDated.countries[0]?.recent.length, 0)
assert.equal(reportDated.countries[0]?.undated.length, 1)

assert.equal(earlierSummary([]), '')
assert.equal(pageSource.includes('—'), false)
assert.equal(pageSource.includes('–'), false)
assert.equal(pageSource.includes('section.earlier.map'), false)
assert.equal(pageSource.includes('earlier.map'), false)
assert.match(pageSource, /signalsAsOf/)
assert.match(pageSource, /buildSignalPage/)
assert.match(appSource, /BrowserRouter/)
assert.equal(appSource.includes('HashRouter'), false)
assert.match(fallbackSource, /pathSegmentsToKeep = 1/)
assert.match(indexSource, /search\[1\] !== '\/'/)
assert.equal(placedIds.has('signal-092'), false)

console.log(JSON.stringify({
  asOf: model.asOf,
  windowStart: model.windowStart,
  signals: model.signalCount,
  recentSignals: model.recentCount,
  earlierSignals: model.earlierCount,
  undatedSignals: model.undatedCount,
  afterAsOfSignals: model.afterCount,
  countries: model.countries.length,
  countriesWithRecent: model.countriesWithRecent,
  summaryOnlyCountries: model.summaryOnlyCountries,
  unassigned: model.unassigned.recent.length + model.unassigned.earlier.length,
  unassignedRecent: model.unassigned.recent.length,
  unassignedEarlier: model.unassigned.earlier.length,
}, null, 2))
