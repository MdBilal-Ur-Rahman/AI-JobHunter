
import { useEffect, useRef, useState } from "react"
import { useAuth } from "../context/AuthContext"
import {
  searchJobs,
  getMySearchResults,
  normalizeAndStoreJob,
} from "../services/api"

function JobSearch() {
  const { token } = useAuth()

  const [jobTitle, setJobTitle] = useState("")
  const [location, setLocation] = useState("")
  const [jobs, setJobs] = useState([])
  const [blockedUrls, setBlockedUrls] = useState([])
  const [invalidUrls, setInvalidUrls] = useState([])
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [savingJobIds, setSavingJobIds] = useState([])
  const [saveMessages, setSaveMessages] = useState({})
  const [saveErrors, setSaveErrors] = useState({})
  const jobsLoadId = useRef(0)

  useEffect(() => {
    const loadId = ++jobsLoadId.current

    if (!token) {
      setJobs([])
      return
    }

    let isCurrent = true

    async function loadPreviouslyDiscoveredJobs() {
      try {
        const response = await getMySearchResults(token)

        if (
          isCurrent &&
          jobsLoadId.current === loadId
        ) {
          setJobs(response.results)
        }
      } catch (err) {
        console.error(
          "Failed to load previously discovered jobs:",
          err
        )

        if (
          isCurrent &&
          jobsLoadId.current === loadId
        ) {
          setError(
            err?.message ||
              "Failed to load previously discovered jobs."
          )
        }
      }
    }

    loadPreviouslyDiscoveredJobs()

    return () => {
      isCurrent = false
    }
  }, [token])

  // Extract job results from supported backend response formats.
  function extractJobs(data) {
    if (Array.isArray(data)) {
      return data
    }

    if (!data || typeof data !== "object") {
      return []
    }

    if (Array.isArray(data.searches)) {
      return data.searches.flatMap((search) =>
        Array.isArray(search?.saved_results)
          ? search.saved_results
          : []
      )
    }

    const possibleKeys = [
      "results",
      "jobs",
      "data",
      "items",
      "search_results",
      "job_results",
      "documents",
      "saved_results",
    ]

    for (const key of possibleKeys) {
      if (Array.isArray(data[key])) {
        return data[key]
      }
    }

    if (data.data && typeof data.data === "object") {
      return extractJobs(data.data)
    }

    return []
  }

  function getJobKey(job, index) {
    return (
      job?.search_result_id ||
      job?._id ||
      job?.job_id ||
      job?.id ||
      job?.url ||
      job?.application_url ||
      `job-${index}`
    )
  }

  function getTitle(job) {
    return (
      getFirstText(
        job?.title,
        job?.job_title,
        job?.position,
        job?.name
      ) || "Untitled Job"
    )
  }

  // Return the first non-empty string from the supplied values.
  function getFirstText(...values) {
    for (const value of values) {
      if (typeof value === "string" && value.trim()) {
        return value.trim()
      }

      if (typeof value === "number") {
        return String(value)
      }
    }

    return ""
  }

  // Do not infer an employer from the website domain.
  function getCompany(job) {
    const company = getFirstText(
      job?.company,
      job?.company_name,
      job?.companyName,
      job?.organization,
      job?.organization_name,
      job?.employer,
      job?.employer_name
    )

    return company || "Not specified"
  }

  function getLocation(job) {
    const value =
      job?.location ??
      job?.job_location ??
      job?.jobLocation ??
      job?.locations ??
      job?.work_location ??
      job?.workLocation

    if (Array.isArray(value)) {
      const locations = value
        .map((item) => {
          if (typeof item === "string") {
            return item.trim()
          }

          if (item && typeof item === "object") {
            return getFirstText(
              item?.name,
              item?.location,
              item?.address,
              item?.city
            )
          }

          return ""
        })
        .filter(Boolean)

      return locations.length
        ? [...new Set(locations)].join(", ")
        : "Not specified"
    }

    if (value && typeof value === "object") {
      return (
        getFirstText(
          value?.name,
          value?.city,
          value?.address,
          value?.location
        ) || "Not specified"
      )
    }

    return getFirstText(value) || "Not specified"
  }

  function getEmploymentType(job) {
    return getFirstText(
      job?.employment_type,
      job?.employmentType,
      job?.job_type,
      job?.jobType,
      job?.type
    )
  }

  function getExperience(job) {
    return getFirstText(
      job?.experience_required,
      job?.experienceRequired,
      job?.experience,
      job?.experience_level,
      job?.experienceLevel
    )
  }

  function getSalary(job) {
    const salary =
      job?.salary ??
      job?.salary_range ??
      job?.salaryRange ??
      job?.compensation

    if (
      typeof salary === "string" ||
      typeof salary === "number"
    ) {
      return String(salary)
    }

    if (salary && typeof salary === "object") {
      return getFirstText(
        salary?.description,
        salary?.formatted,
        salary?.range,
        salary?.amount
      )
    }

    return ""
  }

  function getDescription(job) {
    return getFirstText(
      job?.description,
      job?.content,
      job?.snippet,
      job?.summary,
      job?.job_description,
      job?.jobDescription
    )
  }

  function getApplicationUrl(job) {
    return getFirstText(
      job?.application_url,
      job?.applicationUrl,
      job?.apply_url,
      job?.applyUrl,
      job?.url,
      job?.link
    )
  }

  function getSkills(job) {
    const skills =
      job?.required_skills ??
      job?.requiredSkills ??
      job?.skills

    if (Array.isArray(skills)) {
      return skills
        .map((skill) => {
          if (typeof skill === "string") {
            return skill.trim()
          }

          if (skill && typeof skill === "object") {
            return getFirstText(
              skill?.name,
              skill?.skill
            )
          }

          return ""
        })
        .filter(Boolean)
    }

    if (typeof skills === "string" && skills.trim()) {
      return skills
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean)
    }

    return []
  }

  // Only allow external HTTP/HTTPS links without credentials.
  // Backend verification remains authoritative.
  function isSafeExternalUrl(value) {
    if (!value || typeof value !== "string") {
      return false
    }

    try {
      const parsedUrl = new URL(value)

      return (
        (parsedUrl.protocol === "https:" ||
          parsedUrl.protocol === "http:") &&
        Boolean(parsedUrl.hostname) &&
        !parsedUrl.username &&
        !parsedUrl.password
      )
    } catch {
      return false
    }
  }

  function collectSearchItems(data, key) {
    if (!Array.isArray(data?.searches)) {
      return []
    }

    return data.searches.flatMap((search) =>
      Array.isArray(search?.[key])
        ? search[key]
        : []
    )
  }

  // Save an individual job through the existing backend endpoint.
  async function handleSaveJob(job) {
    const searchResultId = job?.search_result_id

    if (
      typeof searchResultId !== "string" ||
      !/^[a-fA-F0-9]{24}$/.test(searchResultId)
    ) {
      setSaveErrors((previous) => ({
        ...previous,
        [getJobKey(job, 0)]:
          "This result cannot be saved because its search result ID is missing or invalid.",
      }))
      return
    }

    if (!token) {
      setSaveErrors((previous) => ({
        ...previous,
        [searchResultId]:
          "Your session has expired. Please log in again.",
      }))
      return
    }

    if (savingJobIds.includes(searchResultId)) {
      return
    }

    setSavingJobIds((previous) => [
      ...previous,
      searchResultId,
    ])

    setSaveMessages((previous) => ({
      ...previous,
      [searchResultId]: "",
    }))

    setSaveErrors((previous) => ({
      ...previous,
      [searchResultId]: "",
    }))

    try {
      const response = await normalizeAndStoreJob(
        searchResultId,
        token
      )

      if (response?.is_individual_job === false) {
        setSaveMessages((previous) => ({
          ...previous,
          [searchResultId]:
            "This result is a general search page, not an individual job posting. It was not added to Saved Jobs.",
        }))
        return
      }

      setSaveMessages((previous) => ({
        ...previous,
        [searchResultId]:
          response?.message || "Job saved successfully.",
      }))

      // Notify SavedJobs.jsx to refresh its list.
      window.dispatchEvent(
        new CustomEvent("saved-jobs-updated")
      )
    } catch (err) {
      console.error("Failed to save job:", err)

      setSaveErrors((previous) => ({
        ...previous,
        [searchResultId]:
          err?.message ||
          "Unable to save this job. Please try again.",
      }))
    } finally {
      setSavingJobIds((previous) =>
        previous.filter((id) => id !== searchResultId)
      )
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()

    setMessage("")
    setError("")
    setJobs([])
    setBlockedUrls([])
    setInvalidUrls([])
    setSaveMessages({})
    setSaveErrors({})

    if (!jobTitle.trim() && !location.trim()) {
      setError("Please enter a job title or location.")
      return
    }

    if (!token) {
      setError("Your session has expired. Please log in again.")
      return
    }

    jobsLoadId.current += 1

    try {
      setIsSearching(true)

      const data = await searchJobs(
        jobTitle.trim(),
        location.trim(),
        token
      )

      console.log(
        "TAVILY RESPONSE JSON:",
        JSON.stringify(data, null, 2)
      )

      const results = extractJobs(data)

      const blocked = collectSearchItems(
        data,
        "verification_blocked_urls"
      )

      const invalid = collectSearchItems(
        data,
        "invalid_urls"
      )

      console.log("EXTRACTED JOBS:", results)
      console.log("BLOCKED URLS:", blocked)
      console.log("INVALID URLS:", invalid)

      setJobs(results)
      setBlockedUrls(blocked)
      setInvalidUrls(invalid)

      window.dispatchEvent(new Event("jobs-search-completed"))
      window.dispatchEvent(new Event("dashboard-summary-updated"))

      const totalSaved = Number(data?.total_saved) || 0
      const totalDuplicates =
        Number(data?.total_duplicates) || 0
      const normalization = data?.normalization
      const normalizedSaved =
        Number(normalization?.newly_saved_jobs) || 0
      const normalizationSkipped =
        Number(normalization?.skipped_jobs) || 0
      const normalizationErrorCount =
        Array.isArray(normalization?.errors)
          ? normalization.errors.length
          : 0

      const totalInvalidUrls =
        Number(data?.total_invalid_urls) || invalid.length

      const totalBlocked =
        Number(data?.total_verification_blocked) ||
        blocked.length

      const summaryParts = []

      if (totalSaved > 0) {
        summaryParts.push(
          `${totalSaved} new raw search result(s) stored`
        )
      }

      if (totalDuplicates > 0) {
        summaryParts.push(
          `${totalDuplicates} raw result(s) were already stored`
        )
      }

      if (normalizedSaved > 0) {
        summaryParts.push(
          `${normalizedSaved} normalized job(s) added to Saved Jobs`
        )
      }

      if (normalizationSkipped > 0) {
        summaryParts.push(
          `${normalizationSkipped} result(s) skipped during normalization`
        )
      }

      if (normalizationErrorCount > 0) {
        summaryParts.push(
          `${normalizationErrorCount} normalization error(s); see the response details`
        )
      }

      if (totalInvalidUrls > 0) {
        summaryParts.push(
          `${totalInvalidUrls} URL(s) failed verification`
        )
      }

      if (totalBlocked > 0) {
        summaryParts.push(
          `${totalBlocked} URL(s) require manual review`
        )
      }

      if (summaryParts.length > 0) {
        setMessage(
          `Search completed. ${summaryParts.join(". ")}.`
        )
      } else if (results.length > 0) {
        setMessage(
          `Search completed. ${results.length} result(s) returned.`
        )
      } else {
        setMessage(
          "Search completed, but no job results were returned. Try another search query."
        )
      }
    } catch (err) {
      console.error("Job search failed:", err)

      setError(
        err?.message ||
          "Failed to search jobs. Please try again."
      )
    } finally {
      setIsSearching(false)
    }
  }

  function handleClear() {
    jobsLoadId.current += 1
    setJobTitle("")
    setLocation("")
    setJobs([])
    setBlockedUrls([])
    setInvalidUrls([])
    setMessage("")
    setError("")
    setSaveMessages({})
    setSaveErrors({})
  }

  function ExternalLink({ url, children }) {
    if (!isSafeExternalUrl(url)) {
      return (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Link unavailable because the URL format is invalid.
        </span>
      )
    }

    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        referrerPolicy="no-referrer"
        className="inline-flex rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
      >
        {children}
      </a>
    )
  }

  return (
    <section className="w-full rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white sm:text-xl">
          Search Jobs
        </h2>

        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Discover jobs matching your skills and preferred location.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label
              htmlFor="job-title"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Job Title / Skill
            </label>

            <input
              id="job-title"
              type="text"
              value={jobTitle}
              onChange={(event) =>
                setJobTitle(event.target.value)
              }
              placeholder="e.g. React, Python, Developer"
              disabled={isSearching}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:disabled:bg-gray-700"
            />
          </div>

          <div>
            <label
              htmlFor="job-location"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Location
            </label>

            <input
              id="job-location"
              type="text"
              value={location}
              onChange={(event) =>
                setLocation(event.target.value)
              }
              placeholder="e.g. Hyderabad, Bangalore, Remote"
              disabled={isSearching}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:disabled:bg-gray-700"
            />
          </div>
        </div>

        {message && (
          <div
            className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-300"
            role="status"
          >
            {message}
          </div>
        )}

        {error && (
          <div
            className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300"
            role="alert"
          >
            {error}
          </div>
        )}

        {isSearching && (
          <div
            className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-300"
            role="status"
          >
            Searching for jobs...
          </div>
        )}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={handleClear}
            disabled={isSearching}
            className="w-full rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            Clear
          </button>

          <button
            type="submit"
            disabled={isSearching}
            className="w-full rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {isSearching ? "Searching..." : "Search Jobs"}
          </button>
        </div>
      </form>

      {/* Search results */}
      {jobs.length > 0 && (
        <div className="mt-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">
              Search Results
            </h3>

            <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
              {jobs.length} found
            </span>
          </div>

          <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
            Discovered results are retained here. Only individual
            postings that pass normalization and URL checks are added
            to Saved Jobs.
          </p>

          <div className="space-y-3">
            {jobs.map((job, index) => {
              const title = getTitle(job)
              const company = getCompany(job)
              const jobLocation = getLocation(job)
              const employmentType = getEmploymentType(job)
              const experience = getExperience(job)
              const salary = getSalary(job)
              const description = getDescription(job)
              const applicationUrl = getApplicationUrl(job)
              const skills = getSkills(job)

              const urlVerified =
                job?.url_verified === true

              const jobVerified =
                job?.job_verified === true

              const searchResultId = job?.search_result_id

              const hasValidSearchResultId =
                typeof searchResultId === "string" &&
                /^[a-fA-F0-9]{24}$/.test(searchResultId)

              return (
                <article
                  key={getJobKey(job, index)}
                  className="rounded-xl border border-gray-200 p-4 transition hover:shadow-sm dark:border-gray-700"
                >
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <h4 className="break-words text-base font-semibold text-gray-900 dark:text-white">
                        {title}
                      </h4>

                      <div className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
                        <p>
                          <span className="font-medium">
                            Company:
                          </span>{" "}
                          {company}
                        </p>

                        <p>
                          <span className="font-medium">
                            Location:
                          </span>{" "}
                          {jobLocation}
                        </p>

                        {employmentType && (
                          <p>
                            <span className="font-medium">
                              Type:
                            </span>{" "}
                            {employmentType}
                          </p>
                        )}

                        {experience && (
                          <p>
                            <span className="font-medium">
                              Experience:
                            </span>{" "}
                            {experience}
                          </p>
                        )}
                      </div>
                    </div>

                    {salary && (
                      <div className="shrink-0 rounded-lg bg-gray-50 px-3 py-2 text-sm font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                        {salary}
                      </div>
                    )}
                  </div>

                  {description && (
                    <p className="mt-4 whitespace-pre-line text-sm leading-6 text-gray-600 dark:text-gray-400">
                      {description}
                    </p>
                  )}

                  {skills.length > 0 && (
                    <div className="mt-4">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                        Skills
                      </p>

                      <div className="flex flex-wrap gap-2">
                        {skills.map((skill, skillIndex) => (
                          <span
                            key={`${skill}-${skillIndex}`}
                            className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-4 border-t border-gray-100 pt-4 dark:border-gray-800">
                    <div className="flex flex-wrap items-center gap-3">
                      <ExternalLink url={applicationUrl}>
                        View Job
                      </ExternalLink>

                      {hasValidSearchResultId && (
                        <button
                          type="button"
                          onClick={() => handleSaveJob(job)}
                          disabled={savingJobIds.includes(searchResultId)}
                          className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {savingJobIds.includes(searchResultId)
                            ? "Saving..."
                            : "Save Job"}
                        </button>
                      )}
                    </div>

                    {hasValidSearchResultId &&
                      saveMessages[searchResultId] && (
                        <p
                          className="mt-3 text-sm text-green-700 dark:text-green-400"
                          role="status"
                        >
                          {saveMessages[searchResultId]}
                        </p>
                      )}

                    {hasValidSearchResultId &&
                      saveErrors[searchResultId] && (
                        <p
                          className="mt-3 text-sm text-red-600 dark:text-red-400"
                          role="alert"
                        >
                          {saveErrors[searchResultId]}
                        </p>
                      )}

                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {jobVerified
                        ? "Job authenticity has been verified by the backend."
                        : urlVerified
                          ? "URL checks passed. Job authenticity has not been independently verified."
                          : "Review the destination and job details carefully before applying."}
                    </p>
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      )}

      {/* URLs requiring manual review */}
      {blockedUrls.length > 0 && (
        <div className="mt-8">
          <div className="mb-3">
            <h3 className="text-base font-semibold text-amber-700 dark:text-amber-400">
              Manual Review Required
            </h3>

            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Automated verification could not approve these
              destinations. This does not necessarily mean the
              jobs are unsafe. Review the website and employer
              manually before applying.
            </p>
          </div>

          <div className="space-y-3">
            {blockedUrls.map((item, index) => {
              const url = item?.url
              const title =
                item?.title || "Untitled job result"

              return (
                <article
                  key={`${url || "blocked"}-${index}`}
                  className="rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/20"
                >
                  <h4 className="break-words font-semibold text-gray-900 dark:text-white">
                    {title}
                  </h4>

                  <p className="mt-2 text-sm text-amber-800 dark:text-amber-300">
                    {item?.message ||
                      item?.verification?.message ||
                      "Automated verification was blocked. Manual review is required."}
                  </p>

                  <div className="mt-3">
                    <ExternalLink url={url}>
                      Open Job Website
                    </ExternalLink>
                  </div>

                  <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                    Status: Not verified. Check the employer,
                    job details and application page manually.
                  </p>
                </article>
              )
            })}
          </div>
        </div>
      )}

      {/* URLs rejected by verification */}
      {invalidUrls.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-3 text-base font-semibold text-gray-900 dark:text-white">
            URLs That Could Not Be Verified
          </h3>

          <div className="space-y-3">
            {invalidUrls.map((item, index) => {
              const verification = item?.verification || {}

              return (
                <article
                  key={`${item?.url || "invalid"}-${index}`}
                  className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"
                >
                  <h4 className="break-words font-medium text-gray-900 dark:text-white">
                    {item?.title || "Untitled job result"}
                  </h4>

                  <p className="mt-2 break-words text-sm text-gray-600 dark:text-gray-400">
                    Reason:{" "}
                    {verification.message ||
                      verification.reason ||
                      "Unable to verify URL"}
                  </p>

                  {isSafeExternalUrl(item?.url) && (
                    <div className="mt-3">
                      <ExternalLink url={item.url}>
                        Open Link for Manual Review
                      </ExternalLink>
                    </div>
                  )}
                </article>
              )
            })}
          </div>
        </div>
      )}

      {!isSearching &&
        !error &&
        jobs.length === 0 &&
        blockedUrls.length === 0 &&
        invalidUrls.length === 0 &&
        message && (
          <div className="mt-6 rounded-xl border border-dashed border-gray-300 p-6 text-center dark:border-gray-600">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              No displayable job details
            </p>

            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {message}
            </p>
          </div>
        )}
    </section>
  )
}

export default JobSearch
