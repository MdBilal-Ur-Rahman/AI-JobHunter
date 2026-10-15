
import { useCallback, useEffect, useState } from "react"
import { useAuth } from "../context/AuthContext"
import { getDashboardSummary } from "../services/api"

function DashboardCards() {
  const { token } = useAuth()

  const [stats, setStats] = useState({
    jobs_found: 0,
    matched_jobs: 0,
    applications: 0,
  })

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState("")

  const loadDashboardSummary = useCallback(
    async ({ showLoading = false } = {}) => {
      if (!token) {
        setStats({
          jobs_found: 0,
          matched_jobs: 0,
          applications: 0,
        })
        setLoading(false)
        setRefreshing(false)
        setError("")
        return
      }

      if (showLoading) {
        setLoading(true)
      } else {
        setRefreshing(true)
      }

      setError("")

      try {
        const data = await getDashboardSummary(token)

        setStats({
          jobs_found: Number(data?.jobs_found) || 0,
          matched_jobs: Number(data?.matched_jobs) || 0,
          applications: Number(data?.applications) || 0,
        })
      } catch (err) {
        console.error(
          "Failed to load dashboard statistics:",
          err
        )

        setError(
          err?.message ||
            "Failed to load dashboard statistics."
        )
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [token]
  )

  // Initial load and login/token changes.
  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadDashboardSummary({ showLoading: true })
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [loadDashboardSummary])

  // Refresh statistics only after relevant data changes.
  useEffect(() => {
    function handleDashboardUpdate() {
      loadDashboardSummary()
    }

    window.addEventListener(
      "dashboard-summary-updated",
      handleDashboardUpdate
    )

    window.addEventListener(
      "job-match-updated",
      handleDashboardUpdate
    )

    window.addEventListener(
      "applications-updated",
      handleDashboardUpdate
    )

    return () => {
      window.removeEventListener(
        "dashboard-summary-updated",
        handleDashboardUpdate
      )

      window.removeEventListener(
        "job-match-updated",
        handleDashboardUpdate
      )

      window.removeEventListener(
        "applications-updated",
        handleDashboardUpdate
      )
    }
  }, [loadDashboardSummary])

  const cards = [
    {
      title: "Jobs Found",
      value: stats.jobs_found,
      description: "Jobs discovered from job sources",
    },
    {
      title: "Matched Jobs",
      value: stats.matched_jobs,
      description: "Jobs matching your resume",
    },
    {
      title: "Applications",
      value: stats.applications,
      description: "Applications in your tracker",
    },
  ]

  return (
    <section className="mt-6 w-full">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p
          aria-live="polite"
          className="text-xs text-gray-500 dark:text-gray-400"
        >
          {refreshing ? "Updating statistics..." : ""}
        </p>

        <button
          type="button"
          onClick={() => loadDashboardSummary()}
          disabled={loading || refreshing}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          {refreshing ? "Refreshing..." : "Refresh Stats"}
        </button>
      </div>

      {error && (
        <div
          className="mb-4 flex flex-col gap-2 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300 sm:flex-row sm:items-center sm:justify-between"
          role="alert"
        >
          <p>{error}</p>

          <button
            type="button"
            onClick={() =>
              loadDashboardSummary({ showLoading: true })
            }
            className="w-fit rounded-lg border border-red-300 px-3 py-1.5 font-medium hover:bg-red-100 dark:border-red-700 dark:hover:bg-red-950"
          >
            Try Again
          </button>
        </div>
      )}

      <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <div
            key={card.title}
            className="min-w-0 rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-900 sm:p-5 lg:p-6"
          >
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              {card.title}
            </p>

            <div className="mt-2">
              {loading ? (
                <div
                  className="h-10 w-16 animate-pulse rounded-md bg-gray-200 dark:bg-gray-700"
                  aria-label={`Loading ${card.title}`}
                />
              ) : (
                <p className="text-3xl font-bold leading-tight text-gray-900 dark:text-white sm:text-4xl">
                  {card.value}
                </p>
              )}
            </div>

            <p className="mt-2 text-xs leading-5 text-gray-500 dark:text-gray-400 sm:text-sm">
              {card.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}

export default DashboardCards
