import { useEffect, useState } from 'react'
import { Layout, type AppPage } from './components/Layout'
import { AuthPage } from './pages/AuthPage'
import { SensitiveExposurePage } from './pages/SensitiveExposurePage'
import { OsintWorkspacePage } from './pages/OsintWorkspacePage'
import { ReportsPage } from './pages/ReportsPage'
import { MonitoringPage } from './pages/MonitoringPage'
import { RemovalRequestsPage } from './pages/RemovalRequestsPage'
import { AdminPage } from './pages/AdminPage'
import { authApi, type AuthUser } from './services/api'
import { getInitialLocale, translate } from './i18n/messages'

export function App() {
  const locale = getInitialLocale()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState<AppPage>('identities')

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  useEffect(() => {
    let active = true
    void authApi
      .restore()
      .then((restored) => {
        if (active) setUser(restored)
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-950 text-sm text-slate-300">
        {translate(locale, 'authSecureLoading')}
      </div>
    )
  }
  if (!user) return <AuthPage onAuthenticated={setUser} />

  return (
    <Layout
      userEmail={user.email}
      isAdmin={user.is_admin}
      onLogout={() => void authApi.logout().finally(() => setUser(null))}
      activePage={page}
      onNavigate={setPage}
    >
      {page === 'sensitive' ? (
        <SensitiveExposurePage />
      ) : page === 'reports' ? (
        <ReportsPage />
      ) : page === 'monitoring' ? (
        <MonitoringPage />
      ) : page === 'removals' ? (
        <RemovalRequestsPage />
      ) : page === 'admin' ? (
        <AdminPage />
      ) : (
        <OsintWorkspacePage section={page} />
      )}
    </Layout>
  )
}
