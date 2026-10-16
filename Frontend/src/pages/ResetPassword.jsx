import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { resetPassword } from "../services/api"

function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get("token") || ""

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")

    if (password.length < 8) {
      setError("Choose a password with at least 8 characters.")
      return
    }

    if (new TextEncoder().encode(password).length > 72) {
      setError("Password must be no more than 72 UTF-8 bytes.")
      return
    }

    if (password !== confirmPassword) {
      setError("The passwords do not match.")
      return
    }

    setIsLoading(true)

    try {
      await resetPassword(token, password)
      navigate("/login", {
        replace: true,
        state: {
          message: "Password reset. You can now log in with your new password.",
        },
      })
    } catch (requestError) {
      setError(
        requestError?.message ||
          "Unable to reset your password. Request a new reset link and try again."
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="flex min-h-dvh items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-100 px-4 py-10 dark:from-gray-950 dark:via-gray-950 dark:to-blue-950/40 sm:px-6">
      <section className="w-full max-w-md rounded-3xl border border-white/70 bg-white/95 p-6 shadow-xl shadow-blue-950/5 backdrop-blur dark:border-gray-700 dark:bg-gray-900/95 sm:p-9">
        <div className="mb-8 text-center">
          <p className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
            AI JobHunter
          </p>
          <h1 className="text-2xl font-bold tracking-tight text-gray-950 dark:text-white sm:text-3xl">
            Set a new password
          </h1>
          <p className="mt-3 text-sm leading-6 text-gray-600 dark:text-gray-400">
            Use at least 8 characters. You&apos;ll need to log in again after
            changing your password.
          </p>
        </div>

        {!token ? (
          <div className="space-y-5">
            <p
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-5 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
            >
              This reset link is missing its token. Request a new one to
              continue.
            </p>
            <Link
              to="/forgot-password"
              className="inline-flex w-full justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500/25"
            >
              Request a new link
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="new-password"
                className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                New password
              </label>
              <input
                id="new-password"
                name="new-password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value)
                  setError("")
                }}
                disabled={isLoading}
                className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              />
            </div>

            <div>
              <label
                htmlFor="confirm-password"
                className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Confirm new password
              </label>
              <input
                id="confirm-password"
                name="confirm-password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
                value={confirmPassword}
                onChange={(event) => {
                  setConfirmPassword(event.target.value)
                  setError("")
                }}
                disabled={isLoading}
                className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              />
            </div>

            {error && (
              <p
                role="alert"
                className="break-words rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-5 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500/25 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Updating..." : "Update password"}
            </button>
          </form>
        )}

        <p className="mt-7 text-center text-sm text-gray-600 dark:text-gray-400">
          <Link
            to="/login"
            className="font-semibold text-blue-600 hover:underline dark:text-blue-400"
          >
            Back to login
          </Link>
        </p>
      </section>
    </main>
  )
}

export default ResetPassword
