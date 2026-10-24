import {
  CalendarClock,
  Cog,
  FileText,
  Fingerprint,
  LayoutDashboard,
  Moon,
  Search,
  Send,
  ShieldCheck,
  Sun,
  UserRound,
} from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import {
  getInitialLocale,
  saveLocale,
  translate,
  LocaleContext,
  type Locale,
} from '../i18n/messages'

export type AppPage =
  | 'dashboard'
  | 'identities'
  | 'scans'
  | 'results'
  | 'reports'
  | 'monitoring'
  | 'removals'
  | 'sensitive'
  | 'admin'

export function Layout({
  children,
  userEmail,
  isAdmin,
  onLogout,
  activePage,
  onNavigate,
}: {
  children: ReactNode
  userEmail: string
  isAdmin: boolean
  onLogout: () => void
  activePage: AppPage
  onNavigate: (page: AppPage) => void
}) {
  const [dark, setDark] = useState(false)
  const [locale, setLocale] = useState<Locale>(getInitialLocale)
  const t = (key: Parameters<typeof translate>[1]) => translate(locale, key)
  const changeLocale = (next: Locale) => {
    setLocale(next)
    saveLocale(next)
  }
  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])
  return (
    <LocaleContext.Provider value={{ locale, t }}>
      <div className={dark ? 'dark' : ''}>
        <div className="min-h-screen bg-stone-50 text-slate-950 transition-colors dark:bg-slate-950 dark:text-slate-100">
          <header className="border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90 lg:hidden">
            <div className="flex items-center justify-between">
              <Brand />
              <div className="flex items-center gap-2">
                <label className="sr-only" htmlFor="mobile-language-select">
                  {t('language')}
                </label>
                <select
                  id="mobile-language-select"
                  className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
                  value={locale}
                  onChange={(event) =>
                    changeLocale(event.target.value as Locale)
                  }
                >
                  <option value="fr">FR</option>
                  <option value="en">EN</option>
                </select>
                <button
                  className="icon-button"
                  onClick={() => setDark(!dark)}
                  aria-label={t('changeTheme')}
                >
                  {dark ? <Sun size={18} /> : <Moon size={18} />}
                </button>
              </div>
            </div>
            <nav
              className="mt-3 flex gap-2 overflow-x-auto pb-1"
              aria-label="Navigation mobile"
            >
              {mobilePages
                .filter((page) => page !== 'admin' || isAdmin)
                .map((page) => (
                  <button
                    key={page}
                    className={
                      activePage === page
                        ? 'primary-button'
                        : 'secondary-button'
                    }
                    onClick={() => onNavigate(page)}
                  >
                    {mobileLabel(page, t)}
                  </button>
                ))}
            </nav>
          </header>
          <div className="mx-auto flex min-h-screen max-w-[1600px]">
            <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white px-5 py-7 dark:border-slate-800 dark:bg-slate-950 lg:block">
              <Brand />
              <nav
                aria-label="Navigation principale"
                className="mt-10 space-y-1"
              >
                <NavItem
                  icon={<LayoutDashboard size={18} />}
                  label={t('dashboard')}
                  active={activePage === 'dashboard'}
                  onClick={() => onNavigate('dashboard')}
                />
                <NavItem
                  icon={<UserRound size={18} />}
                  label={t('identities')}
                  active={activePage === 'identities'}
                  onClick={() => onNavigate('identities')}
                />
                <NavItem
                  icon={<Search size={18} />}
                  label={t('searches')}
                  active={activePage === 'scans'}
                  onClick={() => onNavigate('scans')}
                />
                <NavItem
                  icon={<Fingerprint size={18} />}
                  label={t('results')}
                  active={activePage === 'results'}
                  onClick={() => onNavigate('results')}
                />
                <NavItem
                  icon={<FileText size={18} />}
                  label={t('reports')}
                  active={activePage === 'reports'}
                  onClick={() => onNavigate('reports')}
                />
                <NavItem
                  icon={<CalendarClock size={18} />}
                  label={t('monitoring')}
                  active={activePage === 'monitoring'}
                  onClick={() => onNavigate('monitoring')}
                />
                <NavItem
                  icon={<Send size={18} />}
                  label={t('removalRequests')}
                  active={activePage === 'removals'}
                  onClick={() => onNavigate('removals')}
                />
                <p className="px-3 pb-2 pt-7 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                  {t('security')}
                </p>
                <NavItem
                  icon={<ShieldCheck size={18} />}
                  label={t('sensitiveData')}
                  active={activePage === 'sensitive'}
                  onClick={() => onNavigate('sensitive')}
                />
                {isAdmin && (
                  <NavItem
                    icon={<Cog size={18} />}
                    label={t('administration')}
                    active={activePage === 'admin'}
                    onClick={() => onNavigate('admin')}
                  />
                )}
              </nav>
              <div className="mt-10 rounded-2xl bg-teal-50 p-4 text-sm text-teal-950 dark:bg-teal-950/50 dark:text-teal-100">
                <p className="font-semibold">{t('localProcessing')}</p>
                <p className="mt-1 text-teal-800 dark:text-teal-200">
                  {t('noSensitiveProvider')}
                </p>
              </div>
            </aside>
            <main className="min-w-0 flex-1">
              <div className="hidden items-center justify-end gap-4 border-b border-slate-200 bg-white px-8 py-3 dark:border-slate-800 dark:bg-slate-950 lg:flex">
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {userEmail}
                </span>
                <label className="sr-only" htmlFor="language-select">
                  {t('language')}
                </label>
                <select
                  id="language-select"
                  className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
                  value={locale}
                  onChange={(event) =>
                    changeLocale(event.target.value as Locale)
                  }
                >
                  <option value="fr">Français</option>
                  <option value="en">English</option>
                </select>
                <button
                  className="text-sm font-medium text-teal-700 dark:text-teal-300"
                  onClick={onLogout}
                >
                  {t('logout')}
                </button>
                <button
                  className="icon-button"
                  onClick={() => setDark(!dark)}
                  aria-label={t('changeTheme')}
                >
                  {dark ? <Sun size={18} /> : <Moon size={18} />}
                </button>
              </div>
              {children}
            </main>
          </div>
        </div>
      </div>
    </LocaleContext.Provider>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-3 font-semibold tracking-tight">
      <span className="grid size-10 place-items-center rounded-xl bg-teal-700 text-white">
        <Fingerprint size={22} />
      </span>
      <span className="text-lg">DigitalFootprint</span>
    </div>
  )
}

function NavItem({
  icon,
  label,
  active = false,
  onClick,
}: {
  icon: ReactNode
  label: string
  active?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium ${active ? 'bg-slate-900 text-white dark:bg-teal-600' : 'text-slate-600 dark:text-slate-300'}`}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

const mobilePages: AppPage[] = [
  'dashboard',
  'identities',
  'scans',
  'results',
  'reports',
  'monitoring',
  'removals',
  'sensitive',
  'admin',
]

function mobileLabel(
  page: AppPage,
  t: (key: Parameters<typeof translate>[1]) => string,
): string {
  const keys: Partial<Record<AppPage, Parameters<typeof translate>[1]>> = {
    dashboard: 'dashboard',
    identities: 'identities',
    scans: 'searches',
    results: 'results',
    reports: 'reports',
    monitoring: 'monitoring',
    removals: 'removalRequests',
    sensitive: 'sensitiveData',
    admin: 'administration',
  }
  return keys[page] ? t(keys[page]!) : t('dashboard')
}
