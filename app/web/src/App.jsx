import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Visualization from './components/Visualization'
import ChatPanel from './components/ChatPanel'
import { askBot } from './api'

const WELCOME =
  'Hi! I can find people in Salesforce. Try “find a Director”, “find a Manager”, or search by name, company, or email.'

// Bump the suffix if the persisted shape ever changes incompatibly.
const STORAGE_KEY = 'rikai.chats.v1'

let seq = 0
function newConversation() {
  seq += 1
  return {
    id: `chat-${Date.now()}-${seq}`,
    title: 'New chat',
    messages: [{ role: 'bot', text: WELCOME }],
    results: [],
    selectedPerson: null,
    loading: false,
    vizError: null,
    hasSearched: false,
    lastQuery: '',
  }
}

// Restore saved chats (with each chat's visualization) from a previous session.
// Returns null when there's nothing valid to restore.
function loadPersisted() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
    if (!saved || !Array.isArray(saved.conversations) || saved.conversations.length === 0) {
      return null
    }
    // A tab could have been closed mid-search — never restore a stuck spinner.
    const conversations = saved.conversations.map((c) => ({ ...c, loading: false }))
    const activeId = conversations.some((c) => c.id === saved.activeId)
      ? saved.activeId
      : conversations[0].id
    return { conversations, activeId }
  } catch {
    return null
  }
}

export default function App() {
  // Compute the initial state once (restore, or start a single fresh chat).
  const [seed] = useState(() => {
    const restored = loadPersisted()
    if (restored) return restored
    const c = newConversation()
    return { conversations: [c], activeId: c.id }
  })
  const [conversations, setConversations] = useState(seed.conversations)
  const [activeId, setActiveId] = useState(seed.activeId)

  // Persist chats + their visualizations so they reload across refreshes.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ conversations, activeId }))
    } catch {
      // Best-effort: ignore quota / serialization errors.
    }
  }, [conversations, activeId])

  const active = conversations.find((c) => c.id === activeId) || conversations[0]

  // Merge a patch (object or updater fn) into the conversation with the given id.
  function patchConversation(id, patch) {
    setConversations((prev) =>
      prev.map((c) =>
        c.id === id ? { ...c, ...(typeof patch === 'function' ? patch(c) : patch) } : c
      )
    )
  }

  function handleNewChat() {
    const c = newConversation()
    setConversations((prev) => [c, ...prev])
    setActiveId(c.id)
  }

  async function handleSend(question) {
    const q = (question || '').trim()
    if (!q || active.loading) return

    const id = activeId
    patchConversation(id, (c) => ({
      messages: [...c.messages, { role: 'user', text: q }],
      loading: true,
      vizError: null,
      selectedPerson: null,
      lastQuery: q,
      // Name the chat after its first question.
      title: c.title === 'New chat' ? q : c.title,
    }))

    try {
      const { answer, people } = await askBot(q)
      patchConversation(id, (c) => ({
        results: people,
        hasSearched: true,
        loading: false,
        messages: [...c.messages, { role: 'bot', text: answer }],
      }))
    } catch (e) {
      patchConversation(id, (c) => ({
        results: [],
        hasSearched: true,
        loading: false,
        vizError: e.message,
        messages: [...c.messages, { role: 'bot', text: e.message, error: true }],
      }))
    }
  }

  return (
    <div className="app">
      <Sidebar
        activeSource="salesforce"
        conversations={conversations}
        activeId={activeId}
        onNewChat={handleNewChat}
        onSelectChat={setActiveId}
      />
      <Visualization
        loading={active.loading}
        error={active.vizError}
        results={active.results}
        hasSearched={active.hasSearched}
        query={active.lastQuery}
        selectedPerson={active.selectedPerson}
        onSelect={(p) => patchConversation(activeId, { selectedPerson: p })}
        onBack={() => patchConversation(activeId, { selectedPerson: null })}
      />
      <ChatPanel
        key={activeId}
        messages={active.messages}
        loading={active.loading}
        onSend={handleSend}
      />
    </div>
  )
}
