
import { useEffect, useState } from "react"
import { NavLink } from "react-router-dom"

function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)

  const navigationItems = [
    { label: "Dashboard", path: "/" },
    { label: "Jobs", path: "/jobs" },
    { label: "Resume", path: "/resume" },
    { label: "Applications", path: "/applications" },
    { label: "Preferences", path: "/preferences" },
    { label: "Profile", path: "/profile" },
  ]

  function handleNavigation() {
    setIsOpen(false)
  }

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setIsOpen(false)
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  return (
    <>
      {/* Mobile Header */}
      <div className="sticky top-0 z-40 flex items-center justify-between border-b border-gray-200 bg-white/95 p-4 backdrop-blur dark:border-gray-700 dark:bg-gray-900/95 md:hidden">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            AI JobHunter
          </h1>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Smart Job Assistant
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen((previous) => !previous)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-gray-700 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
          aria-label={
            isOpen ? "Close navigation menu" : "Open navigation menu"
          }
          aria-expanded={isOpen}
          aria-controls="sidebar-navigation"
        >
          {isOpen ? "✕" : "☰"}
        </button>
      </div>

      {isOpen && (
        <button
          type="button"
          onClick={handleNavigation}
          className="fixed inset-0 z-40 bg-gray-950/50 md:hidden"
          aria-label="Close navigation menu"
        />
      )}

      {/* Sidebar */}
      <aside
        id="sidebar-navigation"
        className={`
          ${isOpen
            ? "fixed inset-y-0 left-0 z-50 block w-72 max-w-[calc(100vw-2rem)] overflow-y-auto"
            : "hidden"
          }
          border-b border-gray-200 bg-white shadow-xl
          dark:border-gray-700 dark:bg-gray-900
          md:fixed md:inset-y-0 md:left-0 md:z-40
          md:block md:h-dvh md:w-64 md:overflow-y-auto
          md:border-b-0 md:border-r md:shadow-none
        `}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-700 md:hidden">
          <div>
            <h2 className="font-bold text-gray-900 dark:text-white">
              Navigation
            </h2>
            <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
              Your workspace
            </p>
          </div>
          <button
            type="button"
            onClick={handleNavigation}
            className="rounded-lg p-2 text-gray-600 transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-gray-300 dark:hover:bg-gray-800"
            aria-label="Close navigation menu"
          >
            ✕
          </button>
        </div>

        {/* Desktop Logo */}
        <div className="hidden p-6 md:block">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI JobHunter
          </h1>

          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Smart Job Assistant
          </p>
        </div>

        {/* Navigation */}
        <nav
          aria-label="Main navigation"
          className="px-4 py-4 md:px-6 md:pt-0"
        >
          <div className="space-y-2">
            {navigationItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                onClick={handleNavigation}
                className={({ isActive }) => `
                  block w-full rounded-lg px-4 py-3 text-left transition
                  focus:outline-none focus:ring-2 focus:ring-blue-500
                  ${
                    isActive
                      ? "bg-gray-100 font-medium text-gray-900 dark:bg-gray-800 dark:text-white"
                      : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                  }
                `}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </aside>
    </>
  )
}

export default Sidebar
