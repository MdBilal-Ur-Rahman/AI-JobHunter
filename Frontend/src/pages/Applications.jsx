import Sidebar from "../components/Sidebar"
import Header from "../components/Header"
import RecentApplications from "../components/RecentApplications"

function Applications() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar />
      <div className="min-h-screen md:ml-64">
        <Header />
        <main className="p-4 sm:p-6 lg:p-8">
          <div className="mx-auto w-full max-w-7xl">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">
                Applications
              </h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Review prepared applications and update their status.
                Submission is always a separate, user-controlled action.
              </p>
            </div>
            <RecentApplications />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Applications
