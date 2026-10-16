import { useState } from "react"
import { Link } from "react-router-dom"
import { requestPasswordReset } from "../services/api"

function ForgotPassword() {
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setMessage("")
    setError("")
    setIsLoading(true)

    try {
      const result = await requestPasswordReset(email)
      setMessage(
        result.message ||
          "If an account exists for that email, a reset link will be sent."
      )
    } catch (requestError) {
      setError(
        requestError?.message ||
          "Unable to request a reset link right now. Please try again."
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
            Forgot your password?
          </h1>
          <p className="mx-auto mt-3 max-w-sm text-sm leading-6 text-gray-600 dark:text-gray-400">
            Enter the email address linked to your account. We&apos;ll send a
            one-time link if an account matches.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Email address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => {
                setEmail(event.target.value)
                setMessage("")
                setError("")
              }}
              placeholder="you@example.com"
              disabled={isLoading}
              className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500"
            />
          </div>

          {message && (
            <p
              role="status"
              className="break-words rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm leading-5 text-green-800 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300"
            >
              {message}
            </p>
          )}

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
            {isLoading ? "Sending..." : "Send reset link"}
          </button>
        </form>

        <p className="mt-7 text-center text-sm text-gray-600 dark:text-gray-400">
          Remembered your password?{" "}
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

export default ForgotPassword
