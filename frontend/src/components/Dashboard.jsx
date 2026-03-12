/**
 * Dashboard – placeholder charts using Recharts.
 * TODO: Replace static data with real API calls to /forecast and warehouse views.
 */

import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

const MOCK_DATA = Array.from({ length: 12 }, (_, i) => ({
  month: `2024-${String(i + 1).padStart(2, '0')}`,
  actual: Math.round(5000 + Math.random() * 3000),
  forecast: Math.round(5200 + Math.random() * 2800),
}))

export default function Dashboard() {
  return (
    <div>
      <h3>Sales Overview (mock data)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={MOCK_DATA}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#8884d8" name="Actual Sales" />
          <Line type="monotone" dataKey="forecast" stroke="#82ca9d" name="Forecast" strokeDasharray="5 5" />
        </LineChart>
      </ResponsiveContainer>
      <p style={{ color: '#888', fontSize: 12 }}>
        TODO: Fetch real data from <code>GET /api/forecast/latest</code> and warehouse views.
      </p>
    </div>
  )
}
