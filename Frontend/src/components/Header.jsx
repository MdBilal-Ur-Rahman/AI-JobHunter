
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import ThemeToggle from "./ThemeToggle"
import { useAuth } from "../context/AuthContext"

function Header() {
  const navigate = useNavigate()
  const { logout, user } = useAuth()

  const [isLoggingOut, setIsLoggingOut] = useState(false)

  async function handleLogout() {
    if (isLoggingOut) {
      return
    }

    setIsLoggingOut(true)

    try {
      // AuthContext backend logout + local token clear
      await logout()
    } catch (error) {
      console.error("Logout failed:", error)
    } finally {
      navigate("/login", { replace: true })
      setIsLoggingOut(false)
    }
  }

  const displayName = user?.name || "User"
  const displayEmail = user?.email || "Job Seeker"

  return (
    <header className="w-full border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <div className="flex flex-col gap-4 p-4 sm:p-5 md:flex-row md:items-center md:justify-between md:p-6">
        <div className="min-w-0">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">
            Welcome to AI JobHunter
          </h2>

          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 sm:text-base">
            Find jobs, match your resume, and manage applications.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 md:justify-end">
          <ThemeToggle />

          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-200 text-sm font-semibold text-gray-700 dark:bg-gray-700 dark:text-gray-200">
              {displayName.charAt(0).toUpperCase()}
            </div>

            <div className="min-w-0">
              <p className="max-w-32 truncate text-sm font-semibold text-gray-900 dark:text-white sm:max-w-48">
                {displayName}
              </p>

              <p className="max-w-40 truncate text-xs text-gray-500 dark:text-gray-400 sm:max-w-56">
                {displayEmail}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            {isLoggingOut ? "Logging out..." : "Logout"}
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
