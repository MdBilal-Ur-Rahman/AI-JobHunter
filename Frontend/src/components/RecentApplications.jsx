import { useCallback, useEffect, useState } from "react"
import { useAuth } from "../context/AuthContext"
import {
  approveApplication,
  checkApplicationSubmissionGate,
  deleteApplication,
  getApplications,
  getMySearchResults,
  inspectApplication,
  mapApplicationFields,
  saveJobAndTrack,
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
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [searchResultsError, setSearchResultsError] = useState("")
  const [updatingId, setUpdatingId] = useState("")
  const [deletingId, setDeletingId] = useState("")
  const [gateResults, setGateResults] = useState({})
  const [reviewResults, setReviewResults] = useState({})
  const [actionId, setActionId] = useState("")
  const [savingResultId, setSavingResultId] = useState("")
  const [savedResultIds, setSavedResultIds] = useState({})
  const [saveResultMessages, setSaveResultMessages] = useState({})

  const loadApplications = useCallback(async () => {
    if (!token) {
      setApplications([])
      setSearchResults([])
      return
    }

    const [applicationsResult, searchResultsResult] =
      await Promise.allSettled([
        getApplications(token),
        getMySearchResults(token),
      ])

    if (applicationsResult.status === "fulfilled") {
      setError("")
      setApplications(
        Array.isArray(applicationsResult.value?.applications)
          ? applicationsResult.value.applications
          : []
      )
    } else {
      console.error(
        "Failed to load applications:",
        applicationsResult.reason
      )
      setError(getErrorMessage(applicationsResult.reason))
    }

    if (searchResultsResult.status === "fulfilled") {
      setSearchResultsError("")
      setSearchResults(
        Array.isArray(searchResultsResult.value?.results)
          ? searchResultsResult.value.results
          : []
      )
    } else {
      console.error(
        "Failed to load live job results:",
        searchResultsResult.reason
      )
      setSearchResultsError(
        getErrorMessage(searchResultsResult.reason)
      )
    }

    setLoading(false)
  }, [token])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadApplications()
    }, 0)

    function handleApplicationsUpdated() {
      loadApplications()
    }

    function handleJobsSearchCompleted() {
      loadApplications()
    }

    window.addEventListener(
      "applications-updated",
      handleApplicationsUpdated
    )
    window.addEventListener(
      "jobs-search-completed",
      handleJobsSearchCompleted
    )

    return () => {
      window.clearTimeout(timeoutId)
      window.removeEventListener(
        "applications-updated",
        handleApplicationsUpdated
      )
      window.removeEventListener(
        "jobs-search-completed",
        handleJobsSearchCompleted
      )
    }
  }, [loadApplications])

  async function handleStatusChange(applicationId, status) {
    if (
      !token ||
      !applicationId ||
      updatingId ||
      deletingId === applicationId
    ) {
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

  async function handleDeleteApplication(applicationId, title) {
    if (
      !token ||
      !applicationId ||
      deletingId ||
      !window.confirm(
        `Delete "${title}" from your application tracker? This cannot be undone.`
      )
    ) {
      return
    }

    setDeletingId(applicationId)
    setError("")

    try {
      await deleteApplication(applicationId, token)
      setApplications((current) =>
        current.filter(
          (application) =>
            application.application_id !== applicationId
        )
      )
      window.dispatchEvent(new Event("applications-updated"))
      window.dispatchEvent(new Event("dashboard-summary-updated"))
    } catch (deleteError) {
      console.error("Failed to delete application:", deleteError)
      setError(getErrorMessage(deleteError))
    } finally {
      setDeletingId("")
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

  async function handleSaveSearchResult(result) {
    const resultId = result?.search_result_id || result?._id
    if (
      !token ||
      typeof resultId !== "string" ||
      !/^[a-fA-F0-9]{24}$/.test(resultId) ||
      result.url_verified !== true ||
      savingResultId
    ) {
      return
    }

    setSavingResultId(resultId)
    setSaveResultMessages((current) => ({
      ...current,
      [resultId]: "",
    }))

    try {
      const response = await saveJobAndTrack(resultId, token)
      if (!response.saved) {
        setSaveResultMessages((current) => ({
          ...current,
          [resultId]:
            response.saveResponse?.message || "This result was not saved.",
        }))
        return
      }

      setSavedResultIds((current) => ({
        ...current,
        [resultId]: true,
      }))
      setSaveResultMessages((current) => ({
        ...current,
        [resultId]: response.tracked
          ? "Job saved and added to your Application Tracker."
          : `Job saved, but not added to the tracker: ${
              response.trackingMessage ||
              response.trackingError?.message ||
              "the tracker could not be updated."
            }`,
      }))
      window.dispatchEvent(new Event("saved-jobs-updated"))
      if (response.tracked) {
        window.dispatchEvent(new Event("applications-updated"))
      }
      window.dispatchEvent(new Event("dashboard-summary-updated"))
    } catch (saveError) {
      console.error("Failed to save live search result:", saveError)
      setSaveResultMessages((current) => ({
        ...current,
        [resultId]: getErrorMessage(saveError),
      }))
    } finally {
      setSavingResultId("")
    }
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

      <div className="mb-6">
        <h4 className="mb-1 text-base font-semibold text-gray-900 dark:text-white">
          Live Job Results
        </h4>
        <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">
          Recent jobs found by your searches. Check each posting and employer
          before applying; a valid URL does not guarantee the job is genuine
          or still open.
        </p>

        {searchResultsError ? (
          <p
            className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300"
            role="alert"
          >
            Could not load live job results: {searchResultsError}
          </p>
        ) : searchResults.length === 0 ? (
          <p className="rounded-lg border border-dashed border-gray-300 px-4 py-5 text-center text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400">
            No live job results yet. Search for jobs on the dashboard to see
            them here.
          </p>
        ) : (
          <div className="space-y-3">
            {searchResults.map((result, index) => {
              const resultId =
                result.search_result_id || result._id || result.url
              const jobUrl = result.url
              let safeJobUrl = ""

              try {
                const parsedUrl = new URL(jobUrl)
                if (
                  ["http:", "https:"].includes(parsedUrl.protocol) &&
                  !parsedUrl.username &&
                  !parsedUrl.password
                ) {
                  safeJobUrl = parsedUrl.href
                }
              } catch {
                safeJobUrl = ""
              }

              return (
                <article
                  key={resultId || `search-result-${index}`}
                  className="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
                >
                  <h5 className="font-semibold text-gray-900 dark:text-white">
                    {result.title || "Untitled job"}
                  </h5>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    {result.company || "Employer not specified"}
                    {result.location ? ` · ${result.location}` : ""}
                  </p>
                  {result.location_confirmed === false &&
                    result.location_query && (
                      <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                        The posting does not confirm{" "}
                        {result.location_query}; verify the location before
                        applying.
                      </p>
                    )}
                  <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                    {result.url_verified === true
                      ? "Web result · Job authenticity not verified"
                      : "Manual review required · URL not verified"}
                  </p>
                  {safeJobUrl && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <a
                        href={safeJobUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        referrerPolicy="no-referrer"
                        className="inline-flex rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                      >
                        View job posting
                      </a>
                      {result.url_verified === true &&
                        typeof resultId === "string" &&
                        /^[a-fA-F0-9]{24}$/.test(resultId) && (
                          <button
                            type="button"
                            onClick={() => handleSaveSearchResult(result)}
                            disabled={
                              Boolean(savingResultId) ||
                              Boolean(savedResultIds[resultId])
                            }
                            className="inline-flex rounded-lg bg-green-600 px-3 py-2 text-xs font-semibold text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {savingResultId === resultId
                              ? "Saving..."
                              : savedResultIds[resultId]
                                ? "Saved"
                                : "Save Job"}
                          </button>
                        )}
                    </div>
                  )}
                  {saveResultMessages[resultId] && (
                    <p
                      className="mt-2 text-xs text-gray-600 dark:text-gray-400"
                      role="status"
                    >
                      {saveResultMessages[resultId]}
                    </p>
                  )}
                </article>
              )
            })}
          </div>
        )}
      </div>

      <div className="pt-5">
        <h4 className="mb-3 text-base font-semibold text-gray-900 dark:text-white">
          Application Tracker
        </h4>
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
            const review = reviewResults[application.application_id]
            const inspection = review?.result?.inspection
            const mapping = review?.result?.mapping
            const mappedFields = Array.isArray(mapping?.mappings)
              ? mapping.mappings
              : []
            const visibleInputs = Array.isArray(inspection?.forms)
              ? inspection.forms.flatMap((form) =>
                  (form.inputs || []).filter((input) => {
                    const identity = `${input.name || ""} ${input.id || ""}`
                    return (
                      input.type !== "hidden" &&
                      !/password|csrf|session|token/i.test(identity)
                    )
                  })
                )
              : []

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
                  <div className="flex w-full items-end gap-2 sm:w-auto">
                    <label className="min-w-0 flex-1 text-sm text-gray-600 dark:text-gray-300 sm:w-48 sm:flex-none">
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
                          updatingId === application.application_id ||
                          deletingId === application.application_id
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
                    <button
                      type="button"
                      onClick={() =>
                        handleDeleteApplication(
                          application.application_id,
                          title
                        )
                      }
                      disabled={
                        Boolean(deletingId) ||
                        updatingId === application.application_id ||
                        actionId === application.application_id
                      }
                      className="h-[38px] shrink-0 rounded-lg border border-red-300 px-3 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950/40"
                    >
                      {deletingId === application.application_id
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      handleInspectApplication(application.application_id)
                    }
                    disabled={
                      actionId === application.application_id ||
                      deletingId === application.application_id
                    }
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
                    disabled={
                      actionId === application.application_id ||
                      deletingId === application.application_id
                    }
                    className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
                  >
                    Map verified resume fields
                  </button>
                </div>
                {review && (
                  <div
                    className="mt-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-800"
                    role="status"
                  >
                    <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">
                      {review.type === "mapping"
                        ? "Verified-resume field mapping"
                        : "Application page inspection"}
                    </p>
                    <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                      {review.result?.message || "Review data is available."}{" "}
                      No application was submitted.
                    </p>
                    {review.result?.safety_note && (
                      <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                        {review.result.safety_note}
                      </p>
                    )}
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs font-medium text-blue-700 dark:text-blue-300">
                        View review details
                      </summary>
                      <div className="mt-2 space-y-2 rounded bg-white p-3 text-xs text-gray-700 dark:bg-gray-900 dark:text-gray-300">
                        {review.type === "inspection" && inspection && (
                          <>
                            {inspection.title && (
                              <p>
                                <span className="font-semibold">Page:</span>{" "}
                                {inspection.title}
                              </p>
                            )}
                            <p>
                              <span className="font-semibold">Forms found:</span>{" "}
                              {inspection.form_count ?? inspection.forms?.length ?? 0}
                            </p>
                            {inspection.blocked && (
                              <p>
                                <span className="font-semibold">Access:</span>{" "}
                                Sign-in or page restrictions were detected.
                              </p>
                            )}
                            {visibleInputs.length > 0 && (
                              <div>
                                <p className="font-semibold">
                                  Visible form fields:
                                </p>
                                <ul className="mt-1 list-inside list-disc">
                                  {visibleInputs.slice(0, 12).map((input, index) => (
                                    <li key={`${input.name || input.id || "field"}-${index}`}>
                                      {input.placeholder ||
                                        input.name ||
                                        input.id ||
                                        `${input.type || "text"} field`}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {visibleInputs.length === 0 && (
                              <p>
                                No safe, user-facing form fields were available
                                to display.
                              </p>
                            )}
                          </>
                        )}
                        {review.type === "mapping" && (
                          mappedFields.length > 0 ? (
                            <ul className="space-y-1">
                              {mappedFields.map((field, index) => (
                                <li key={`${field.field_name || field.name || "field"}-${index}`}>
                                  <span className="font-semibold">
                                    {field.field_name || field.name || "Form field"}:
                                  </span>{" "}
                                  {field.available && field.value
                                    ? field.value
                                    : "Not found in verified resume"}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p>No verified-resume field mappings were found.</p>
                          )
                        )}
                        {review.type !== "inspection" &&
                          review.type !== "mapping" && (
                            <p>No additional readable review details.</p>
                          )}
                      </div>
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
                      disabled={
                        actionId === application.application_id ||
                        deletingId === application.application_id
                      }
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
                      disabled={
                        actionId === application.application_id ||
                        deletingId === application.application_id
                      }
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
      </div>
    </section>
  )
}

export default RecentApplications