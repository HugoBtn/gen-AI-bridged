import { useState, useEffect } from 'react'
import {
  Cloud,
  IdCard,
  Users,
  FolderKanban,
  Plus,
  MessageSquare,
  ChevronDown,
} from 'lucide-react'

const SOURCES = [
  { id: 'salesforce', name: 'Salesforce', icon: Cloud, status: 'connected' },
  { id: 'sansan', name: 'Sansan', icon: IdCard, status: 'soon' },
  { id: 'hr', name: 'HR', icon: Users, status: 'soon' },
  { id: 'pm', name: 'PM', icon: FolderKanban, status: 'soon' },
]

// Which sections the user has folded away. Bump the suffix if the shape changes.
const STORAGE_KEY = 'rikai.sidebar.v1'

function loadCollapsed() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return { sources: !!saved?.sources, chats: !!saved?.chats }
  } catch {
    return { sources: false, chats: false }
  }
}

// Clickable section header: folds its section away and, when folded, shows how
// many items are hidden underneath.
function SectionHead({ label, collapsed, onToggle, count, action }) {
  return (
    <div className="sidebar__section-head">
      <button
        type="button"
        className="sidebar__section-toggle"
        onClick={onToggle}
        aria-expanded={!collapsed}
        title={`${collapsed ? 'Show' : 'Hide'} ${label.toLowerCase()}`}
      >
        <ChevronDown
          size={13}
          className={'sidebar__chevron' + (collapsed ? ' sidebar__chevron--collapsed' : '')}
        />
        <span className="sidebar__section-name">{label}</span>
        {collapsed && count > 0 && <span className="sidebar__count">{count}</span>}
      </button>
      {action}
    </div>
  )
}

export default function Sidebar({
  activeSource,
  conversations = [],
  activeId,
  onNewChat,
  onSelectChat,
}) {
  const [collapsed, setCollapsed] = useState(loadCollapsed)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(collapsed))
    } catch {
      // Best-effort: ignore quota / serialization errors.
    }
  }, [collapsed])

  function toggle(key) {
    setCollapsed((c) => ({ ...c, [key]: !c[key] }))
  }

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
        <SectionHead
          label="Data sources"
          collapsed={collapsed.sources}
          onToggle={() => toggle('sources')}
          count={SOURCES.length}
        />
        {!collapsed.sources &&
          SOURCES.map((s) => {
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

      <div
        className={
          'sidebar__section sidebar__chats' +
          (collapsed.chats ? ' sidebar__chats--collapsed' : '')
        }
      >
        <SectionHead
          label="Chats"
          collapsed={collapsed.chats}
          onToggle={() => toggle('chats')}
          count={conversations.length}
          // Folding the list away shouldn't cost you the ability to start a chat.
          action={
            collapsed.chats && (
              <button
                type="button"
                className="sidebar__icon-btn"
                onClick={onNewChat}
                title="New chat"
                aria-label="New chat"
              >
                <Plus size={14} />
              </button>
            )
          }
        />
        {!collapsed.chats && (
          <>
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
          </>
        )}
      </div>

      <div className="sidebar__footer">Proof of concept</div>
    </aside>
  )
}
