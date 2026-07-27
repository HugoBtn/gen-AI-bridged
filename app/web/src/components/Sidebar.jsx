import { Cloud, IdCard, Users, FolderKanban } from 'lucide-react'

const SOURCES = [
  { id: 'salesforce', name: 'Salesforce', icon: Cloud, status: 'connected' },
  { id: 'sansan', name: 'Sansan', icon: IdCard, status: 'soon' },
  { id: 'hr', name: 'HR', icon: Users, status: 'soon' },
  { id: 'pm', name: 'PM', icon: FolderKanban, status: 'soon' },
]

export default function Sidebar({ activeSource }) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">R</div>
        <div>
          <div className="sidebar__title">RIKAI</div>
          <div className="sidebar__subtitle">Bridge AI</div>
        </div>
      </div>

      <div className="sidebar__section">
        <div className="sidebar__section-label">Data sources</div>
        {SOURCES.map((s) => {
          const Icon = s.icon
          const active = s.id === activeSource
          const disabled = s.status === 'soon'
          return (
            <div
              key={s.id}
              className={
                'source' +
                (active ? ' source--active' : '') +
                (disabled ? ' source--disabled' : '')
              }
              title={disabled ? 'Coming soon' : 'Connected'}
              aria-disabled={disabled}
            >
              <Icon size={18} className="source__icon" />
              <span className="source__name">{s.name}</span>
              {disabled ? (
                <span className="badge badge--soon">Soon</span>
              ) : (
                <span className="source__dot" title="Connected" />
              )}
            </div>
          )
        })}
      </div>

      <div className="sidebar__footer">Proof of concept</div>
    </aside>
  )
}
