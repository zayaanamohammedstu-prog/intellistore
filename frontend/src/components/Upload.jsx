/**
 * Upload component – POST a CSV/Excel file to the API and poll job status.
 */

import React, { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export default function Upload({ token }) {
  const [file, setFile] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return

    setError(null)
    setJobId(null)
    setStatus(null)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/uploads/`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      })

      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Upload failed')
        return
      }

      const data = await res.json()
      setJobId(data.job_id)
      setStatus(data.status)
      pollStatus(data.job_id)
    } catch (err) {
      setError(String(err))
    }
  }

  function pollStatus(id) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/uploads/${id}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!res.ok) {
          clearInterval(interval)
          return
        }
        const data = await res.json()
        setStatus(data.status)
        if (['completed', 'failed'].includes(data.status)) {
          clearInterval(interval)
        }
      } catch {
        clearInterval(interval)
      }
    }, 2000)
  }

  return (
    <div>
      <h3>Upload Sales Data</h3>
      <form onSubmit={handleUpload}>
        <input
          type="file"
          accept=".csv,.xls,.xlsx"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button type="submit" disabled={!file}>
          Upload &amp; Process
        </button>
      </form>
      {jobId && <p>Job ID: <code>{jobId}</code> — Status: <strong>{status}</strong></p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
    </div>
  )
}
