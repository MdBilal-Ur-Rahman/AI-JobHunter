import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react"
import { logoutUser } from "../services/api"

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => {
    return localStorage.getItem("access_token")
  })

  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem("auth_user")

    if (!savedUser) {
      return null
    }

    try {
      return JSON.parse(savedUser)
    } catch {
      localStorage.removeItem("auth_user")
      return null
    }
  })

  const isAuthenticated = Boolean(token)

  useEffect(() => {
    if (token) {
      localStorage.setItem("access_token", token)
    } else {
      localStorage.removeItem("access_token")
    }
  }, [token])

  useEffect(() => {
    if (user) {
      localStorage.setItem(
        "auth_user",
        JSON.stringify(user)
      )
    } else {
      localStorage.removeItem("auth_user")
    }
  }, [user])

  useEffect(() => {
    function handleSessionExpired() {
      setToken(null)
      setUser(null)

      localStorage.removeItem("access_token")
      localStorage.removeItem("auth_user")
    }

    window.addEventListener(
      "auth:session-expired",
      handleSessionExpired
    )

    return () => {
      window.removeEventListener(
        "auth:session-expired",
        handleSessionExpired
      )
    }
  }, [])

  function login(accessToken, userData = null) {
    setToken(accessToken)

    if (userData) {
      setUser(userData)
    }
  }

  async function logout() {
    const currentToken = token

    try {
      if (currentToken) {
        await logoutUser(currentToken)
      }
    } catch (error) {
      console.error(
        "Backend logout failed:",
        error
      )
    } finally {
      setToken(null)
      setUser(null)

      localStorage.removeItem("access_token")
      localStorage.removeItem("auth_user")
    }
  }

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        setUser,
        isAuthenticated,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}