
import { useState } from "react"
import { NavLink } from "react-router-dom"

function Sidebar() {
  const [isOpen, setIsOpen] = useState(false)

  const navigationItems = [
    { label: "Dashboard", path: "/" },
    { label: "Jobs", path: "/jobs" },
    { label: "Resume", path: "/resume" },
    { label: "Applications", path: "/applications" },
    { label: "Preferences", path: "/preferences" },
  ]

  function handleNavigation() {
    setIsOpen(false)
  }

  return (
    <>
      {/* Mobile Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900 md:hidden">
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

      {/* Sidebar */}
      <aside
        id="sidebar-navigation"
        className={`
          ${isOpen ? "block" : "hidden"}
          w-full border-b border-gray-200 bg-white
          dark:border-gray-700 dark:bg-gray-900
          md:fixed md:inset-y-0 md:left-0 md:z-40
          md:block md:h-screen md:w-64 md:overflow-y-auto
          md:border-b-0 md:border-r
        `}
      >
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
