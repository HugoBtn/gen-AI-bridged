import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Visualization from './components/Visualization'
import ChatPanel from './components/ChatPanel'
import { askBot } from './api'

const WELCOME =
  'Hi! I can find people in Salesforce. Try “find a Director”, “find a Manager”, or search by name, company, or email.'

export default function App() {
  const [messages, setMessages] = useState([{ role: 'bot', text: WELCOME }])
  const [results, setResults] = useState([])
  const [selectedPerson, setSelectedPerson] = useState(null)
  const [loading, setLoading] = useState(false)
  const [vizError, setVizError] = useState(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [lastQuery, setLastQuery] = useState('')

  async function handleSend(question) {
    const q = (question || '').trim()
    if (!q || loading) return

    setMessages((prev) => [...prev, { role: 'user', text: q }])
    setLoading(true)
    setVizError(null)
    setSelectedPerson(null)
    setLastQuery(q)

    try {
      const { answer, people } = await askBot(q)
      setResults(people)
      setHasSearched(true)
      setMessages((prev) => [...prev, { role: 'bot', text: answer }])
    } catch (e) {
      setResults([])
      setHasSearched(true)
      setVizError(e.message)
      setMessages((prev) => [...prev, { role: 'bot', text: e.message, error: true }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <Sidebar activeSource="salesforce" />
      <Visualization
        loading={loading}
        error={vizError}
        results={results}
        hasSearched={hasSearched}
        query={lastQuery}
        selectedPerson={selectedPerson}
        onSelect={setSelectedPerson}
        onBack={() => setSelectedPerson(null)}
      />
      <ChatPanel messages={messages} loading={loading} onSend={handleSend} />
    </div>
  )
}
