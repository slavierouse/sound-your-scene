import { useState, useEffect } from 'react'
import Plot from 'react-plotly.js'
import VolumeMetrics from './VolumeMetrics'
import { APP_CONFIG } from '../config/constants'

function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${APP_CONFIG.API_BASE_URL}/stats`)
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data')
      }
      const dashboardData = await response.json()
      setData(dashboardData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-red-600">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Performance Metrics Dashboard</h1>
          <p className="text-gray-600">Analytics for Sound Your Scene search performance and user engagement</p>
        </div>

        {/* Volume Metrics */}
        <VolumeMetrics metrics={data?.volume_metrics} />

        {/* Performance Charts Row */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Core Performance Metrics</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* HR@K Chart */}
            <div className="bg-white p-4 rounded-lg shadow">
              <Plot
                data={[
                  {
                    x: data?.performance_charts?.hr_at_k?.map(d => d.k) || [],
                    y: data?.performance_charts?.hr_at_k?.map(d => d.hr_at_k) || [],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'HR@K',
                    line: { color: '#2563eb' }
                  }
                ]}
                layout={{
                  title: 'Hit Rate @ K',
                  xaxis: { title: 'K (Position)' },
                  yaxis: { title: 'Hit Rate', range: [0, 1] },
                  showlegend: false,
                  margin: { t: 50, r: 50, b: 50, l: 50 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '300px' }}
              />
            </div>

            {/* Latency CDF Chart */}
            <div className="bg-white p-4 rounded-lg shadow">
              <Plot
                data={[
                  {
                    x: data?.performance_charts?.latency_cdf?.map(d => d.latency_seconds) || [],
                    y: data?.performance_charts?.latency_cdf?.map(d => d.percentile) || [],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Latency CDF',
                    line: { color: '#dc2626' }
                  }
                ]}
                layout={{
                  title: 'Latency Distribution (CDF)',
                  xaxis: { title: 'Latency (seconds)' },
                  yaxis: { title: 'Percentile', range: [0, 1] },
                  showlegend: false,
                  margin: { t: 50, r: 50, b: 50, l: 50 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '300px' }}
              />
            </div>
          </div>
        </div>

        {/* Segmented Analysis */}
        <div className="space-y-8">
          {/* HR@K by Conversation Turn */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hit Rate by Conversation Turn</h3>
            <Plot
              data={Object.entries(data?.segmented_charts?.by_conversation_turn || {}).map(([turn, turnData], index) => ({
                x: turnData.map(d => d.k),
                y: turnData.map(d => d.hr_at_k),
                type: 'scatter',
                mode: 'lines+markers',
                name: turn,
                line: { color: `hsl(${index * 60}, 70%, 50%)` }
              }))}
              layout={{
                title: 'HR@K by Conversation Turn',
                xaxis: { title: 'K (Position)' },
                yaxis: { title: 'Hit Rate', range: [0, 1] },
                margin: { t: 50, r: 50, b: 50, l: 50 }
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%', height: '400px' }}
            />
          </div>

          {/* HR@K by Model */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hit Rate by Model</h3>
            <Plot
              data={Object.entries(data?.segmented_charts?.by_model || {}).map(([model, modelData], index) => ({
                x: modelData.map(d => d.k),
                y: modelData.map(d => d.hr_at_k),
                type: 'scatter',
                mode: 'lines+markers',
                name: model,
                line: { color: `hsl(${index * 120}, 70%, 50%)` }
              }))}
              layout={{
                title: 'HR@K by Model',
                xaxis: { title: 'K (Position)' },
                yaxis: { title: 'Hit Rate', range: [0, 1] },
                margin: { t: 50, r: 50, b: 50, l: 50 }
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%', height: '400px' }}
            />
          </div>

          {/* HR@K by Hit Component */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hit Rate by Component Type</h3>
            <Plot
              data={Object.entries(data?.segmented_charts?.by_hit_component || {}).map(([component, componentData], index) => ({
                x: componentData.map(d => d.k),
                y: componentData.map(d => d.hr_at_k),
                type: 'scatter',
                mode: 'lines+markers',
                name: component.replace('_', ' '),
                line: { color: `hsl(${index * 90}, 70%, 50%)` }
              }))}
              layout={{
                title: 'HR@K by Hit Component',
                xaxis: { title: 'K (Position)' },
                yaxis: { title: 'Hit Rate', range: [0, 1] },
                margin: { t: 50, r: 50, b: 50, l: 50 }
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%', height: '400px' }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard