import { SEARCH_RECIPES } from '../searchGuide'

// Cheat-sheet of every search the assistant understands. Examples are runnable
// (click = ask it); patterns need a value from your org, so they stay read-only.
export default function SearchGuide({ onExample }) {
  return (
    <div className="guide">
      <div className="guide__intro">
        <h2 className="guide__title">How to search</h2>
        <p className="guide__hint">
          Ask in plain English in the chat on the right — or click any example below to run it.
        </p>
      </div>

      <div className="guide__grid">
        {SEARCH_RECIPES.map((r) => {
          const Icon = r.icon
          return (
            <section key={r.id} className="guide__card">
              <div className="guide__card-head">
                <span className="guide__icon">
                  <Icon size={16} />
                </span>
                <h3 className="guide__card-title">{r.label}</h3>
              </div>
              <p className="guide__card-hint">{r.hint}</p>

              <div className="guide__patterns">
                {r.patterns.map((p) => (
                  <code key={p} className="guide__pattern">
                    {p}
                  </code>
                ))}
              </div>

              {r.examples.length > 0 && (
                <div className="guide__examples">
                  {r.examples.map((ex) => (
                    <button
                      key={ex}
                      type="button"
                      className="chip chip--example"
                      onClick={() => onExample(ex)}
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              )}
            </section>
          )
        })}
      </div>

      <p className="guide__note">
        Filters combine with AND and match a case-insensitive “contains”. Up to 25 people are
        returned per search.
      </p>
    </div>
  )
}
