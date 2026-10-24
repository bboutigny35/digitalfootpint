import { Database, KeyRound, ServerCog, ShieldCheck } from 'lucide-react'
import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react'
import {
  adminApi,
  osintApi,
  type AdminOverview,
  type AuditEventPage,
  type ConnectorStatus,
  type ConnectorSecretStatus,
  type PlatformCatalogEntry,
  type WebSource,
} from '../services/api'
import { useTranslation } from '../i18n/messages'

export function AdminPage() {
  const { locale, t } = useTranslation()
  const [overview, setOverview] = useState<AdminOverview | null>(null)
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [events, setEvents] = useState<AuditEventPage | null>(null)
  const [secrets, setSecrets] = useState<ConnectorSecretStatus[]>([])
  const [platforms, setPlatforms] = useState<PlatformCatalogEntry[]>([])
  const [sources, setSources] = useState<WebSource[]>([])
  const [sourceUrl, setSourceUrl] = useState('')
  const [sourceCategory, setSourceCategory] = useState('manual')
  const [githubToken, setGithubToken] = useState('')
  const [braveToken, setBraveToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [
        nextOverview,
        nextConnectors,
        nextEvents,
        nextSecrets,
        nextPlatforms,
        nextSources,
      ] = await Promise.all([
        adminApi.overview(),
        osintApi.connectors(),
        adminApi.auditEvents(),
        adminApi.connectorSecrets(),
        adminApi.platformCatalog(),
        adminApi.webSources(),
      ])
      setOverview(nextOverview)
      setConnectors(nextConnectors)
      setEvents(nextEvents)
      setSecrets(nextSecrets)
      setPlatforms(nextPlatforms)
      setSources(nextSources)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t('adminLoadFailed'))
    }
  }, [t])

  async function createSource(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await adminApi.createWebSource(sourceUrl, sourceCategory)
      setSourceUrl('')
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t('adminSaveFailed'))
    } finally {
      setBusy(false)
    }
  }

  async function saveGithubToken(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await adminApi.setConnectorSecret('github', githubToken)
      setGithubToken('')
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t('adminSaveFailed'))
    } finally {
      setBusy(false)
    }
  }

  async function deleteGithubToken() {
    if (!window.confirm(t('adminConfirmDeleteToken'))) return
    setBusy(true)
    try {
      await adminApi.deleteConnectorSecret('github')
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('adminDeleteFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function saveBraveToken(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await adminApi.setConnectorSecret('brave', braveToken)
      setBraveToken('')
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t('adminSaveFailed'))
    } finally {
      setBusy(false)
    }
  }

  async function deleteBraveToken() {
    if (!window.confirm(t('adminConfirmDeleteToken'))) return
    setBusy(true)
    try {
      await adminApi.deleteConnectorSecret('brave')
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('adminDeleteFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function rotateSecrets() {
    setBusy(true)
    try {
      await adminApi.rotateConnectorSecrets()
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('adminRotationFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function configureConnector(connector: ConnectorStatus) {
    if (
      connector.enabled &&
      !window.confirm(
        formatMessage(t('adminConfirmDisableConnector'), {
          connector: connector.identifier,
        }),
      )
    )
      return
    setBusy(true)
    try {
      await adminApi.configureConnector(
        connector.identifier,
        !connector.enabled,
      )
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('adminConfigureFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function downloadBackup() {
    if (!window.confirm(t('adminConfirmBackup'))) return
    setBusy(true)
    setError(null)
    try {
      const { blob, filename } = await adminApi.downloadBackup()
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename
      link.click()
      URL.revokeObjectURL(objectUrl)
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('adminBackupFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(task)
  }, [load])

  return (
    <div className="px-4 py-8 sm:px-8 xl:px-12">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-semibold text-teal-700 dark:text-teal-400">
          {t('adminAccess')}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          {t('adminTitle')}
        </h1>
        {error && <p className="error-message mt-5">{error}</p>}
        {overview && (
          <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <AdminMetric
              icon={<ServerCog size={19} />}
              label={t('adminVersion')}
              value={overview.application_version}
            />
            <AdminMetric
              icon={<Database size={19} />}
              label={t('adminDatabase')}
              value={overview.database_backend}
            />
            <AdminMetric
              icon={<ShieldCheck size={19} />}
              label={t('adminSecureCookie')}
              value={t(
                overview.cookie_secure ? 'adminEnabled' : 'adminDisabled',
              )}
            />
            <AdminMetric
              icon={<KeyRound size={19} />}
              label={t('adminToken')}
              value={t(
                overview.github_token_configured
                  ? 'adminConfigured'
                  : 'adminMissing',
              )}
            />
          </section>
        )}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="panel">
            <h2 className="section-title">{t('adminConnectors')}</h2>
            <div className="mt-4 space-y-3">
              {connectors.map((connector) => (
                <article
                  className="rounded-xl border border-slate-200 p-4 dark:border-slate-700"
                  key={connector.identifier}
                >
                  <div className="flex justify-between gap-3">
                    <p className="font-semibold">{connector.identifier}</p>
                    <span className="text-sm">{connector.health}</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    Version {connector.version} ·{' '}
                    {formatMessage(t('adminResultsAndErrors'), {
                      results: connector.result_count,
                      errors: connector.error_count,
                    })}
                  </p>
                  <button
                    className="secondary-button mt-3"
                    disabled={busy}
                    onClick={() => void configureConnector(connector)}
                  >
                    {t(connector.enabled ? 'adminDisable' : 'adminEnable')}
                  </button>
                </article>
              ))}
            </div>
          </section>
          <section className="panel">
            <h2 className="section-title">{t('adminConnectorKeys')}</h2>
            <p className="section-copy">{t('adminSecretsNotice')}</p>
            <form className="mt-5 space-y-4" onSubmit={saveGithubToken}>
              <label className="field-label">
                {t('adminToken')}
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={githubToken}
                  onChange={(event) => setGithubToken(event.target.value)}
                />
              </label>
              <p className="text-xs text-slate-500">
                {t('adminSecretState')}{' '}
                {secrets.find((item) => item.connector_id === 'github')
                  ?.configured
                  ? t('adminConfigured').toLowerCase()
                  : t('adminMissing').toLowerCase()}
              </p>
              <div className="flex flex-wrap gap-3">
                <button className="primary-button" disabled={busy}>
                  {t('adminSave')}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={busy}
                  onClick={() => void deleteGithubToken()}
                >
                  {t('adminDelete')}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={busy}
                  onClick={() => void rotateSecrets()}
                >
                  {t('adminRotate')}
                </button>
              </div>
            </form>
            <form
              className="mt-6 space-y-4 border-t border-slate-200 pt-5 dark:border-slate-700"
              onSubmit={saveBraveToken}
            >
              <label className="field-label">
                {t('adminBraveToken')}
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={braveToken}
                  onChange={(event) => setBraveToken(event.target.value)}
                />
              </label>
              <p className="text-xs text-slate-500">
                {t('adminSecretState')}{' '}
                {secrets.find((item) => item.connector_id === 'brave')
                  ?.configured
                  ? t('adminConfigured').toLowerCase()
                  : t('adminMissing').toLowerCase()}
              </p>
              <p className="text-sm text-amber-700 dark:text-amber-300">
                {t('adminBraveDisclosure')}{' '}
                <a
                  className="underline"
                  href="https://api-dashboard.search.brave.com/documentation/pricing"
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  {t('adminBravePricing')}
                </a>
              </p>
              <div className="flex flex-wrap gap-3">
                <button className="primary-button" disabled={busy}>
                  {t('adminSave')}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={busy}
                  onClick={() => void deleteBraveToken()}
                >
                  {t('adminDelete')}
                </button>
              </div>
            </form>
          </section>
          <section className="panel">
            <h2 className="section-title">{t('adminBackups')}</h2>
            <p className="section-copy">{t('adminBackupNotice')}</p>
            <button
              className="primary-button mt-5"
              disabled={busy}
              onClick={() => void downloadBackup()}
            >
              {t('adminDownloadBackup')}
            </button>
            <code className="mt-4 block rounded-xl bg-slate-950 p-4 text-sm text-slate-100">
              sudo /opt/digitalfootprint/current/scripts/backup.sh
            </code>
          </section>
        </div>
        <section className="panel mt-6 overflow-x-auto">
          <h2 className="section-title">{t('adminPlatformCatalog')}</h2>
          <p className="section-copy">{t('adminPlatformCatalogNotice')}</p>
          <table className="mt-4">
            <thead>
              <tr>
                <th>{t('adminPlatform')}</th>
                <th>{t('adminMethod')}</th>
                <th>{t('adminStatus')}</th>
                <th>{t('adminConnector')}</th>
                <th>{t('adminLastCheck')}</th>
                <th>{t('adminLastError')}</th>
              </tr>
            </thead>
            <tbody>
              {platforms.map((platform) => (
                <tr key={platform.identifier}>
                  <td>{platform.display_name}</td>
                  <td>{platform.verification_method}</td>
                  <td>{platform.default_status}</td>
                  <td>{platform.connector_id ?? '—'}</td>
                  <td>
                    {platform.last_checked_at
                      ? new Date(platform.last_checked_at).toLocaleString(
                          locale === 'fr' ? 'fr-FR' : 'en-GB',
                        )
                      : '—'}
                  </td>
                  <td>{platform.last_error_code ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className="panel mt-6">
          <h2 className="section-title">{t('adminWebSources')}</h2>
          <p className="section-copy">{t('adminWebSourcesNotice')}</p>
          <form
            className="mt-4 grid gap-4 md:grid-cols-[2fr_1fr_auto]"
            onSubmit={(event) => void createSource(event)}
          >
            <label className="field-label">
              {t('adminSourceUrl')}
              <input
                type="url"
                required
                value={sourceUrl}
                onChange={(event) => setSourceUrl(event.target.value)}
              />
            </label>
            <label className="field-label">
              {t('adminSourceCategory')}
              <input
                required
                value={sourceCategory}
                onChange={(event) => setSourceCategory(event.target.value)}
              />
            </label>
            <button className="primary-button self-end" disabled={busy}>
              {t('adminAddSource')}
            </button>
          </form>
          <div className="mt-5 space-y-3">
            {sources.map((source) => (
              <article
                className="rounded-xl border border-slate-200 p-4 dark:border-slate-700"
                key={source.id}
              >
                <div className="flex flex-wrap justify-between gap-3">
                  <p className="font-semibold">{source.domain}</p>
                  <span className="text-sm">{source.state}</span>
                </div>
                <p className="mt-2 break-all text-xs text-slate-500">
                  {source.base_url}
                </p>
              </article>
            ))}
          </div>
        </section>
        <section className="panel mt-6 overflow-x-auto">
          <div className="flex items-center justify-between gap-3">
            <h2 className="section-title">{t('adminAuditLog')}</h2>
            <span className="text-sm text-slate-500">
              {events?.total ?? 0} {t('adminEvents')}
            </span>
          </div>
          <table className="mt-4">
            <thead>
              <tr>
                <th>{t('reportDate')}</th>
                <th>{t('adminAction')}</th>
                <th>{t('adminResource')}</th>
                <th>{t('adminIdentifier')}</th>
              </tr>
            </thead>
            <tbody>
              {events?.items.map((event) => (
                <tr key={event.id}>
                  <td>
                    {new Date(event.created_at).toLocaleString(
                      locale === 'fr' ? 'fr-FR' : 'en-GB',
                    )}
                  </td>
                  <td>{event.action}</td>
                  <td>{event.resource_type}</td>
                  <td className="font-mono text-xs">
                    {event.resource_id ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  )
}

function AdminMetric({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="panel">
      <div className="text-teal-700">{icon}</div>
      <p className="mt-3 text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  )
}

function formatMessage(
  message: string,
  values: Record<string, string | number>,
): string {
  return message.replace(/\{(\w+)\}/g, (placeholder, key: string) =>
    Object.hasOwn(values, key) ? String(values[key]) : placeholder,
  )
}
