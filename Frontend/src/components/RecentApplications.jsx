import { useCallback, useEffect, useState } from "react"
import { useAuth } from "../context/AuthContext"
import {
  approveApplication,
  checkApplicationSubmissionGate,
  getApplications,
  inspectApplication,
  mapApplicationFields,
  updateApplicationStatus,
} from "../services/api"

const APPLICATION_STATUSES = [
  "discovered",
  "saved",
  "shortlisted",
  "ready-to-apply",
  "applied",
  "interview",
  "rejected",
]

function getErrorMessage(error) {
  return error?.message || "Unable to update applications."
}

function formatDate(value) {
  if (!value) {
    return "Not recorded"
  }

  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? "Not recorded"
    : date.toLocaleDateString()
}

function RecentApplications() {
  const { token } = useAuth()
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [updatingId, setUpdatingId] = useState("")
  const [gateResults, setGateResults] = useState({})
  const [reviewResults, setReviewResults] = useState({})
  const [actionId, setActionId] = useState("")

  const loadApplications = useCallback(async () => {
    if (!token) {
      return
    }

    try {
      const response = await getApplications(token)
      setError("")
      setApplications(
        Array.isArray(response?.applications)
          ? response.applications
          : []
      )
    } catch (loadError) {
      console.error("Failed to load applications:", loadError)
      setError(getErrorMessage(loadError))
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadApplications()
    }, 0)

    function handleApplicationsUpdated() {
      loadApplications()
    }

    window.addEventListener(
      "applications-updated",
      handleApplicationsUpdated
    )

    return () => {
      window.clearTimeout(timeoutId)
      window.removeEventListener(
        "applications-updated",
        handleApplicationsUpdated
      )
    }
  }, [loadApplications])

  async function handleStatusChange(applicationId, status) {
    if (!token || !applicationId || updatingId) {
      return
    }

    setUpdatingId(applicationId)
    setError("")

    try {
      await updateApplicationStatus(
        applicationId,
        status,
        token
      )

      setApplications((current) =>
        current.map((application) =>
          application.application_id === applicationId
            ? { ...application, status }
            : application
        )
      )

      window.dispatchEvent(
        new Event("applications-updated")
      )
      window.dispatchEvent(
        new Event("dashboard-summary-updated")
      )
    } catch (updateError) {
      console.error(
        "Failed to update application status:",
        updateError
      )
      setError(getErrorMessage(updateError))
    } finally {
      setUpdatingId("")
    }
  }

  async function handleApprove(applicationId) {
    if (!token || !applicationId || actionId) {
      return
    }

    setActionId(applicationId)
    setError("")

    try {
      const result = await approveApplication(
        applicationId,
        token
      )

      setApplications((current) =>
        current.map((application) =>
          application.application_id === applicationId
            ? {
                ...application,
                approved: result.approved,
                requires_user_review:
                  result.requires_user_review,
                status: result.status,
              }
            : application
        )
      )
      window.dispatchEvent(new Event("applications-updated"))
    } catch (approveError) {
      console.error(
        "Failed to approve application for review:",
        approveError
      )
      setError(getErrorMessage(approveError))
    } finally {
      setActionId("")
    }
  }

  async function handleSubmissionGate(applicationId) {
    if (!token || !applicationId || actionId) {
      return
    }

    setActionId(applicationId)
    setError("")

    try {
      const result = await checkApplicationSubmissionGate(
        applicationId,
        token
      )

      setGateResults((current) => ({
        ...current,
        [applicationId]: result,
      }))
    } catch (gateError) {
      console.error(
        "Application safety check failed:",
        gateError
      )
      setError(getErrorMessage(gateError))
    } finally {
      setActionId("")
    }
  }

  async function handleInspectApplication(applicationId) {
    if (!token || !applicationId || actionId) {
      return
    }

    setActionId(applicationId)
    setError("")

    try {
      const result = await inspectApplication(applicationId, token)
      setReviewResults((current) => ({
        ...current,
        [applicationId]: { type: "inspection", result },
      }))
    } catch (inspectError) {
      console.error("Application inspection failed:", inspectError)
      setError(getErrorMessage(inspectError))
    } finally {
      setActionId("")
    }
  }

  async function handleMapApplicationFields(applicationId) {
    if (!token || !applicationId || actionId) {
      return
    }

    setActionId(applicationId)
    setError("")

    try {
      const result = await mapApplicationFields(
        applicationId,
        token
      )
      setReviewResults((current) => ({
        ...current,
        [applicationId]: { type: "mapping", result },
      }))
    } catch (mappingError) {
      console.error("Application field mapping failed:", mappingError)
      setError(getErrorMessage(mappingError))
    } finally {
      setActionId("")
    }
  }

  function handleRefresh() {
    setLoading(true)
    loadApplications()
  }

  return (
    <section className="w-full rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white sm:text-xl">
          Recent Applications
        </h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Track your latest job applications.
        </p>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={loading}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <p
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300"
          role="alert"
        >
          {error}
        </p>
      )}

      {loading ? (
        <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
          Loading applications...
        </p>
      ) : applications.length === 0 ? (
        <div className="flex min-h-32 items-center justify-center rounded-lg border border-dashed border-gray-300 px-4 py-8 text-center dark:border-gray-600">
          <div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-200 sm:text-base">
              No applications yet
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 sm:text-sm">
              Prepared applications will appear here.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {applications.map((application) => {
            const title =
              application?.job?.title || "Untitled job"
            const company =
              application?.job?.company || "Not specified"

            return (
              <article
                key={application.application_id}
                className="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-white">
                      {title}
                    </h4>
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      {company}
                      {application?.job?.location
                        ? ` · ${application.job.location}`
                        : ""}
                    </p>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Created {formatDate(application.created_at)}
                    </p>
                  </div>
                  <label className="text-sm text-gray-600 dark:text-gray-300">
                    Status
                    <select
                      value={
                        APPLICATION_STATUSES.includes(
                          application.status
                        )
                          ? application.status
                          : "discovered"
                      }
                      onChange={(event) =>
                        handleStatusChange(
                          application.application_id,
                          event.target.value
                        )
                      }
                      disabled={
                        updatingId === application.application_id
                      }
                      className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                    >
                      {APPLICATION_STATUSES.map((status) => (
                        <option key={status} value={status}>
                          {status.replaceAll("-", " ")}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      handleInspectApplication(application.application_id)
                    }
                    disabled={actionId === application.application_id}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                  >
                    {actionId === application.application_id
                      ? "Working..."
                      : "Inspect application page"}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      handleMapApplicationFields(
                        application.application_id
                      )
                    }
                    disabled={actionId === application.application_id}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                  >
                    Map verified resume fields
                  </button>
                </div>
                {reviewResults[application.application_id] && (
                  <div
                    className="mt-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-800"
                    role="status"
                  >
                    <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">
                      {reviewResults[application.application_id].type ===
                      "mapping"
                        ? "Verified-resume field mapping"
                        : "Application page inspection"}
                    </p>
                    <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                      {reviewResults[application.application_id].result
                        ?.message ||
                        "Review data is available."}{" "}
                      No application was submitted.
                    </p>
                    {reviewResults[application.application_id].result
                      ?.safety_note && (
                      <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                        {
                          reviewResults[
                            application.application_id
                          ].result.safety_note
                        }
                      </p>
                    )}
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs font-medium text-blue-700 dark:text-blue-300">
                        View review details
                      </summary>
                      <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded bg-white p-2 text-xs text-gray-700 dark:bg-gray-900 dark:text-gray-300">
                        {JSON.stringify(
                          reviewResults[application.application_id].result
                            ?.inspection ??
                            reviewResults[application.application_id].result
                              ?.mapping ??
                            reviewResults[application.application_id].result
                              ?.verification ??
                            reviewResults[application.application_id].result,
                          null,
                          2
                        )}
                      </pre>
                    </details>
                  </div>
                )}
                {application.requires_user_review && (
                  <div className="mt-3">
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      Review is required before this application can proceed.
                    </p>
                    <button
                      type="button"
                      onClick={() =>
                        handleApprove(application.application_id)
                      }
                      disabled={actionId === application.application_id}
                      className="mt-2 rounded-lg border border-amber-400 px-3 py-2 text-xs font-semibold text-amber-800 hover:bg-amber-50 disabled:opacity-50 dark:text-amber-300 dark:hover:bg-amber-950"
                    >
                      {actionId === application.application_id
                        ? "Approving..."
                        : "I reviewed this application"}
                    </button>
                  </div>
                )}
                {application.approved && (
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={() =>
                        handleSubmissionGate(
                          application.application_id
                        )
                      }
                      disabled={actionId === application.application_id}
                      className="rounded-lg border border-blue-300 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-50 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-950"
                    >
                      {actionId === application.application_id
                        ? "Checking..."
                        : "Check safety before applying"}
                    </button>
                    {gateResults[application.application_id] && (
                      <p
                        className="mt-2 text-xs text-gray-600 dark:text-gray-400"
                        role="status"
                      >
                        {gateResults[application.application_id].message}
                        {" "}
                        {gateResults[application.application_id].submitted
                          ? "Application submitted."
                          : "No application was submitted."}
                      </p>
                    )}
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

export default RecentApplications