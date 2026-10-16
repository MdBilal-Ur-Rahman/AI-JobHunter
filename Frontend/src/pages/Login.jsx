
import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { loginUser } from "../services/api"

function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, token } = useAuth()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [message, setMessage] = useState(location.state?.message || "")
  const [isLoading, setIsLoading] = useState(false)
  const isSuccessMessage =
    Boolean(location.state?.message) && message === location.state.message

  // Prevent an already logged-in user from logging in again.
  useEffect(() => {
    if (token) {
      navigate("/", { replace: true })
    }
  }, [token, navigate])

  async function handleSubmit(event) {
    event.preventDefault()

    setMessage("")

    // Do not send another login request if the user is already logged in.
    if (token) {
      setMessage(
        "You are already logged in. Please logout first before logging in again."
      )
      return
    }

    const cleanEmail = email.trim().toLowerCase()

    if (!cleanEmail || !password) {
      setMessage("Please enter your email and password.")
      return
    }

    setIsLoading(true)

    try {
      const data = await loginUser(
        cleanEmail,
        password
      )

      // Backend did not return an access token.
      if (!data || !data.access_token) {
        setMessage(
          data?.message ||
            "Login failed. Please check your email and password and try again."
        )
        return
      }

      // Save the token in AuthContext after successful login.
      login(data.access_token)

      navigate("/", { replace: true })
    } catch (error) {
      const status = error?.status

      if (status === 401) {
        setMessage(
          "Email or password is incorrect. Please check your credentials and try again."
        )
      } else if (status === 409) {
        setMessage(
          "This account is already logged in. Please logout from the current session before logging in again."
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
            Welcome back
          </h1>

          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Login to your job hunting assistant
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
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
              disabled={isLoading || Boolean(token)}
              className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-900 dark:disabled:bg-gray-800"
            />
          </div>

          <div>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Password
              </label>
              <Link
                to="/forgot-password"
                className="text-sm font-semibold text-blue-600 hover:underline dark:text-blue-400"
              >
                Forgot password?
              </Link>
            </div>

            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setMessage("")
              }}
              placeholder="Enter your password"
              disabled={isLoading || Boolean(token)}
              className="min-w-0 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-900 dark:disabled:bg-gray-800"
            />
          </div>

          {message && (
            <div
              role={isSuccessMessage ? "status" : "alert"}
              className={`break-words rounded-xl border px-4 py-3 text-sm leading-5 ${
                isSuccessMessage
                  ? "border-green-200 bg-green-50 text-green-800 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300"
                  : "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
              }`}
            >
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || Boolean(token)}
            className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-500/25 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Don't have an account?{" "}
            <Link
              to="/register"
              className="font-semibold text-blue-600 transition hover:text-blue-700 hover:underline dark:text-blue-400 dark:hover:text-blue-300"
            >
              Register
            </Link>
          </p>
        </div>
        </section>
      </main>
  )
}

export default Login
