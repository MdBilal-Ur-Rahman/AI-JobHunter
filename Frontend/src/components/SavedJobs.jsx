
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  getJobs,
  getMyResumes,
  matchJobWithResume,
  prepareApplication,
  tailorJobResume,
} from "../services/api";

/* Get job ID */
function getJobId(job) {
  return String(job?.job_id || job?._id || job?.id || "");
}

/* Get resume ID */
function getResumeId(resume) {
  return String(
    resume?.resume_id || resume?._id || resume?.id || ""
  );
}

/* Extract API error message */
function getErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    "Something went wrong. Please try again."
  );
}

/* Extract jobs from supported API response formats */
function extractJobs(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (!data || typeof data !== "object") {
    return [];
  }

  const possibleKeys = [
    "jobs",
    "saved_jobs",
    "results",
    "data",
    "items",
  ];

  for (const key of possibleKeys) {
    if (Array.isArray(data[key])) {
      return data[key];
    }
  }

  return [];
}

/* Extract resumes from supported API response formats */
function extractResumes(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (!data || typeof data !== "object") {
    return [];
  }

  const possibleKeys = [
    "resumes",
    "data",
    "items",
    "results",
  ];

  for (const key of possibleKeys) {
    if (Array.isArray(data[key])) {
      return data[key];
    }
  }

  return [];
}

function SavedJobs() {
  const { token } = useAuth();

  const [jobs, setJobs] = useState([]);
  const [resumes, setResumes] = useState([]);
  const [selectedResumes, setSelectedResumes] = useState({});
  const [matchResults, setMatchResults] = useState({});
  const [matchingJobId, setMatchingJobId] = useState("");
  const [trackingJobId, setTrackingJobId] = useState("");
  const [trackingMessages, setTrackingMessages] = useState({});
  const [trackingErrors, setTrackingErrors] = useState({});
  const [tailoringJobId, setTailoringJobId] = useState("");
  const [tailoredDrafts, setTailoredDrafts] = useState({});
  const [tailoringErrors, setTailoringErrors] = useState({});

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [resumesLoading, setResumesLoading] = useState(true);

  const [error, setError] = useState("");
  const [resumeError, setResumeError] = useState("");
  const [matchErrors, setMatchErrors] = useState({});

  /* =========================
     LOAD SAVED JOBS
  ========================= */
  const loadJobs = useCallback(
    async ({ showLoading = false } = {}) => {
      if (!token) {
        setJobs([]);
        setLoading(false);
        setRefreshing(false);
        setError("Please log in to view your saved jobs.");
        return;
      }

      if (showLoading) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      try {
        setError("");

        const response = await getJobs(token);
        const savedJobs = extractJobs(response);

        console.log("SAVED JOBS API RESPONSE:", response);
        console.log("EXTRACTED SAVED JOBS:", savedJobs);

        setJobs(savedJobs);

        // Notify listeners that saved jobs were refreshed.
        // Dashboard statistics are intentionally not refreshed
        // by this event in the updated DashboardCards component.
        window.dispatchEvent(
          new CustomEvent("saved-jobs-updated", {
            detail: {
              total_jobs: savedJobs.length,
            },
          })
        );
      } catch (err) {
        console.error("Failed to load saved jobs:", err);

        // Keep the currently displayed jobs if refresh fails.
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [token]
  );

  /* =========================
     LOAD VERIFIED RESUMES
  ========================= */
  const loadResumes = useCallback(async () => {
    if (!token) {
      setResumes([]);
      setResumesLoading(false);
      setResumeError("");
      return;
    }

    try {
      setResumesLoading(true);
      setResumeError("");

      const response = await getMyResumes(token);
      const allResumes = extractResumes(response);

      const verifiedResumes = allResumes.filter(
        (resume) => resume?.resume_verified === true
      );

      console.log("VERIFIED RESUMES:", verifiedResumes);

      setResumes(verifiedResumes);

      setSelectedResumes((previous) => {
        const next = { ...previous };

        const defaultResumeStillExists = verifiedResumes.some(
          (resume) => getResumeId(resume) === next.default
        );

        if (!defaultResumeStillExists) {
          next.default = verifiedResumes.length
            ? getResumeId(verifiedResumes[0])
            : "";
        }

        verifiedResumes.forEach((resume) => {
          const resumeId = getResumeId(resume);

          if (resumeId && !next[resumeId]) {
            next[resumeId] = resumeId;
          }
        });

        return next;
      });
    } catch (err) {
      console.error("Failed to load resumes:", err);
      setResumeError(getErrorMessage(err));
    } finally {
      setResumesLoading(false);
    }
  }, [token]);

  /* =========================
     INITIAL LOAD
  ========================= */
  useEffect(() => {
    loadJobs({ showLoading: true });
    loadResumes();
  }, [loadJobs, loadResumes]);

  useEffect(() => {
    function handleJobsSearchCompleted() {
      loadJobs();
    }

    window.addEventListener(
      "jobs-search-completed",
      handleJobsSearchCompleted
    );

    return () => {
      window.removeEventListener(
        "jobs-search-completed",
        handleJobsSearchCompleted
      );
    };
  }, [loadJobs]);

  /* =========================
     MANUAL REFRESH
  ========================= */
  async function handleRefresh() {
    if (refreshing || resumesLoading) {
      return;
    }

    await Promise.all([
      loadJobs(),
      loadResumes(),
    ]);
  }

  /* =========================
     RESUME SELECTION
  ========================= */
  function handleResumeChange(jobId, resumeId) {
    setSelectedResumes((previous) => ({
      ...previous,
      [jobId]: resumeId,
    }));

    setMatchErrors((previous) => ({
      ...previous,
      [jobId]: "",
    }));
  }

  async function handleTrackApplication(job) {
    const jobId = getJobId(job);
    const resumeId =
      selectedResumes[jobId] ||
      selectedResumes.default ||
      "";

    if (!jobId || !resumeId || !token) {
      setTrackingErrors((previous) => ({
        ...previous,
        [jobId || "unknown"]:
          "Select a verified resume before tracking this job.",
      }));
      return;
    }

    try {
      setTrackingJobId(jobId);
      setTrackingMessages((previous) => ({
        ...previous,
        [jobId]: "",
      }));
      setTrackingErrors((previous) => ({
        ...previous,
        [jobId]: "",
      }));

      const response = await prepareApplication(
        jobId,
        resumeId,
        token
      );

      setTrackingMessages((previous) => ({
        ...previous,
        [jobId]:
          response?.message ||
          "Added to your application tracker for review.",
      }));
      window.dispatchEvent(new Event("applications-updated"));
      window.dispatchEvent(new Event("dashboard-summary-updated"));
    } catch (err) {
      console.error("Failed to track application:", err);
      setTrackingErrors((previous) => ({
        ...previous,
        [jobId]: getErrorMessage(err),
      }));
    } finally {
      setTrackingJobId("");
    }
  }

  async function handleTailorResume(job) {
    const jobId = getJobId(job);
    const resumeId =
      selectedResumes[jobId] ||
      selectedResumes.default ||
      "";

    if (!jobId || !resumeId || !token) {
      setTailoringErrors((previous) => ({
        ...previous,
        [jobId || "unknown"]:
          "Select a verified resume before creating a draft.",
      }));
      return;
    }

    try {
      setTailoringJobId(jobId);
      setTailoringErrors((previous) => ({
        ...previous,
        [jobId]: "",
      }));

      const response = await tailorJobResume(
        jobId,
        resumeId,
        token
      );

      setTailoredDrafts((previous) => ({
        ...previous,
        [jobId]: response?.result,
      }));
    } catch (err) {
      console.error("Resume draft generation failed:", err);
      setTailoringErrors((previous) => ({
        ...previous,
        [jobId]: getErrorMessage(err),
      }));
    } finally {
      setTailoringJobId("");
    }
  }

  /* =========================
     MATCH JOB WITH RESUME
  ========================= */
  async function handleMatchJob(job) {
    const jobId = getJobId(job);

    const resumeId =
      selectedResumes[jobId] ||
      selectedResumes.default ||
      "";

    if (!jobId) {
      setMatchErrors((previous) => ({
        ...previous,
        unknown: "Job ID nahi mila. API response check karein.",
      }));

      return;
    }

    if (!resumeId) {
      setMatchErrors((previous) => ({
        ...previous,
        [jobId]: "Pehle ek verified resume select karein.",
      }));

      return;
    }

    if (!token) {
      setMatchErrors((previous) => ({
        ...previous,
        [jobId]: "Session expire ho gaya. Dobara login karein.",
      }));

      return;
    }

    try {
      setMatchingJobId(jobId);

      setMatchErrors((previous) => ({
        ...previous,
        [jobId]: "",
      }));

      setMatchResults((previous) => ({
        ...previous,
        [jobId]: null,
      }));

      const response = await matchJobWithResume(
        jobId,
        resumeId,
        token
      );

      console.log("RESUME MATCH RESPONSE:", response);

      const result =
        response?.match_result ??
        response?.result ??
        response;

      setMatchResults((previous) => ({
        ...previous,
        [jobId]: result,
      }));

      window.dispatchEvent(
        new CustomEvent("job-match-updated", {
          detail: {
            job_id: jobId,
            resume_id: resumeId,
            result,
          },
        })
      );

      window.dispatchEvent(
        new Event("dashboard-summary-updated")
      );
    } catch (err) {
      console.error("Resume matching failed:", err);

      setMatchErrors((previous) => ({
        ...previous,
        [jobId]: getErrorMessage(err),
      }));
    } finally {
      setMatchingJobId("");
    }
  }

  /* =========================
     STYLES
  ========================= */
  const sectionClass =
    "my-6 w-full rounded-xl border border-gray-200 bg-white px-4 py-8 text-gray-900 shadow-sm sm:my-8 sm:px-6 sm:py-10 lg:px-8 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";

  const mutedTextClass =
    "text-gray-500 dark:text-gray-400";

  /* =========================
     INITIAL LOADING STATE
  ========================= */
  if (loading) {
    return (
      <section className={sectionClass}>
        <div className="py-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Saved Jobs
          </h2>

          <p
            className={`mt-3 text-sm ${mutedTextClass}`}
            role="status"
          >
            Saved jobs load ho rahi hain...
          </p>
        </div>
      </section>
    );
  }

  /* =========================
     MAIN UI
  ========================= */
  return (
    <section className={sectionClass}>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 sm:mb-8">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 sm:text-2xl">
            Saved Jobs
          </h2>

          <p className={`mt-2 text-sm ${mutedTextClass}`}>
            {jobs.length} saved{" "}
            {jobs.length === 1 ? "job" : "jobs"}
          </p>
        </div>

        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing || resumesLoading}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
        >
          {refreshing || resumesLoading ? (
            <>
              <span
                className="h-4 w-4 animate-spin rounded-full border-2 border-gray-400 border-t-transparent"
                aria-hidden="true"
              />
              Refreshing...
            </>
          ) : (
            "Refresh"
          )}
        </button>
      </div>

      {/* Saved jobs error */}
      {error && (
        <div
          role="alert"
          className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <p className="font-medium">
            Saved jobs refresh nahi ho saka.
          </p>

          <p className="mt-2">{error}</p>

          <button
            type="button"
            onClick={() => loadJobs()}
            disabled={refreshing}
            className="mt-3 rounded-lg border border-red-300 px-3 py-2 font-medium hover:bg-red-100 disabled:opacity-50 dark:border-red-700 dark:hover:bg-red-900"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Resume error */}
      {resumeError && (
        <div
          role="alert"
          className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300"
        >
          <p className="font-medium">
            Verified resumes load nahi ho sake.
          </p>

          <p className="mt-2">{resumeError}</p>

          <button
            type="button"
            onClick={loadResumes}
            disabled={resumesLoading}
            className="mt-3 rounded-lg border border-amber-300 px-3 py-2 font-medium hover:bg-amber-100 disabled:opacity-50 dark:border-amber-700 dark:hover:bg-amber-900"
          >
            Retry Resumes
          </button>
        </div>
      )}

      {/* Empty jobs state */}
      {!error && jobs.length === 0 && (
        <div className="my-4 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-10 text-center sm:py-12 dark:border-gray-700 dark:bg-gray-800">
          <h3 className="font-medium text-gray-800 dark:text-gray-100">
            No saved jobs yet
          </h3>

          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-gray-500 dark:text-gray-400">
            Job Search se jobs search karein. Agar jobs save
            karne ke baad bhi yahan nahi dikh rahi hain, toh
            backend API aur database mein saved jobs check karein.
          </p>

          <button
            type="button"
            onClick={() => loadJobs()}
            disabled={refreshing}
            className="mt-5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {refreshing ? "Loading..." : "Reload Jobs"}
          </button>
        </div>
      )}

      {/* Jobs list */}
      {jobs.length > 0 && (
        <div className="mt-6 space-y-5 sm:mt-8 sm:space-y-6">
          {jobs.map((job, index) => {
            const jobId = getJobId(job);

            const selectedResumeId =
              selectedResumes[jobId] ||
              selectedResumes.default ||
              "";

            const result = matchResults[jobId];

            return (
              <article
                key={jobId || `job-${index}`}
                className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-colors sm:p-6 dark:border-gray-700 dark:bg-gray-800"
              >
                {/* Job details */}
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <h3 className="break-words text-lg font-semibold text-gray-900 dark:text-gray-100 sm:text-xl">
                      {job?.title ||
                        job?.job_title ||
                        "Untitled job"}
                    </h3>

                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                      {job?.company ||
                        job?.company_name ||
                        "Company not specified"}
                    </p>

                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                      {job?.location || "Location not specified"}
                    </p>
                  </div>

                  {job?.employment_type &&
                    job.employment_type !== "Not specified" && (
                      <span className="shrink-0 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                        {job.employment_type}
                      </span>
                    )}
                </div>

                {/* Experience and salary */}
                <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
                  <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-900">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                      Experience
                    </p>

                    <p className="mt-2 text-sm text-gray-800 dark:text-gray-200">
                      {job?.experience_required ||
                        job?.experience ||
                        "Not specified"}
                    </p>
                  </div>

                  <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-900">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                      Salary
                    </p>

                    <p className="mt-2 text-sm text-gray-800 dark:text-gray-200">
                      {job?.salary || "Not specified"}
                    </p>
                  </div>
                </div>

                {/* Required skills */}
                {Array.isArray(job?.required_skills) &&
                  job.required_skills.length > 0 && (
                    <div className="mt-6">
                      <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                        Required Skills
                      </p>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {job.required_skills.map(
                          (skill, skillIndex) => (
                            <span
                              key={`${String(skill)}-${skillIndex}`}
                              className="rounded-full bg-gray-100 px-3 py-1.5 text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-200"
                            >
                              {typeof skill === "string"
                                ? skill
                                : skill?.name ||
                                  JSON.stringify(skill)}
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  )}

                {/* Original job link */}
                {job?.application_url &&
                  job.application_url !== "Not specified" && (
                    <div className="mt-5">
                      <a
                        href={job.application_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
                      >
                        View Original Job ↗
                      </a>
                    </div>
                  )}

                {/* Resume matching */}
                <div className="mt-6 border-t border-gray-200 pt-5 sm:mt-8 sm:pt-6 dark:border-gray-700">
                  <label
                    htmlFor={`resume-${jobId || index}`}
                    className="mb-3 block text-sm font-medium text-gray-700 dark:text-gray-200"
                  >
                    Select Verified Resume
                  </label>

                  {resumesLoading ? (
                    <p
                      className="text-sm text-gray-500 dark:text-gray-400"
                      role="status"
                    >
                      Resumes load ho rahe hain...
                    </p>
                  ) : resumes.length === 0 ? (
                    <p className="rounded-lg bg-amber-50 p-3 text-sm leading-6 text-amber-700 dark:bg-amber-950 dark:text-amber-400">
                      Koi verified resume nahi mila. Resume
                      section mein jaakar apna resume verify karein.
                    </p>
                  ) : (
                    <select
                      id={`resume-${jobId || index}`}
                      value={selectedResumeId}
                      onChange={(event) =>
                        handleResumeChange(
                          jobId,
                          event.target.value
                        )
                      }
                      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-3 text-sm text-gray-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                    >
                      <option value="">
                        Select a verified resume
                      </option>

                      {resumes.map((resume, resumeIndex) => {
                        const resumeId = getResumeId(resume);

                        return (
                          <option
                            key={resumeId || `resume-${resumeIndex}`}
                            value={resumeId}
                          >
                            {resume?.filename ||
                              resume?.file_name ||
                              resume?.name ||
                              `Resume ${resumeIndex + 1}`}
                          </option>
                        );
                      })}
                    </select>
                  )}

                  <button
                    type="button"
                    onClick={() => handleMatchJob(job)}
                    disabled={
                      !jobId ||
                      !selectedResumeId ||
                      resumesLoading ||
                      matchingJobId === jobId
                    }
                    className="mt-4 w-full rounded-lg bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                  >
                    {matchingJobId === jobId
                      ? "Matching..."
                      : "Match Resume"}
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTrackApplication(job)}
                    disabled={
                      !jobId ||
                      !selectedResumeId ||
                      resumesLoading ||
                      trackingJobId === jobId
                    }
                    className="mt-4 w-full rounded-lg border border-gray-300 px-5 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 sm:ml-2 sm:w-auto dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                  >
                    {trackingJobId === jobId
                      ? "Adding..."
                      : "Add to Application Tracker"}
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTailorResume(job)}
                    disabled={
                      !jobId ||
                      !selectedResumeId ||
                      resumesLoading ||
                      tailoringJobId === jobId
                    }
                    className="mt-4 w-full rounded-lg border border-purple-300 px-5 py-3 text-sm font-medium text-purple-700 transition hover:bg-purple-50 disabled:cursor-not-allowed disabled:opacity-50 sm:ml-2 sm:w-auto dark:border-purple-700 dark:text-purple-300 dark:hover:bg-purple-950"
                  >
                    {tailoringJobId === jobId
                      ? "Preparing draft..."
                      : "Create Resume Draft"}
                  </button>

                  {tailoringErrors[jobId] && (
                    <p
                      className="mt-3 text-sm text-red-700 dark:text-red-400"
                      role="alert"
                    >
                      {tailoringErrors[jobId]}
                    </p>
                  )}

                  {tailoredDrafts[jobId] && (
                    <div className="mt-4 rounded-lg border border-purple-200 bg-purple-50 p-4 dark:border-purple-900 dark:bg-purple-950/30">
                      <h4 className="font-semibold text-purple-900 dark:text-purple-200">
                        AI Resume Draft — Review Required
                      </h4>
                      <p className="mt-2 text-xs text-purple-800 dark:text-purple-300">
                        {tailoredDrafts[jobId].safety_note}
                      </p>
                      <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs leading-6 text-gray-800 dark:text-gray-200">
                        {tailoredDrafts[jobId].tailored_resume}
                      </pre>
                      {Array.isArray(tailoredDrafts[jobId].changes) &&
                        tailoredDrafts[jobId].changes.length > 0 && (
                          <ul className="mt-3 list-inside list-disc text-xs text-gray-700 dark:text-gray-300">
                            {tailoredDrafts[jobId].changes.map(
                              (change, changeIndex) => (
                                <li key={`${change}-${changeIndex}`}>
                                  {change}
                                </li>
                              )
                            )}
                          </ul>
                        )}
                    </div>
                  )}

                  {trackingMessages[jobId] && (
                    <p
                      className="mt-3 text-sm text-green-700 dark:text-green-400"
                      role="status"
                    >
                      {trackingMessages[jobId]}
                    </p>
                  )}

                  {(trackingErrors[jobId] ||
                    trackingErrors.unknown) && (
                    <p
                      className="mt-3 text-sm text-red-700 dark:text-red-400"
                      role="alert"
                    >
                      {trackingErrors[jobId] ||
                        trackingErrors.unknown}
                    </p>
                  )}

                  {/* Matching error */}
                  {(matchErrors[jobId] || matchErrors.unknown) && (
                    <p
                      role="alert"
                      className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm leading-6 text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
                    >
                      {matchErrors[jobId] || matchErrors.unknown}
                    </p>
                  )}

                  {/* Match result */}
                  {result && (
                    <div className="mt-5 rounded-lg border border-green-200 bg-green-50 p-4 sm:p-5 dark:border-green-900 dark:bg-green-950">
                      <h4 className="font-semibold text-green-900 dark:text-green-300">
                        Resume Match Result
                      </h4>

                      {typeof result === "string" ? (
                        <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-green-900 dark:text-green-200">
                          {result}
                        </p>
                      ) : (
                        <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-6 text-green-900 dark:text-green-200">
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div aria-hidden="true" className="h-2 sm:h-4" />
    </section>
  );
}

export default SavedJobs;
