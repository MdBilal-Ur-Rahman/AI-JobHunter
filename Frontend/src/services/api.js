const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "")

// =========================================================
// RESPONSE HELPERS
// =========================================================

async function getResponseData(response) {
  try {
    return await response.json()
  } catch {
    return {}
  }
}

function getApiErrorMessage(data, fallbackMessage) {
  if (typeof data?.detail === "string") {
    return data.detail
  }

  if (typeof data?.message === "string") {
    return data.message
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => {
        if (typeof item === "string") {
          return item
        }

        if (typeof item?.msg === "string") {
          return item.msg
        }

        return null
      })
      .filter(Boolean)
      .join(", ")
  }

  return fallbackMessage
}

function createApiError(message, status, data = {}) {
  const error = new Error(message)
  error.status = status
  error.data = data
  return error
}

function getStoredToken() {
  return localStorage.getItem("access_token")
}

// =========================================================
// GENERIC API REQUEST
// =========================================================

async function apiRequest(
  endpoint,
  {
    method = "GET",
    body,
    token,
    headers = {},
    timeoutMs,
    ...options
  } = {}
) {
  const requestHeaders = {
    Accept: "application/json",
    ...headers,
  }

  const requestToken =
    token !== undefined ? token : getStoredToken()

  if (requestToken) {
    requestHeaders.Authorization = `Bearer ${requestToken}`
  }

  const isFormData =
    typeof FormData !== "undefined" &&
    body instanceof FormData

  if (body !== undefined && !isFormData) {
    requestHeaders["Content-Type"] = "application/json"
  }

  const timeoutController =
    Number.isFinite(timeoutMs) && timeoutMs > 0
      ? new AbortController()
      : null
  const timeoutId = timeoutController
    ? window.setTimeout(() => timeoutController.abort(), timeoutMs)
    : null

  let response
  let data

  try {
    response = await fetch(
      `${API_BASE_URL}${endpoint}`,
      {
        method,
        headers: requestHeaders,
        body:
          body === undefined
            ? undefined
            : isFormData
              ? body
              : JSON.stringify(body),
        ...options,
        ...(timeoutController
          ? { signal: timeoutController.signal }
          : {}),
      }
    )

    data = await getResponseData(response)
  } catch (error) {
    if (timeoutController?.signal.aborted) {
      throw createApiError(
        "This AI request timed out. Please try again.",
        408
      )
    }

    throw error
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId)
    }
  }

  if (!response.ok) {
    const message = getApiErrorMessage(
      data,
      `Request failed with status ${response.status}.`
    )

    // Session expiration should be handled only when
    // the server explicitly rejects the request with 401.
    if (response.status === 401) {
      localStorage.removeItem("access_token")
      localStorage.removeItem("auth_user")

      window.dispatchEvent(
        new CustomEvent("auth:session-expired")
      )
    }

    throw createApiError(
      message,
      response.status,
      data
    )
  }

  return data
}

// =========================================================
// AUTH
// =========================================================

export async function registerUser(name, email, password) {
  return apiRequest("/users/register", {
    method: "POST",
    body: {
      name: name.trim(),
      email: email.trim().toLowerCase(),
      password,
    },
  })
}

export async function loginUser(email, password) {
  return apiRequest("/users/login", {
    method: "POST",
    body: {
      email: email.trim().toLowerCase(),
      password,
    },
  })
}

export async function requestPasswordReset(email) {
  return apiRequest("/users/forgot-password", {
    method: "POST",
    body: {
      email: email.trim().toLowerCase(),
    },
  })
}

export async function resetPassword(token, newPassword) {
  return apiRequest("/users/reset-password", {
    method: "POST",
    body: {
      token,
      new_password: newPassword,
    },
  })
}

export async function logoutUser(token) {
  if (!token) {
    return {
      message: "No active login session found.",
    }
  }

  return apiRequest("/users/logout", {
    method: "POST",
    token,
  })
}

export async function getCurrentUser(token) {
  return apiRequest("/users/me", {
    method: "GET",
    token,
  })
}

export async function updateCurrentUser(profile, token) {
  return apiRequest("/users/me", {
    method: "PUT",
    body: {
      name: profile.name.trim(),
      email: profile.email.trim().toLowerCase(),
    },
    token,
  })
}

// =========================================================
// DASHBOARD
// =========================================================

export async function getDashboardSummary(token) {
  return apiRequest("/dashboard/summary", {
    method: "GET",
    token,
  })
}

// =========================================================
// RESUME
// =========================================================

