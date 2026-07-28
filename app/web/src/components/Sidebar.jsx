import { Cloud, IdCard, Users, FolderKanban, Plus, MessageSquare } from 'lucide-react'

const SOURCES = [
  { id: 'salesforce', name: 'Salesforce', icon: Cloud, status: 'connected' },
  { id: 'sansan', name: 'Sansan', icon: IdCard, status: 'soon' },
  { id: 'hr', name: 'HR', icon: Users, status: 'soon' },
  { id: 'pm', name: 'PM', icon: FolderKanban, status: 'soon' },
]

export default function Sidebar({
  activeSource,
  conversations = [],
  activeId,
  onNewChat,
  onSelectChat,
}) {
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

      <div className="sidebar__section sidebar__chats">
        <div className="sidebar__section-label">Chats</div>
        <button type="button" className="new-chat" onClick={onNewChat}>
          <Plus size={16} />
          <span>New chat</span>
        </button>
        <div className="chat-list">
          {conversations.map((c) => (
            <button
              key={c.id}
              type="button"
              className={'chat-item' + (c.id === activeId ? ' chat-item--active' : '')}
              onClick={() => onSelectChat(c.id)}
              title={c.title}
            >
              <MessageSquare size={16} className="chat-item__icon" />
              <span className="chat-item__title">{c.title}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar__footer">Proof of concept</div>
    </aside>
  )
}
