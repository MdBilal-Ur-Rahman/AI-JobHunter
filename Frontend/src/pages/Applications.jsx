import { useNavigate } from "react-router-dom"
import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import RecentApplications from "../components/RecentApplications"

function Applications() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar />
      <div className="min-h-screen md:ml-64">
        <Header />
        <main className="p-4 sm:p-6 lg:p-8">
          <div className="mx-auto w-full max-w-7xl">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">
                  Applications
                </h1>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  Review prepared applications and update their status.
                  Submission is always a separate, user-controlled action.
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
            <RecentApplications />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Applications
