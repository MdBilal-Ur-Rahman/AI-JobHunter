
import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { loginUser } from "../services/api"

function Login() {
  const navigate = useNavigate()
  const { login, token } = useAuth()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [message, setMessage] = useState("")
  const [isLoading, setIsLoading] = useState(false)

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
    <div className="flex min-h-screen items-center justify-center bg-gray-100 px-4 py-8 dark:bg-gray-950">
      <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900 sm:p-8">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">
            AI JobHunter
          </h1>

          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
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
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-900 dark:disabled:bg-gray-800"
            />
          </div>

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
              autoComplete="current-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setMessage("")
              }}
              placeholder="Enter your password"
              disabled={isLoading || Boolean(token)}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:opacity-70 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-400 dark:focus:ring-blue-900 dark:disabled:bg-gray-800"
            />
          </div>

          {message && (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm leading-5 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
            >
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || Boolean(token)}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:focus:ring-offset-gray-900"
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
      </div>
    </div>
  )
}

export default Login
