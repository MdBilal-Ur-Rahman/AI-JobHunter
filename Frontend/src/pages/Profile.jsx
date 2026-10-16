import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import { useAuth } from "../context/AuthContext"
import { getCurrentUser, updateCurrentUser } from "../services/api"

function Profile() {
  const navigate = useNavigate()
  const { token, user, setUser } = useAuth()
  const [name, setName] = useState(user?.name || "")
  const [email, setEmail] = useState(user?.email || "")
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  useEffect(() => {
    let active = true

    async function loadProfile() {
      if (!token) {
        setIsLoading(false)
        return
      }

      try {
        const profile = await getCurrentUser(token)
        if (active) {
          setName(profile.name || "")
          setEmail(profile.email || "")
          setUser(profile)
        }
      } catch (loadError) {
        if (active) {
          setError(
            loadError?.message || "Failed to load your profile."
          )
        }
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    loadProfile()

    return () => {
      active = false
    }
  }, [token, setUser])

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    setMessage("")

    const cleanName = name.trim()
    const cleanEmail = email.trim().toLowerCase()

    if (!cleanName || !cleanEmail) {
      setError("Name and email are required.")
      return
    }

    if (!token) {
      setError("Your session has expired. Please log in again.")
      return
    }

    setIsSaving(true)
    try {
      const updateResponse = await updateCurrentUser(
        { name: cleanName, email: cleanEmail },
        token
      )
      const updatedProfile = await getCurrentUser(token)

      if (
        updatedProfile.name !== cleanName ||
        updatedProfile.email !== cleanEmail
      ) {
        throw new Error(
          "The server accepted the update but returned different profile details. Please refresh and try again."
        )
      }

      setName(updatedProfile.name)
      setEmail(updatedProfile.email)
      setUser(updatedProfile)
      setMessage(
        updateResponse?.message || "Profile updated successfully."
      )
    } catch (saveError) {
      setError(
        saveError?.message || "Failed to update your profile."
      )
    } finally {
      setIsSaving(false)
    }
  }

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
                  Profile
                </h1>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  Update the name and email associated with your account.
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

            {isLoading ? (
              <p className="py-8 text-sm text-gray-500 dark:text-gray-400">
                Loading profile...
              </p>
            ) : (
              <form className="space-y-5" onSubmit={handleSubmit}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Name
                  <input
                    name="name"
                    type="text"
                    autoComplete="name"
                    required
                    maxLength={120}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>

                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Email
                  <input
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    maxLength={254}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  />
                </label>

                {error && (
                  <p
                    className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300"
                    role="alert"
                  >
                    {error}
                  </p>
                )}
                {message && (
                  <p
                    className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-300"
                    role="status"
                  >
                    {message}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={isSaving || isLoading}
                  className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSaving ? "Saving..." : "Save Profile"}
                </button>
              </form>
            )}
          </section>
        </main>
      </div>
    </div>
  )
}

export default Profile