export async function uploadResume(file, token) {
  const formData = new FormData()
  formData.append("file", file)

  return apiRequest("/resumes", {
    method: "POST",
    body: formData,
    token,
  })
}

export async function extractResumeText(resumeId, token) {
  return apiRequest(
    `/resumes/${encodeURIComponent(resumeId)}/extract-text`,
    {
      method: "POST",
      token,
    }
  )
}

export async function getMyResumes(token) {
  return apiRequest("/resumes", {
    method: "GET",
    token,
  })
}

export async function deleteResume(resumeId, token) {
  return apiRequest(
    `/resumes/${encodeURIComponent(resumeId)}`,
    {
      method: "DELETE",
      token,
    }
  )
}

export async function getPreferences(token) {
  return apiRequest("/preferences", {
    method: "GET",
    token,
  })
}

export async function createPreferences(preferences, token) {
  return apiRequest("/preferences", {
    method: "POST",
    body: preferences,
    token,
  })
}

export async function updatePreferences(preferences, token) {
  return apiRequest("/preferences", {
    method: "PUT",
    body: preferences,
    token,
  })
}

// =========================================================
// JOBS - TAVILY SEARCH
// =========================================================

export async function searchJobs(jobTitle, location, token) {
  const cleanJobTitle = jobTitle?.trim() || ""
  const cleanLocation = location?.trim() || ""

  const queryParts = []

  if (cleanJobTitle) {
    queryParts.push(cleanJobTitle)
  }

  if (cleanLocation) {
    queryParts.push(`jobs in ${cleanLocation}`)
  } else {
    queryParts.push("jobs")
  }

  const params = new URLSearchParams({
    query: queryParts.join(" "),
  })

  if (cleanJobTitle) {
    params.set("job_title", cleanJobTitle)
  }

  if (cleanLocation) {
    params.set("location", cleanLocation)
  }

  return apiRequest(
    `/jobs/search/tavily?${params.toString()}`,
    {
      method: "GET",
      token,
    }
  )
}

export async function getMySearchResults(token) {
  const response = await apiRequest(
    "/jobs/search-results",
    {
      method: "GET",
      token,
    }
  )

  const results = Array.isArray(response?.results)
    ? response.results
    : []

  return {
    ...response,
    results: results.map((result) => ({
      ...result,
      search_result_id:
        result.search_result_id || result._id,
    })),
  }
}

// =========================================================
// JOBS - GET ALL SAVED JOBS
// =========================================================

export async function getJobs(token) {
  const response = await apiRequest(
    "/users/my-stored-jobs",
    {
      method: "GET",
      token,
    }
  )

  if (Array.isArray(response)) {
    return {
      message: "Stored jobs fetched successfully",
      total_jobs: response.length,
      jobs: response,
    }
  }

  if (!response || typeof response !== "object") {
    return {
      message: "Stored jobs fetched successfully",
      total_jobs: 0,
      jobs: [],
    }
  }

  const jobs = Array.isArray(response.jobs)
    ? response.jobs
    : []

  return {
    ...response,
    jobs,
    total_jobs: jobs.length,
  }
}

// =========================================================
// JOBS - NORMALIZE AND STORE
// =========================================================

export async function normalizeAndStoreJob(
  searchResultId,
  token
) {
  if (
    typeof searchResultId !== "string" ||
    !/^[a-fA-F0-9]{24}$/.test(searchResultId)
  ) {
    throw createApiError(
      "Invalid search result ID.",
      400
    )
  }

  const params = new URLSearchParams({
    search_result_id: searchResultId,
  })

  return apiRequest(
    `/jobs/normalize-and-store?${params.toString()}`,
    {
      method: "POST",
      token,
    }
  )
}

export async function saveJobAndTrack(searchResultId, token) {
  const saveResponse = await normalizeAndStoreJob(searchResultId, token)
  const jobId = saveResponse?.job_id

  if (
    saveResponse?.is_individual_job === false ||
    (saveResponse?.stored === false && !jobId)
  ) {
    return {
      saved: false,
      tracked: false,
      saveResponse,
    }
  }

  if (!jobId) {
    return {
      saved: true,
      tracked: false,
      saveResponse,
      trackingMessage:
        "Job saved, but the server did not return its ID for the tracker.",
    }
  }

  let resumes
  try {
    resumes = await getMyResumes(token)
  } catch (error) {
    return {
      saved: true,
      tracked: false,
      saveResponse,
      trackingError: error,
    }
  }

  const resumeList = Array.isArray(resumes)
    ? resumes
    : Array.isArray(resumes?.resumes)
      ? resumes.resumes
      : Array.isArray(resumes?.data)
        ? resumes.data
        : Array.isArray(resumes?.items)
          ? resumes.items
          : Array.isArray(resumes?.results)
            ? resumes.results
            : []
  const verifiedResume = resumeList.find(
    (resume) => resume?.resume_verified === true
  )
  const resumeId =
    verifiedResume?.resume_id || verifiedResume?._id || verifiedResume?.id

  if (!resumeId) {
    return {
      saved: true,
      tracked: false,
      saveResponse,
      trackingMessage:
        "Job saved, but no verified resume is available to add it to the tracker.",
    }
  }

  try {
    const trackingResponse = await prepareApplication(
      jobId,
      resumeId,
      token
    )
    return {
      saved: true,
      tracked: true,
      saveResponse,
      trackingResponse,
    }
  } catch (error) {
    return {
      saved: true,
      tracked: false,
      saveResponse,
      trackingError: error,
    }
  }
}

