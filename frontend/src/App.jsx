import React, { useState } from 'react'
import Login from './components/Login'
import Upload from './components/Upload'
import Dashboard from './components/Dashboard'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('access_token'))

  function handleLogout() {
    localStorage.removeItem('access_token')
    setToken(null)
  }

  if (!token) {
    return (
      <main style={{ maxWidth: 480, margin: '80px auto', fontFamily: 'sans-serif' }}>
        <Login onLogin={setToken} />
      </main>
    )
  }

  return (
    <main style={{ maxWidth: 900, margin: '32px auto', fontFamily: 'sans-serif', padding: '0 16px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>IntelliStore 📊</h1>
        <button onClick={handleLogout}>Sign out</button>
      </header>
      <Upload token={token} />
      <hr />
      <Dashboard />
    </main>
  )
}
