import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import { useAuth } from "../context/AuthContext"
import {
  createPreferences,
  getPreferences,
  updatePreferences,
} from "../services/api"

const INITIAL_PREFERENCES = {
  job_titles: "",
  locations: "",
  skills: "",
  min_experience: "",
  work_mode: "",
  employment_type: "",
}

function toList(value) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function Preferences() {
  const navigate = useNavigate()
  const { token } = useAuth()
  const [values, setValues] = useState(INITIAL_PREFERENCES)
  const [hasPreferences, setHasPreferences] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  useEffect(() => {
    let active = true

    if (!token) {
      return () => {
        active = false
      }
    }

    async function loadPreferences() {
      try {
        const preferences = await getPreferences(token)

        if (!active) {
          return
        }

        setValues({
          job_titles: (preferences.job_titles || []).join(", "),
          locations: (preferences.locations || []).join(", "),
          skills: (preferences.skills || []).join(", "),
          min_experience: preferences.min_experience || "",
          work_mode: preferences.work_mode || "",
          employment_type: preferences.employment_type || "",
        })
        setHasPreferences(true)
      } catch (loadError) {
        if (loadError?.status !== 404 && active) {
          setError(
            loadError?.message ||
              "Failed to load your job preferences."
          )
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadPreferences()

    return () => {
      active = false
    }
  }, [token])

  function handleChange(event) {
    const { name, value } = event.target
    setValues((current) => ({
      ...current,
      [name]: value,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    setMessage("")

    const preferences = {
      job_titles: toList(values.job_titles),
      locations: toList(values.locations),
      skills: toList(values.skills),
      min_experience: values.min_experience.trim(),
      work_mode: values.work_mode.trim(),
      employment_type: values.employment_type.trim(),
    }

    if (!preferences.job_titles.length || !preferences.locations.length) {
      setError("At least one job title and one location are required.")
      return
    }

    if (!token) {
      setError("Your session has expired. Please log in again.")
      return
    }

    setSaving(true)

    try {
      if (hasPreferences) {
        await updatePreferences(preferences, token)
      } else {
        await createPreferences(preferences, token)
        setHasPreferences(true)
      }

      setMessage("Job preferences saved successfully.")
    } catch (saveError) {
      setError(
        saveError?.message ||
          "Failed to save your job preferences."
      )
    } finally {
      setSaving(false)
    }
  }

  const textFields = [
    {
      name: "job_titles",
      label: "Target job titles",
      placeholder: "Frontend Developer, React Developer",
    },
    {
      name: "locations",
      label: "Preferred locations",
      placeholder: "Hyderabad, Remote",
    },
    {
      name: "skills",
      label: "Skills",
      placeholder: "React, JavaScript, APIs",
    },
    {
      name: "min_experience",
      label: "Minimum experience",
      placeholder: "e.g. 2 years",
    },
    {
      name: "work_mode",
      label: "Work mode",
      placeholder: "Remote, hybrid, or onsite",
    },
    {
      name: "employment_type",
      label: "Employment type",
      placeholder: "Full-time, contract, or internship",
    },
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar />
      <div className="min-h-screen md:ml-64">
        <Header />
        <main className="p-4 sm:p-6 lg:p-8">
          <section className="mx-auto w-full max-w-3xl rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-6">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Job Preferences
                </h1>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  Set target roles and locations to guide job discovery.
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate("/")}
                className="w-full rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:w-auto dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
              >
                ← Back to Dashboard
              </button>
            </div>

            {loading ? (
              <p className="py-8 text-sm text-gray-500 dark:text-gray-400">
                Loading preferences...
              </p>
            ) : (
              <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
                {textFields.map((field) => (
                  <label
                    key={field.name}
                    className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                  >
                    {field.label}
                    <input
                      name={field.name}
                      value={values[field.name]}
                      onChange={handleChange}
                      placeholder={field.placeholder}
                      required={
                        field.name === "job_titles" ||
                        field.name === "locations"
                      }
                      className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                    />
                    {["job_titles", "locations", "skills"].includes(
                      field.name
                    ) && (
                      <span className="mt-1 block text-xs font-normal text-gray-500 dark:text-gray-400">
                        Separate values with commas.
                      </span>
                    )}
                  </label>
                ))}

                {error && (
                  <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300" role="alert">
                    {error}
                  </p>
                )}
                {message && (
                  <p className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-300" role="status">
                    {message}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Preferences"}
                </button>
              </form>
            )}
          </section>
        </main>
      </div>
    </div>
  )
}

export default Preferences
