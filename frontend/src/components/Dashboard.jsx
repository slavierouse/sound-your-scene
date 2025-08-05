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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* HR@K Chart */}
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Hit Rate @ K</h3>
              <p className="text-sm text-gray-600 mb-4">Fraction of searches where user found at least one hit in top K results</p>
              <Plot
                data={[
                  {
                    x: data?.performance_charts?.hr_at_k?.map(d => d.k) || [],
                    y: data?.performance_charts?.hr_at_k?.map(d => d.hr_at_k * 100) || [],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'HR@K',
                    line: { color: '#2563eb' },
                    hovertemplate: '<b>Position %{x}</b><br>Hit Rate: %{y:.1f}%<extra></extra>',
                    error_y: {
                      type: 'data',
                      array: data?.performance_charts?.hr_at_k?.map(d => (d.ci_upper - d.hr_at_k) * 100) || [],
                      arrayminus: data?.performance_charts?.hr_at_k?.map(d => (d.hr_at_k - d.ci_lower) * 100) || [],
                      visible: true,
                      color: 'rgba(37, 99, 235, 0.3)',
                      thickness: 1,
                      width: 2
                    }
                  }
                ]}
                layout={{
                  xaxis: { title: 'K (Position)' },
                  yaxis: { title: 'Hit Rate (%)', range: [0, 100] },
                  showlegend: false,
                  margin: { t: 10, r: 50, b: 50, l: 50 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '300px' }}
              />
            </div>

            {/* Latency CDF Chart */}
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Search Latency Distribution</h3>
              <p className="text-sm text-gray-600 mb-4">Cumulative distribution of search processing times</p>
              <Plot
                data={[
                  {
                    x: data?.performance_charts?.latency_cdf?.map(d => d.latency_seconds) || [],
                    y: data?.performance_charts?.latency_cdf?.map(d => d.percentile * 100) || [],
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Latency CDF',
                    line: { color: '#dc2626' }
                  }
                ]}
                layout={{
                  xaxis: { title: 'Latency (seconds)' },
                  yaxis: { title: 'Percentile (%)', range: [0, 100] },
                  showlegend: false,
                  margin: { t: 10, r: 50, b: 50, l: 50 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '300px' }}
              />
            </div>
          </div>

          {/* Recall and Precision Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recall@K Chart */}
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Recall @ K</h3>
              <p className="text-sm text-gray-600 mb-4">Fraction of relevant items retrieved in top K results</p>
              <Plot
                data={[
                  {
                    x: data?.performance_charts?.recall_at_k?.map(d => d.k) || [],
                    y: data?.performance_charts?.recall_at_k?.map(d => d.recall_at_k * 100) || [],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Recall@K',
                    line: { color: '#059669' },
                    hovertemplate: '<b>Position %{x}</b><br>Recall: %{y:.1f}%<extra></extra>',
                    error_y: {
                      type: 'data',
                      array: data?.performance_charts?.recall_at_k?.map(d => (d.ci_upper - d.recall_at_k) * 100) || [],
                      arrayminus: data?.performance_charts?.recall_at_k?.map(d => (d.recall_at_k - d.ci_lower) * 100) || [],
                      visible: true,
                      color: 'rgba(5, 150, 105, 0.3)',
                      thickness: 1,
                      width: 2
                    }
                  }
                ]}
                layout={{
                  xaxis: { title: 'K (Position)' },
                  yaxis: { title: 'Recall (%)', range: [0, 100] },
                  showlegend: false,
                  margin: { t: 10, r: 50, b: 50, l: 50 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '300px' }}
              />
            </div>

            {/* Precision@K Chart */}
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Precision @ K</h3>
              <p className="text-sm text-gray-600 mb-4">Fraction of retrieved items in top K that are relevant</p>
              <Plot
                data={[
                  {
                    x: data?.performance_charts?.precision_at_k?.map(d => d.k) || [],
                    y: data?.performance_charts?.precision_at_k?.map(d => d.precision_at_k * 100) || [],
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Precision@K',
                    line: { color: '#7c3aed' },
                    hovertemplate: '<b>Position %{x}</b><br>Precision: %{y:.1f}%<extra></extra>',
                    error_y: {
                      type: 'data',
                      array: data?.performance_charts?.precision_at_k?.map(d => (d.ci_upper - d.precision_at_k) * 100) || [],
                      arrayminus: data?.performance_charts?.precision_at_k?.map(d => (d.precision_at_k - d.ci_lower) * 100) || [],
                      visible: true,
                      color: 'rgba(124, 58, 237, 0.3)',
                      thickness: 1,
                      width: 2
                    }
                  }
                ]}
                layout={{
                  xaxis: { title: 'K (Position)' },
                  yaxis: { title: 'Precision (%)', range: [0, 100] },
                  showlegend: false,
                  margin: { t: 10, r: 50, b: 50, l: 50 }
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
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h4 className="text-md font-medium text-gray-700 mb-2">Hit Rate @ K</h4>
                <Plot
                  data={Object.entries(data?.segmented_charts?.by_conversation_turn?.hr_data || {}).map(([turn, turnData], index) => ({
                    x: turnData.map(d => d.k),
                    y: turnData.map(d => d.hr_at_k * 100),
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: turn,
                    line: { color: `hsl(${index * 60}, 70%, 50%)` },
                    error_y: {
                      type: 'data',
                      array: turnData.map(d => (d.ci_upper - d.hr_at_k) * 100),
                      arrayminus: turnData.map(d => (d.hr_at_k - d.ci_lower) * 100),
                      visible: true,
                      color: `hsla(${index * 60}, 70%, 50%, 0.3)`,
                      thickness: 1,
                      width: 2
                    }
                  }))}
                  layout={{
                    xaxis: { title: 'K (Position)' },
                    yaxis: { title: 'Hit Rate (%)', range: [0, 100] },
                    margin: { t: 10, r: 50, b: 50, l: 50 }
                  }}
                  config={{ displayModeBar: false }}
                  style={{ width: '100%', height: '350px' }}
                />
              </div>
              <div>
                <h4 className="text-md font-medium text-gray-700 mb-2">Latency Distribution</h4>
                <Plot
                  data={Object.entries(data?.segmented_charts?.by_conversation_turn?.latency_data || {}).map(([turn, turnData], index) => ({
                    x: turnData.map(d => d.latency_seconds),
                    y: turnData.map(d => d.percentile * 100),
                    type: 'scatter',
                    mode: 'lines',
                    name: turn,
                    line: { color: `hsl(${index * 60}, 70%, 50%)` }
                  }))}
                  layout={{
                    xaxis: { title: 'Latency (seconds)' },
                    yaxis: { title: 'Percentile (%)', range: [0, 100] },
                    margin: { t: 10, r: 50, b: 50, l: 50 }
                  }}
                  config={{ displayModeBar: false }}
                  style={{ width: '100%', height: '350px' }}
                />
              </div>
            </div>
          </div>

          {/* HR@K by Model */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hit Rate by Model</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h4 className="text-md font-medium text-gray-700 mb-2">Hit Rate @ K</h4>
                <Plot
                  data={Object.entries(data?.segmented_charts?.by_model?.hr_data || {}).map(([model, modelData], index) => ({
                    x: modelData.map(d => d.k),
                    y: modelData.map(d => d.hr_at_k * 100),
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: model,
                    line: { color: `hsl(${index * 120}, 70%, 50%)` },
                    error_y: {
                      type: 'data',
                      array: modelData.map(d => (d.ci_upper - d.hr_at_k) * 100),
                      arrayminus: modelData.map(d => (d.hr_at_k - d.ci_lower) * 100),
                      visible: true,
                      color: `hsla(${index * 120}, 70%, 50%, 0.3)`,
                      thickness: 1,
                      width: 2
                    }
                  }))}
                  layout={{
                    xaxis: { title: 'K (Position)' },
                    yaxis: { title: 'Hit Rate (%)', range: [0, 100] },
                    margin: { t: 10, r: 50, b: 50, l: 50 }
                  }}
                  config={{ displayModeBar: false }}
                  style={{ width: '100%', height: '350px' }}
                />
              </div>
              <div>
                <h4 className="text-md font-medium text-gray-700 mb-2">Latency Distribution</h4>
                <Plot
                  data={Object.entries(data?.segmented_charts?.by_model?.latency_data || {}).map(([model, modelData], index) => ({
                    x: modelData.map(d => d.latency_seconds),
                    y: modelData.map(d => d.percentile * 100),
                    type: 'scatter',
                    mode: 'lines',
                    name: model,
                    line: { color: `hsl(${index * 120}, 70%, 50%)` }
                  }))}
                  layout={{
                    xaxis: { title: 'Latency (seconds)' },
                    yaxis: { title: 'Percentile (%)', range: [0, 100] },
                    margin: { t: 10, r: 50, b: 50, l: 50 }
                  }}
                  config={{ displayModeBar: false }}
                  style={{ width: '100%', height: '350px' }}
                />
              </div>
            </div>
          </div>

          {/* HR@K by Hit Component */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hit Rate by Component Type</h3>
            <Plot
              data={Object.entries(data?.segmented_charts?.by_hit_component || {}).map(([component, componentData], index) => ({
                x: componentData.map(d => d.k),
                y: componentData.map(d => d.hr_at_k * 100),
                type: 'scatter',
                mode: 'lines+markers',
                name: component,
                line: { color: `hsl(${index * 90}, 70%, 50%)` },
                error_y: {
                  type: 'data',
                  array: componentData.map(d => (d.ci_upper - d.hr_at_k) * 100),
                  arrayminus: componentData.map(d => (d.hr_at_k - d.ci_lower) * 100),
                  visible: true,
                  color: `hsla(${index * 90}, 70%, 50%, 0.3)`,
                  thickness: 1,
                  width: 2
                }
              }))}
              layout={{
                xaxis: { title: 'K (Position)' },
                yaxis: { title: 'Hit Rate (%)', range: [0, 100] },
                margin: { t: 50, r: 50, b: 50, l: 50 }
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%', height: '400px' }}
            />
          </div>

          {/* HR@K by Image Presence */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Hit Rate by Image Presence</h3>
            <Plot
              data={Object.entries(data?.segmented_charts?.by_image_presence || {}).map(([imageType, imageData], index) => ({
                x: imageData.map(d => d.k),
                y: imageData.map(d => d.hr_at_k * 100),
                type: 'scatter',
                mode: 'lines+markers',
                name: imageType === 'with_image' ? 'With Image' : 'Without Image',
                line: { color: imageType === 'with_image' ? '#059669' : '#dc2626' },
                error_y: {
                  type: 'data',
                  array: imageData.map(d => (d.ci_upper - d.hr_at_k) * 100),
                  arrayminus: imageData.map(d => (d.hr_at_k - d.ci_lower) * 100),
                  visible: true,
                  color: imageType === 'with_image' ? 'rgba(5, 150, 105, 0.3)' : 'rgba(220, 38, 38, 0.3)',
                  thickness: 1,
                  width: 2
                }
              }))}
              layout={{
                xaxis: { title: 'K (Position)' },
                yaxis: { title: 'Hit Rate (%)', range: [0, 100] },
                margin: { t: 50, r: 50, b: 50, l: 50 }
              }}
              config={{ displayModeBar: false }}
              style={{ width: '100%', height: '400px' }}
            />
          </div>
        </div>

        {/* Analysis Tables */}
        <div className="space-y-8">
          {/* Genre Usage Analysis */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Genre Usage Analysis</h3>
            <p className="text-sm text-gray-600 mb-4">Breakdown of how genres are used in search filters (included, excluded, boosted)</p>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Genre</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Filter Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usage Count</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {(data?.analysis_tables?.genre_usage || []).map((row, index) => (
                    <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{row.genre}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${{
                          'included': 'bg-green-100 text-green-800',
                          'excluded': 'bg-red-100 text-red-800',
                          'boosted': 'bg-blue-100 text-blue-800'
                        }[row.filter_type] || 'bg-gray-100 text-gray-800'}`}>
                          {row.filter_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.usage_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Conversation Analysis */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Conversation Analysis</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h4 className="text-md font-medium text-gray-700 mb-2">Conversation Length Distribution by Model</h4>
                <Plot
                  data={[
                    {
                      x: data?.analysis_tables?.conversation_analysis?.turns_by_model?.map(d => d.turns) || [],
                      y: data?.analysis_tables?.conversation_analysis?.turns_by_model?.map(d => d.cumulative_percentage * 100) || [],
                      type: 'scatter',
                      mode: 'lines',
                      name: 'Conversation Turns CDF',
                      line: { color: '#7c3aed' }
                    }
                  ]}
                  layout={{
                    xaxis: { title: 'Number of Turns' },
                    yaxis: { title: 'Cumulative Percentage (%)', range: [0, 100] },
                    showlegend: false,
                    margin: { t: 10, r: 50, b: 50, l: 50 }
                  }}
                  config={{ displayModeBar: false }}
                  style={{ width: '100%', height: '300px' }}
                />
              </div>
              <div>
                <h4 className="text-md font-medium text-gray-700 mb-2">Average Result Count by Turn</h4>
                <Plot
                  data={[
                    {
                      x: data?.analysis_tables?.conversation_analysis?.result_count_by_turn?.map(d => d.turn) || [],
                      y: data?.analysis_tables?.conversation_analysis?.result_count_by_turn?.map(d => d.avg_result_count) || [],
                      type: 'scatter',
                      mode: 'lines+markers',
                      name: 'Avg Results',
                      line: { color: '#059669' },
                      error_y: {
                        type: 'data',
                        array: data?.analysis_tables?.conversation_analysis?.result_count_by_turn?.map(d => d.std_dev) || [],
                        visible: true,
                        color: 'rgba(5, 150, 105, 0.3)'
                      }
                    }
                  ]}
                  layout={{
                    xaxis: { title: 'Conversation Turn' },
                    yaxis: { title: 'Average Result Count' },
                    showlegend: false,
                    margin: { t: 10, r: 50, b: 50, l: 50 }
                  }}
                  config={{ displayModeBar: false }}
                  style={{ width: '100%', height: '300px' }}
                />
              </div>
            </div>
          </div>

          {/* Filters Analysis */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Filters Usage Analysis</h3>
            <p className="text-sm text-gray-600 mb-4">Most commonly used filters (excluding genres)</p>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Filter Field</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usage Count</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Value</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {(data?.analysis_tables?.filters_analysis || []).map((row, index) => (
                    <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{row.field}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${{
                          'min': 'bg-blue-100 text-blue-800',
                          'max': 'bg-purple-100 text-purple-800',
                          'other': 'bg-gray-100 text-gray-800'
                        }[row.filter_type] || 'bg-gray-100 text-gray-800'}`}>
                          {row.filter_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.usage_count}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.avg_value || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Leaderboards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Query Leaderboard */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Queries</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Query</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Count</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latest</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {(data?.analysis_tables?.leaderboards?.top_queries || []).map((row, index) => (
                      <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">{row.query}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.search_count}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(row.latest_search).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* User Leaderboard */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Users</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User IP</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sessions</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Searches</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Engagement</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {(data?.analysis_tables?.leaderboards?.top_users || []).map((row, index) => (
                      <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">{row.user_ip.substring(0, 12)}...</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.total_sessions}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.total_searches}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.avg_engagement_score.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard