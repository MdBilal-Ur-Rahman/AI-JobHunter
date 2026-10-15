
import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import {
  uploadResume,
  extractResumeText,
  getMyResumes,
  deleteResume,
} from "../services/api"

function Resume() {
  const fileInputRef = useRef(null)
  const navigate = useNavigate()
  const { token } = useAuth()

  const [selectedFile, setSelectedFile] =
    useState(null)

  const [message, setMessage] =
    useState("")

  const [error, setError] =
    useState("")

  const [isUploading, setIsUploading] =
    useState(false)

  const [isExtracting, setIsExtracting] =
    useState(false)

  const [isLoadingResumes, setIsLoadingResumes] =
    useState(true)

  const [deletingResumeId, setDeletingResumeId] =
    useState(null)

  const [resumeResult, setResumeResult] =
    useState(null)

  const [resumes, setResumes] =
    useState([])

  const loadResumes = useCallback(async () => {
    if (!token) {
      setIsLoadingResumes(false)
      return
    }

    try {
      setIsLoadingResumes(true)
      setError("")

      const data = await getMyResumes(token)

      setResumes(
        Array.isArray(data) ? data : []
      )
    } catch (err) {
      setError(
        err?.message ||
          "Failed to load your resumes."
      )
    } finally {
      setIsLoadingResumes(false)
    }
  }, [token])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadResumes()
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [loadResumes])

  function handleBackToDashboard() {
    navigate("/")
  }

  function handleFileChange(event) {
    const file =
      event.target.files?.[0]

    setMessage("")
    setError("")
    setResumeResult(null)

    if (!file) {
      setSelectedFile(null)
      return
    }

    const allowedTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    const isValidType =
      allowedTypes.includes(file.type)

    if (!isValidType) {
      setSelectedFile(null)
      setError(
        "Please select a PDF or DOCX file."
      )
      return
    }

    if (file.size === 0) {
      setSelectedFile(null)
      setError(
        "Resume file cannot be empty."
      )
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setSelectedFile(null)
      setError(
        "Resume file size must be less than 5 MB."
      )
      return
    }

    setSelectedFile(file)
  }

  function handleChooseFile() {
    fileInputRef.current?.click()
  }

  async function handleUpload(event) {
    event.preventDefault()

    setMessage("")
    setError("")
    setResumeResult(null)

    if (!selectedFile) {
      setError(
        "Please select a resume first."
      )
      return
    }

    if (!token) {
      setError(
        "Your session has expired. Please log in again."
      )
      return
    }

    if (resumes.length >= 3) {
      setError(
        "Maximum 3 resumes are allowed per user."
      )
      return
    }

    try {
      setIsUploading(true)

      const uploadData =
        await uploadResume(
          selectedFile,
          token
        )

      setIsUploading(false)

      setMessage(
        "Resume uploaded. Extracting and verifying text..."
      )

      if (!uploadData?.resume_id) {
        throw new Error(
          "Resume uploaded, but no resume ID was returned."
        )
      }

      setIsExtracting(true)

      const extractionData =
        await extractResumeText(
          uploadData.resume_id,
          token
        )

      setIsExtracting(false)

      setResumeResult({
        resume_id:
          uploadData.resume_id,

        filename:
          uploadData.filename ||
          selectedFile.name,

        file_size:
          uploadData.file_size ||
          selectedFile.size,

        text_length:
          extractionData?.text_length || 0,

        resume_verified:
          Boolean(
            extractionData?.resume_verified
          ),

        resume_source:
          extractionData?.resume_source ||
          "",
      })

      if (
        extractionData?.resume_verified
      ) {
        setMessage(
          "Resume uploaded, extracted, and verified successfully."
        )
      } else {
        setMessage(
          "Resume uploaded and text extracted, but the resume could not be verified."
        )
      }

      setSelectedFile(null)

      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }

      await loadResumes()
    } catch (err) {
      setIsUploading(false)
      setIsExtracting(false)

      setError(
        err?.message ||
          "Failed to process resume."
      )
    }
  }

  async function handleDeleteResume(
    resumeId,
    filename
  ) {
    if (!token) {
      setError(
        "Your session has expired. Please log in again."
      )
      return
    }

    const confirmed =
      window.confirm(
        `Are you sure you want to delete "${filename || "this resume"}"?`
      )

    if (!confirmed) {
      return
    }

    try {
      setDeletingResumeId(resumeId)
      setError("")
      setMessage("")

      await deleteResume(
        resumeId,
        token
      )

      setMessage(
        "Resume deleted successfully."
      )

      setResumes((currentResumes) =>
        currentResumes.filter(
          (resume) =>
            resume._id !== resumeId
        )
      )

      if (
        resumeResult?.resume_id ===
        resumeId
      ) {
        setResumeResult(null)
      }
    } catch (err) {
      setError(
        err?.message ||
          "Failed to delete resume."
      )
    } finally {
      setDeletingResumeId(null)
    }
  }

  const isProcessing =
    isUploading || isExtracting

  function formatDate(value) {
    if (!value) {
      return "Date not available"
    }

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) {
      return "Date not available"
    }

    return date.toLocaleDateString(
      undefined,
      {
        day: "numeric",
        month: "short",
        year: "numeric",
      }
    )
  }

  function getVerificationStatus(
    resume
  ) {
    if (resume?.resume_verified) {
      return "Verified"
    }

    if (resume?.extracted_text) {
      return "Not Verified"
    }

    return "Not Processed"
  }

  function getVerificationClass(
    resume
  ) {
    if (resume?.resume_verified) {
      return "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
    }

    if (resume?.extracted_text) {
      return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
    }

    return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="p-4 sm:p-6 lg:p-8">
        <div className="mx-auto w-full max-w-5xl">

          {/* PAGE HEADER */}
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">
                Resume
              </h1>

              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 sm:text-base">
                Upload and verify your resume for job matching.
              </p>
            </div>

            {/* BACK TO DASHBOARD */}
            <button
              type="button"
              onClick={handleBackToDashboard}
              className="w-full rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:w-auto dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
            >
              ← Back to Dashboard
            </button>
          </div>

          {/* RESUME STATUS */}
          <section className="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Resume Processing
                </h2>

                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Your resume will be extracted and verified after upload.
                </p>
              </div>

              <span className="w-fit rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                {resumes.length} / 3 resumes
              </span>
            </div>
          </section>

          {/* UPLOAD */}
          <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
            <div className="mb-5">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Upload Resume
              </h2>

              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Upload your latest resume in PDF or DOCX format.
              </p>
            </div>

            <form onSubmit={handleUpload}>
              <div className="rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 p-6 text-center dark:border-gray-600 dark:bg-gray-800 sm:p-10">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-xl dark:bg-blue-900/40">
                  📄
                </div>

                <h3 className="mt-4 text-base font-semibold text-gray-900 dark:text-white">
                  Select your resume
                </h3>

                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  PDF or DOCX files only · Maximum 5 MB
                </p>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={handleFileChange}
                  className="hidden"
                />

                <button
                  type="button"
                  onClick={handleChooseFile}
                  disabled={isProcessing}
                  className="mt-5 rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
                >
                  Choose File
                </button>

                {selectedFile && (
                  <div className="mx-auto mt-5 max-w-md rounded-lg bg-white px-4 py-3 text-left shadow-sm dark:bg-gray-900">
                    <p className="truncate text-sm font-medium text-gray-900 dark:text-white">
                      {selectedFile.name}
                    </p>

                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      {(
                        selectedFile.size /
                        1024 /
                        1024
                      ).toFixed(2)}{" "}
                      MB
                    </p>
                  </div>
                )}
              </div>

              {message && (
                <div
                  className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-300"
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

              {isProcessing && (
                <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-300">
                  {isUploading
                    ? "Uploading resume..."
                    : "Extracting and verifying resume text..."}
                </div>
              )}

              <div className="mt-5 flex justify-end">
                <button
                  type="submit"
                  disabled={
                    !selectedFile ||
                    isProcessing ||
                    resumes.length >= 3
                  }
                  className="w-full rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-offset-gray-900 sm:w-auto"
                >
                  {isUploading
                    ? "Uploading..."
                    : isExtracting
                      ? "Processing..."
                      : resumes.length >= 3
                        ? "Maximum 3 Resumes Reached"
                        : "Upload & Verify Resume"}
                </button>
              </div>
            </form>
          </section>

          {/* SAVED RESUMES */}
          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
            <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Your Resumes
                </h2>

                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Resumes currently saved in your account.
                </p>
              </div>

              <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                {resumes.length} of 3
              </span>
            </div>

            {isLoadingResumes ? (
              <div className="rounded-lg bg-gray-50 p-5 text-center text-sm text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                Loading your resumes...
              </div>
            ) : resumes.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center dark:border-gray-600">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  No resumes uploaded yet.
                </p>

                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Upload your first resume using the section above.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {resumes.map((resume) => (
                  <div
                    key={resume._id}
                    className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

                      {/* RESUME INFO */}
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-gray-900 dark:text-white">
                          {resume.filename ||
                            "Unnamed Resume"}
                        </p>

                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
                          <span>
                            Uploaded:{" "}
                            {formatDate(
                              resume.created_at
                            )}
                          </span>

                          {resume.file_size && (
                            <span>
                              Size:{" "}
                              {(
                                resume.file_size /
                                1024 /
                                1024
                              ).toFixed(2)}{" "}
                              MB
                            </span>
                          )}

                          {resume.text_length && (
                            <span>
                              Text:{" "}
                              {Number(
                                resume.text_length
                              ).toLocaleString()}{" "}
                              chars
                            </span>
                          )}
                        </div>
                      </div>

                      {/* STATUS + DELETE */}
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-medium ${getVerificationClass(
                            resume
                          )}`}
                        >
                          {getVerificationStatus(
                            resume
                          )}
                        </span>

                        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                          {resume.text_extracted_at
                            ? "Text Extracted"
                            : "Text Pending"}
                        </span>

                        <button
                          type="button"
                          onClick={() =>
                            handleDeleteResume(
                              resume._id,
                              resume.filename
                            )
                          }
                          disabled={
                            deletingResumeId ===
                            resume._id
                          }
                          className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950/30"
                        >
                          {deletingResumeId ===
                          resume._id
                            ? "Deleting..."
                            : "Delete Resume"}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* LATEST PROCESSING RESULT */}
          {resumeResult && (
            <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
              <div className="mb-5">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Latest Processing Result
                </h2>

                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Backend extraction and verification result.
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    File
                  </p>

                  <p className="mt-1 truncate text-sm font-semibold text-gray-900 dark:text-white">
                    {resumeResult.filename}
                  </p>
                </div>

                <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Extracted Text
                  </p>

                  <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
                    {resumeResult.text_length.toLocaleString()}{" "}
                    characters
                  </p>
                </div>

                <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Verification
                  </p>

                  <p
                    className={`mt-1 text-sm font-semibold ${
                      resumeResult.resume_verified
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {resumeResult.resume_verified
                      ? "Verified"
                      : "Not Verified"}
                  </p>
                </div>

                <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Verification Source
                  </p>

                  <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
                    {resumeResult.resume_source ||
                      "Not available"}
                  </p>
                </div>
              </div>
            </section>
          )}

        </div>
      </div>
    </div>
  )
}

export default Resume
