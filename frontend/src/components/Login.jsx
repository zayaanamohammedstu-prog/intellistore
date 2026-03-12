/**
 * Login component – Google OAuth via Google Identity Services SDK.
 *
 * Flow
 * ----
 * 1. User clicks "Sign in with Google".
 * 2. Google pops up the consent screen and returns an ID token (credential).
 * 3. We POST the ID token to the API /auth/google endpoint.
 * 4. API verifies the token, upserts the user, and returns an app JWT.
 * 5. JWT is stored in localStorage and sent in subsequent API requests.
 *
 * TODO (production)
 * -----------------
 * - Store JWT in an httpOnly cookie instead of localStorage.
 * - Handle token expiry / refresh.
 */

import React, { useEffect } from 'react'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export default function Login({ onLogin }) {
  useEffect(() => {
    if (!window.google) return

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleCredentialResponse,
    })

    window.google.accounts.id.renderButton(
      document.getElementById('google-signin-btn'),
      { theme: 'outline', size: 'large', text: 'sign_in_with' }
    )
  }, [])

  async function handleCredentialResponse(response) {
    try {
      const res = await fetch(`${API_BASE}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      })

      if (!res.ok) {
        const err = await res.json()
        alert(`Login failed: ${err.detail}`)
        return
      }

      const data = await res.json()
      localStorage.setItem('access_token', data.access_token)
      onLogin(data.access_token)
    } catch (err) {
      console.error('Login error:', err)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
      <h2>Welcome to IntelliStore</h2>
      <p>Sign in to access your sales dashboard and forecasts.</p>
      <div id="google-signin-btn" />
      {!GOOGLE_CLIENT_ID && (
        <p style={{ color: 'orange', fontSize: 12 }}>
          ⚠ VITE_GOOGLE_CLIENT_ID not set – Google Sign-In button will not render.
        </p>
      )}
    </div>
  )
}
