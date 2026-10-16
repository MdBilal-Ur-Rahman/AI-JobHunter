import { useCallback, useEffect, useState } from "react"
import { useAuth } from "../context/AuthContext"
import { getJobMatches, getJobs } from "../services/api"

function ResumeMatchHistory() {
  const { token } = useAuth()
  const [matches, setMatches] = useState([])
  const [jobsById, setJobsById] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const loadMatches = useCallback(async () => {
    if (!token) {
      setMatches([])
      setJobsById({})
      setLoading(false)
      return
    }

    setLoading(true)
    setError("")

    try {
      const [matchResponse, jobsResponse] = await Promise.all([
        getJobMatches(token),
        getJobs(token),
      ])
      const savedJobs = Array.isArray(jobsResponse?.jobs)
        ? jobsResponse.jobs
        : []
      const jobLookup = Object.fromEntries(
        savedJobs.map((job) => [
          String(job?.job_id || job?._id || job?.id || ""),
          job,
        ])
      )

      setMatches(
        Array.isArray(matchResponse?.matches)
          ? matchResponse.matches
          : []
      )
      setJobsById(jobLookup)
    } catch (loadError) {
      console.error("Failed to load resume match history:", loadError)
      setError(
        loadError?.message ||
          "Unable to load resume match history."
      )
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    const timeoutId = window.setTimeout(loadMatches, 0)
    function handleMatchUpdated() {
      loadMatches()
    }

    window.addEventListener("job-match-updated", handleMatchUpdated)
    return () => {
      window.clearTimeout(timeoutId)
      window.removeEventListener("job-match-updated", handleMatchUpdated)
    }
  }, [loadMatches])

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Resume Matches
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Your saved resume-to-job comparisons.
        </p>
      </div>

      {loading ? (
        <p className="py-5 text-center text-sm text-gray-500 dark:text-gray-400">
          Loading resume matches...
        </p>
      ) : error ? (
        <p
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300"
          role="alert"
        >
          {error}
        </p>
      ) : matches.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 px-4 py-6 text-center dark:border-gray-700">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
            No resume matches yet
          </p>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Save a job, then choose Match Resume to compare it with your
            verified resume.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {matches.slice(0, 5).map((match) => {
            const job = jobsById[String(match.job_id)]
            const result = match.match_result || {}
            const score = Number(result.match_score)
            const hasScore = Number.isFinite(score)
            const matchedSkills = Array.isArray(result.matched_skills)
              ? result.matched_skills
              : []

            return (
              <article
                key={match.match_id}
                className="flex flex-col gap-3 rounded-xl border border-gray-200 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-gray-700"
              >
                <div className="min-w-0">
                  <h3 className="truncate font-medium text-gray-900 dark:text-white">
                    {job?.title || "Saved job"}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {[job?.company, job?.location]
                      .filter(
                        (value) =>
                          value &&
                          value !== "Not specified"
                      )
                      .join(" · ") || "Employer or location not specified"}
                  </p>
                  {result.summary && (
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                      {result.summary}
                    </p>
                  )}
                  {matchedSkills.length > 0 && (
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      Matched skills: {matchedSkills.slice(0, 4).join(", ")}
                    </p>
                  )}
                </div>
                {hasScore && (
                  <div className="flex shrink-0 items-center gap-3 sm:w-40">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
                      <div
                        className="h-full rounded-full bg-blue-600"
                        style={{
                          width: `${Math.min(100, Math.max(0, score))}%`,
                        }}
                      />
                    </div>
                    <span className="w-12 text-right text-sm font-semibold text-blue-700 dark:text-blue-300">
                      {score}%
                    </span>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default ResumeMatchHistory
