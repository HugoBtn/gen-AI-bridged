// Single entry point for talking to the backend. Goes through the Vite proxy
// (/api -> http://127.0.0.1:8000), so this stays same-origin in the browser.
export async function askBot(question) {
  let res
  try {
    res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
  } catch {
    throw new Error("Can't reach the backend. Is the Python server running on port 8000?")
  }

  let data = {}
  try {
    data = await res.json()
  } catch {
    // non-JSON response — leave data empty and fall through to the error below
  }

  if (!res.ok) {
    throw new Error(data.error || data.answer || `Server error (${res.status}).`)
  }

  return {
    answer: data.answer || '',
    people: Array.isArray(data.people) ? data.people : [],
    count: data.count ?? (Array.isArray(data.people) ? data.people.length : 0),
    error: data.error || null,
  }
}
