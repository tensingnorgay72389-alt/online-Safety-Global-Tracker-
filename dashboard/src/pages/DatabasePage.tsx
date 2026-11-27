import FilterBar from '../components/database/FilterBar'
import MarketTable from '../components/database/MarketTable'
import { useFilters } from '../context/FilterContext'

export default function DatabasePage() {
  const { scope, setScope } = useFilters()

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Market Database</h2>
          <p className="text-sm text-slate-500 max-w-3xl">
            Search and filter regulatory severity, China sentiment, status, service scope and key obligations.
            Open a row for the assessment. Edits made under Edit Scores &amp; Wording appear here immediately.
          </p>
        </div>
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
          <button
            type="button"
            onClick={() => setScope('moderate_plus')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium ${
              scope === 'moderate_plus' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            Moderate and above
          </button>
          <button
            type="button"
            onClick={() => setScope('all')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium ${
              scope === 'all' ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            All 158 markets
          </button>
        </div>
      </div>
      <FilterBar />
      <MarketTable />
    </div>
  )
}
