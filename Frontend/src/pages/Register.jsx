import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import {
  loginUser,
  registerUser,
} from "../services/api"

function Register() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [message, setMessage] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()

    setMessage("")

    const cleanName = name.trim()
    const cleanEmail = email.trim().toLowerCase()

    if (!cleanName || !cleanEmail || !password) {
      setMessage("Please fill in all fields.")
      return
    }

    setIsLoading(true)

    try {
      // Step 1: Create the account.
      await registerUser(
        cleanName,
        cleanEmail,
        password
      )

      // Step 2: Automatically login with the
      // newly created account.
      const loginData = await loginUser(
        cleanEmail,
        password
      )

      if (!loginData?.access_token) {
        setMessage(
          "Account created, but automatic login failed. Please login manually."
        )
        return
      }

      // Step 3: Save token in AuthContext.
      login(
        loginData.access_token,
        {
          name: cleanName,
          email: cleanEmail,
        }
      )

      // Step 4: Go directly to dashboard.
      navigate("/", { replace: true })
    } catch (error) {
      if (error?.status === 409) {
        setMessage(
          "An account with this email already exists. Please login."
        )
      } else if (error?.status === 401) {
        setMessage(
          "Account was created, but automatic login was rejected. Please login manually."
        )
      } else if (error?.message) {
        setMessage(error.message)
      } else {
        setMessage(
          "Unable to connect to the backend. Please make sure FastAPI is running."
        )
      }
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
            Create Account
          </h1>

          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Start your AI-powered job search
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-5"
        >

          {/* Name */}
          <div>
            <label
              htmlFor="name"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Name
            </label>

            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                setMessage("")
              }}
              placeholder="Your name"
              disabled={isLoading}
              className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-900 dark:disabled:bg-gray-800"
            />
          </div>

          {/* Email */}
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Email
            </label>

            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value)
                setMessage("")
              }}
              placeholder="you@example.com"
              disabled={isLoading}
              className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-900 dark:disabled:bg-gray-800"
            />
          </div>

          {/* Password */}
          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Password
            </label>

            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setMessage("")
              }}
              placeholder="Create a password"
              disabled={isLoading}
              className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-900 dark:disabled:bg-gray-800"
            />
          </div>

          {/* Message */}
          {message && (
            <div
              role="alert"
              className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300"
            >
              {message}
            </div>
          )}

          {/* Register */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500/25 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading
              ? "Creating account..."
              : "Create Account"}
          </button>

          {/* Login */}
          <button
            type="button"
            onClick={() => navigate("/login")}
            disabled={isLoading}
            className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            Already have an account? Login
          </button>

        </form>
      </section>
    </main>
  )
}

export default Register