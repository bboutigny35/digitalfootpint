import { Fingerprint, LoaderCircle, LockKeyhole } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { authApi, type AuthUser } from '../services/api'
import {
  getInitialLocale,
  saveLocale,
  translate,
  type Locale,
  type MessageKey,
} from '../i18n/messages'

export function AuthPage({
  onAuthenticated,
}: {
  onAuthenticated: (user: AuthUser) => void
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [bootstrap, setBootstrap] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [locale, setLocale] = useState<Locale>(getInitialLocale)
  const t = (key: MessageKey) => translate(locale, key)

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = bootstrap
        ? await authApi.bootstrap(email, password)
        : await authApi.login(email, password)
      onAuthenticated(user)
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : t('authConnectionFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 px-4 py-10 text-slate-950">
      <div className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl shadow-teal-950/30 sm:p-9">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 text-slate-950">
            <span className="grid size-12 place-items-center rounded-2xl bg-teal-700 text-white">
              <Fingerprint size={26} />
            </span>
            <div>
              <p className="text-lg font-semibold">DigitalFootprint</p>
              <p className="text-sm text-slate-500">
                {t('authHostedInstance')}
              </p>
            </div>
          </div>
          <label className="sr-only" htmlFor="auth-language-select">
            {t('language')}
          </label>
          <select
            id="auth-language-select"
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-sm"
            value={locale}
            onChange={(event) => {
              const nextLocale = event.target.value as Locale
              setLocale(nextLocale)
              saveLocale(nextLocale)
            }}
          >
            <option value="fr">Français</option>
            <option value="en">English</option>
          </select>
        </div>
        <div className="mt-9">
          <LockKeyhole className="text-teal-700" size={26} />
          <h1 className="mt-3 text-2xl font-semibold tracking-tight">
            {bootstrap ? t('authCreateAdmin') : t('authSignIn')}
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {bootstrap ? t('authFirstOpen') : t('authLocalSpace')}
          </p>
        </div>
        <form className="mt-7 space-y-4" onSubmit={submit}>
          <label className="block text-sm font-medium">
            {t('authEmail')}
            <input
              className="input mt-2"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block text-sm font-medium">
            {t('authPassword')}
            <input
              className="input mt-2"
              type="password"
              autoComplete={bootstrap ? 'new-password' : 'current-password'}
              minLength={12}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && (
            <p
              role="alert"
              className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              {error}
            </p>
          )}
          <button
            className="button-primary w-full"
            type="submit"
            disabled={busy}
          >
            {busy && <LoaderCircle className="animate-spin" size={17} />}
            {bootstrap ? t('authInitialize') : t('authLogin')}
          </button>
        </form>
        <button
          className="mt-5 w-full text-center text-sm font-medium text-teal-800 hover:text-teal-950"
          type="button"
          onClick={() => {
            setBootstrap(!bootstrap)
            setError(null)
          }}
        >
          {bootstrap ? t('authAlreadyAccount') : t('authFirstUse')}
        </button>
      </div>
    </main>
  )
}