export async function normalizeAndStoreJobById(
  searchResultId,
  token
) {
  if (
    typeof searchResultId !== "string" ||
    !/^[a-fA-F0-9]{24}$/.test(searchResultId)
  ) {
    throw createApiError(
      "Invalid search result ID.",
      400
    )
  }

  return apiRequest(
    `/jobs/normalize-and-store/${encodeURIComponent(searchResultId)}`,
    {
      method: "GET",
      token,
    }
  )
}

// =========================================================
// JOBS - GET ONE
// =========================================================

export async function getJob(jobId, token) {
  return apiRequest(
    `/jobs/${encodeURIComponent(jobId)}`,
    {
      method: "GET",
      token,
    }
  )
}

// =========================================================
// JOBS - MATCH JOB WITH RESUME
// =========================================================

export async function matchJobWithResume(
  jobId,
  resumeId,
  token
) {
  if (!jobId || !resumeId) {
    throw createApiError(
      "Job ID and resume ID are required.",
      400
    )
  }

  return apiRequest(
    `/jobs/match/${encodeURIComponent(jobId)}/${encodeURIComponent(resumeId)}`,
    {
      method: "GET",
      token,
      timeoutMs: 7 * 60 * 1000,
    }
  )
}

export async function tailorJobResume(
  jobId,
  resumeId,
  token
) {
  const params = new URLSearchParams({ resume_id: resumeId })

  return apiRequest(
    `/jobs/${encodeURIComponent(jobId)}/tailor-resume?${params.toString()}`,
    {
      method: "POST",
      token,
      timeoutMs: 7 * 60 * 1000,
    }
  )
}

export async function prepareApplication(
  jobId,
  resumeId,
  token
) {
  return apiRequest("/applications/prepare", {
    method: "POST",
    body: {
      job_id: jobId,
      resume_id: resumeId,
      cover_letter: "",
      application_answers: {},
      notes: "Added to the application tracker for user review.",
      requires_user_review: true,
      approved: false,
    },
    token,
  })
}

// =========================================================
// APPLICATIONS
// =========================================================

export async function getApplications(token) {
  return apiRequest("/applications", {
    method: "GET",
    token,
  })
}

export async function deleteApplication(applicationId, token) {
  return apiRequest(
    `/applications/${encodeURIComponent(applicationId)}`,
    {
      method: "DELETE",
      token,
    }
  )
}

export async function getJobMatches(token) {
  return apiRequest("/jobs/matches", {
    method: "GET",
    token,
  })
}

export async function inspectApplication(applicationId, token) {
  return apiRequest(
    `/applications/${encodeURIComponent(applicationId)}/inspect`,
    {
      method: "POST",
      token,
    }
  )
}

export async function mapApplicationFields(applicationId, token) {
  return apiRequest(
    `/applications/${encodeURIComponent(applicationId)}/map-fields`,
    {
      method: "POST",
      token,
    }
  )
}

export async function updateApplicationStatus(
  applicationId,
  status,
  token
) {
  const params = new URLSearchParams({ status })

  return apiRequest(
    `/applications/${encodeURIComponent(applicationId)}/status?${params.toString()}`,
    {
      method: "PATCH",
      token,
    }
  )
}

export async function approveApplication(
  applicationId,
  token
) {
  return apiRequest(
    `/applications/${encodeURIComponent(applicationId)}/approve`,
    {
      method: "POST",
      token,
    }
  )
}

export async function checkApplicationSubmissionGate(
  applicationId,
  token
) {
  return apiRequest(
    `/applications/${encodeURIComponent(applicationId)}/submit-gate`,
    {
      method: "POST",
      token,
    }
  )
}

// =========================================================
// GENERIC API EXPORT
// =========================================================

export { apiRequest }