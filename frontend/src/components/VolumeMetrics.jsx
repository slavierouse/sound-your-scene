function VolumeMetrics({ metrics }) {
  if (!metrics) return null

  const metricCards = [
    { label: '# Users', value: metrics.users, description: 'Unique user sessions' },
    { label: '# User Sessions', value: metrics.user_sessions, description: 'Total site visits' },
    { label: '# Search Sessions', value: metrics.search_sessions, description: 'Search conversations' },
    { label: '# Search Jobs', value: metrics.search_jobs, description: 'Individual queries' },
    { label: '# Playlists', value: metrics.playlists, description: 'Created playlists' },
    { label: '# Emails Sent', value: metrics.emails_sent, description: 'Successful email sends' },
    { label: '# Unique Emails', value: metrics.unique_emails, description: 'Distinct email addresses' }
  ]

  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Volume Metrics</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {metricCards.map((metric, index) => (
          <div key={index} className="bg-white p-4 rounded-lg shadow text-center">
            <div className="text-2xl font-bold text-blue-600 mb-1">
              {metric.value.toLocaleString()}
            </div>
            <div className="text-sm font-medium text-gray-900 mb-1">
              {metric.label}
            </div>
            <div className="text-xs text-gray-500">
              {metric.description}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default VolumeMetrics