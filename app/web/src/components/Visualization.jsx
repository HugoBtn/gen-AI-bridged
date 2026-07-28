import { LoaderCircle, TriangleAlert, SearchX, Search, BookOpen } from 'lucide-react'
import PersonCard from './PersonCard'
import PersonDetail from './PersonDetail'
import SearchGuide from './SearchGuide'

function subtitle({ selectedPerson, hasSearched, loading, error, results, query, guideVisible }) {
  if (guideVisible) return 'Search options and examples'
  if (selectedPerson) return 'Person details'
  if (hasSearched && !loading && !error) {
    const n = results.length
    return `${n} match${n === 1 ? '' : 'es'}${query ? ` for “${query}”` : ''}`
  }
  return 'Salesforce · people search'
}

export default function Visualization(props) {
  const {
    loading,
    error,
    results,
    hasSearched,
    selectedPerson,
    onSelect,
    onBack,
    guideVisible,
    onToggleGuide,
    onExample,
  } = props

  return (
    <main className="viz">
      <header className="viz__header">
        <div className="viz__heading">
          <h1 className="viz__title">{guideVisible ? 'Search options' : 'Results'}</h1>
          <p className="viz__subtitle">{subtitle(props)}</p>
        </div>
        <button
          type="button"
          className={'viz__tips' + (guideVisible ? ' viz__tips--active' : '')}
          onClick={onToggleGuide}
          aria-pressed={guideVisible}
        >
          <BookOpen size={15} />
          <span>{guideVisible ? 'Hide tips' : 'Search tips'}</span>
        </button>
      </header>

      <div className="viz__body">
        {loading ? (
          <div className="state">
            <LoaderCircle className="spin" size={30} />
            <p className="state__title">Searching Salesforce…</p>
            <p className="state__hint">Looking up contacts and leads.</p>
          </div>
        ) : error ? (
          <div className="state">
            <TriangleAlert size={30} className="state__icon state__icon--warn" />
            <p className="state__title">Couldn't load results</p>
            <p className="state__hint">{error}</p>
          </div>
        ) : selectedPerson ? (
          <PersonDetail person={selectedPerson} onBack={onBack} />
        ) : guideVisible ? (
          <SearchGuide onExample={onExample} />
        ) : results.length > 0 ? (
          <div className="cards">
            {results.map((p) => (
              <PersonCard key={`${p.type}-${p.id}`} person={p} onClick={() => onSelect(p)} />
            ))}
          </div>
        ) : hasSearched ? (
          <div className="state">
            <SearchX size={30} className="state__icon" />
            <p className="state__title">No people found</p>
            <p className="state__hint">
              Try a shorter or different search term — “Search tips” lists every option.
            </p>
          </div>
        ) : (
          <div className="state">
            <Search size={30} className="state__icon" />
            <p className="state__title">Search for someone to get started</p>
            <p className="state__hint">
              Use the chat on the right — e.g. “find a Director” or “find a Manager”.
            </p>
          </div>
        )}
      </div>
    </main>
  )
}
