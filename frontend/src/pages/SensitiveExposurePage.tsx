import {
  AlertTriangle,
  CheckCircle2,
  EyeOff,
  LockKeyhole,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { sensitiveApi } from '../services/api'
import type {
  SensitiveAlert,
  SensitiveCheck,
  SensitiveDescriptor,
  SensitiveFinding,
} from '../types/sensitive'
import { useTranslation, type MessageKey } from '../i18n/messages'

const categoryKeys: Record<string, MessageKey> = {
  nir: 'sensitiveCategoryNir',
  payment_card: 'sensitiveCategoryCard',
  iban: 'sensitiveCategoryIban',
  phone: 'sensitiveCategoryPhone',
  postal_address: 'sensitiveCategoryAddress',
  id_document: 'sensitiveCategoryIdDocument',
}

export function SensitiveExposurePage() {
  const { locale, t } = useTranslation()
  const [descriptors, setDescriptors] = useState<SensitiveDescriptor[]>([])
  const [checks, setChecks] = useState<SensitiveCheck[]>([])
  const [findings, setFindings] = useState<SensitiveFinding[]>([])
  const [alerts, setAlerts] = useState<SensitiveAlert[]>([])
  const [mode, setMode] = useState<'stored' | 'ephemeral' | 'card'>('stored')
  const [category, setCategory] = useState('phone')
  const [value, setValue] = useState('')
  const [network, setNetwork] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [nextDescriptors, nextChecks, nextFindings, nextAlerts] =
        await Promise.all([
          sensitiveApi.descriptors(),
          sensitiveApi.checks(),
          sensitiveApi.findings(),
          sensitiveApi.alerts(),
        ])
      setDescriptors(nextDescriptors)
      setChecks(nextChecks)
      setFindings(nextFindings)
      setAlerts(nextAlerts)
      setError(null)
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('sensitiveLoadFailed'),
      )
    }
  }, [t])
  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(task)
  }, [load])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setMessage(null)
    setError(null)
    try {
      if (mode === 'ephemeral') {
        const result = await sensitiveApi.validate(
          category as 'nir' | 'id_document',
          value,
        )
        setMessage(
          result.valid
            ? `${t('sensitiveValidFormat')} — ${result.masked_value ?? t('sensitiveValue')}`
            : t('sensitiveInvalidFormat'),
        )
      } else if (mode === 'card') {
        await sensitiveApi.createCard(network, value)
        setMessage(t('sensitiveCardAdded'))
        await load()
      } else {
        await sensitiveApi.createDescriptor(
          category as 'iban' | 'phone' | 'postal_address',
          value,
        )
        setMessage(t('sensitiveItemAdded'))
        await load()
      }
      setValue('')
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : t('sensitiveOperationFailed'),
      )
    }
  }

  return (
    <div className="px-4 py-8 sm:px-8 xl:px-12">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-semibold text-teal-700 dark:text-teal-400">
          {t('sensitiveSection')}
        </p>
        <div className="mt-2 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              {t('sensitiveTitle')}
            </h1>
            <p className="mt-3 max-w-3xl text-slate-600 dark:text-slate-300">
              {t('sensitiveIntro')}
            </p>
          </div>
          <button className="secondary-button" onClick={() => void load()}>
            <RefreshCw size={17} />
            {t('sensitiveRefresh')}
          </button>
        </div>

        <section
          className="mt-8 grid gap-4 sm:grid-cols-3"
          aria-label={t('sensitiveSummary')}
        >
          <Metric
            value={descriptors.length}
            label={t('sensitiveMonitoredCategories')}
          />
          <Metric value={checks.length} label={t('sensitiveChecksPerformed')} />
          <Metric
            value={alerts.filter((alert) => !alert.acknowledged_at).length}
            label={t('sensitiveAlertsToHandle')}
            safe={alerts.every((alert) => alert.acknowledged_at !== null)}
          />
        </section>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
          <section className="panel">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="section-title">
                  {t('sensitiveMonitoredItems')}
                </h2>
                <p className="section-copy">{t('sensitiveMaskedStorage')}</p>
              </div>
              <EyeOff className="text-teal-700" />
            </div>
            <div className="mt-5 space-y-3">
              {descriptors.length === 0 ? (
                <Empty t={t} />
              ) : (
                descriptors.map((item) => (
                  <article
                    key={item.id}
                    className="flex items-center justify-between rounded-2xl border border-slate-200 p-4 dark:border-slate-700"
                  >
                    <div>
                      <p className="text-sm font-semibold">
                        {t(categoryKeys[item.category])}
                      </p>
                      <p className="mt-1 font-mono text-sm text-slate-600 dark:text-slate-300">
                        {item.masked_label}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        className="icon-button"
                        aria-label={`${t('sensitiveCheck')} ${t(categoryKeys[item.category])}`}
                        onClick={() =>
                          void sensitiveApi.localCheck(item.id).then(load)
                        }
                      >
                        <RefreshCw size={17} />
                      </button>
                      <button
                        className="icon-button danger"
                        aria-label={`${t('sensitiveDelete')} ${t(categoryKeys[item.category])}`}
                        onClick={() =>
                          void sensitiveApi.remove(item.id).then(load)
                        }
                      >
                        <Trash2 size={17} />
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="panel">
            <h2 className="section-title">
              <Plus className="inline -translate-y-0.5" size={20} />{' '}
              {t('sensitiveAddOrCheck')}
            </h2>
            <div className="mt-4 grid grid-cols-3 rounded-xl bg-slate-100 p-1 text-xs font-semibold dark:bg-slate-800">
              {(
                [
                  ['stored', t('sensitiveModeStored')],
                  ['ephemeral', t('sensitiveModeEphemeral')],
                  ['card', t('sensitiveModeCard')],
                ] as const
              ).map(([key, label]) => (
                <button
                  key={key}
                  className={`rounded-lg px-2 py-2 ${mode === key ? 'bg-white shadow-sm dark:bg-slate-700' : ''}`}
                  onClick={() => {
                    setMode(key)
                    setCategory(key === 'ephemeral' ? 'nir' : 'phone')
                    setValue('')
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <form
              className="mt-5 space-y-4"
              onSubmit={(event) => void submit(event)}
            >
              {mode !== 'card' && (
                <label className="field-label">
                  {t('sensitiveCategory')}
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    {mode === 'ephemeral' ? (
                      <>
                        <option value="nir">NIR</option>
                        <option value="id_document">
                          {t('sensitiveCategoryIdDocument')}
                        </option>
                      </>
                    ) : (
                      <>
                        <option value="phone">
                          {t('sensitiveCategoryPhone')}
                        </option>
                        <option value="iban">IBAN</option>
                        <option value="postal_address">
                          {t('sensitiveCategoryAddress')}
                        </option>
                      </>
                    )}
                  </select>
                </label>
              )}
              {mode === 'card' && (
                <label className="field-label">
                  {t('sensitiveNetwork')}
                  <input
                    required
                    value={network}
                    onChange={(e) => setNetwork(e.target.value)}
                    placeholder={t('sensitiveVisaExample')}
                  />
                </label>
              )}
              <label className="field-label">
                {mode === 'card' ? t('sensitiveLastFour') : t('sensitiveValue')}
                <input
                  required
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  inputMode={mode === 'card' ? 'numeric' : 'text'}
                  maxLength={mode === 'card' ? 4 : 300}
                  autoComplete="off"
                />
              </label>
              <div className="notice">
                <LockKeyhole size={17} />
                <span>
                  {mode === 'ephemeral'
                    ? t('sensitiveEphemeralNotice')
                    : mode === 'card'
                      ? t('sensitiveCardNotice')
                      : t('sensitiveStoredNotice')}
                </span>
              </div>
              {message && (
                <p className="success-message">
                  <CheckCircle2 size={17} />
                  {message}
                </p>
              )}
              {error && (
                <p className="error-message">
                  <AlertTriangle size={17} />
                  {error}
                </p>
              )}
              <button className="primary-button w-full" type="submit">
                {mode === 'ephemeral'
                  ? t('sensitiveValidateLocally')
                  : t('sensitiveAddSecurely')}
              </button>
            </form>
          </section>
        </div>

        <section className="panel mt-6" aria-labelledby="alerts-title">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
            <div>
              <h2 className="section-title" id="alerts-title">
                {t('sensitiveAlertsTitle')}
              </h2>
              <p className="section-copy">
                {findings.length} {t('sensitiveFindings')}
              </p>
            </div>
            <p className="text-xs text-slate-500">
              {t('sensitiveNotificationPrivacy')}
            </p>
          </div>
          <div className="mt-5 space-y-3">
            {alerts.length === 0 ? (
              <div className="rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-100">
                {t('sensitiveNoConfirmedAlerts')}
              </div>
            ) : (
              alerts.map((alert) => (
                <article
                  key={alert.id}
                  className="rounded-2xl border border-amber-200 bg-amber-50/60 p-4 dark:border-amber-900 dark:bg-amber-950/20"
                >
                  <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`risk-badge risk-${alert.risk_level}`}>
                          {t('sensitiveRisk')} {t(riskKeys[alert.risk_level])}
                        </span>
                        <span className="text-sm font-semibold">
                          {t(categoryKeys[alert.category])}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-slate-700 dark:text-slate-200">
                        {t('sensitiveAuthorizedSource')} {alert.source_label} ·{' '}
                        {t('sensitiveDetectedOn')}{' '}
                        {new Date(alert.created_at).toLocaleDateString(
                          locale === 'fr' ? 'fr-FR' : 'en-GB',
                        )}
                      </p>
                      <p className="mt-2 text-sm font-medium text-slate-900 dark:text-white">
                        {alert.recommendation}
                      </p>
                    </div>
                    {alert.acknowledged_at ? (
                      <span className="status whitespace-nowrap">
                        {t('sensitiveAcknowledged')}
                      </span>
                    ) : (
                      <button
                        className="secondary-button whitespace-nowrap"
                        onClick={() =>
                          void sensitiveApi
                            .acknowledgeAlert(alert.id)
                            .then(load)
                            .catch((caught: unknown) =>
                              setError(
                                caught instanceof Error
                                  ? caught.message
                                  : t('sensitiveOperationFailed'),
                              ),
                            )
                        }
                      >
                        {t('sensitiveMarkHandled')}
                      </button>
                    )}
                  </div>
                </article>
              ))
            )}
          </div>
        </section>

        <section className="panel mt-6">
          <h2 className="section-title">{t('sensitiveHistory')}</h2>
          <p className="section-copy">{t('sensitiveNoAlertDoesNotProve')}</p>
          <div className="mt-5 overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>{t('sensitiveCategory')}</th>
                  <th>{t('sensitiveAuthorizedSource').replace(':', '')}</th>
                  <th>{t('sensitiveDate')}</th>
                  <th>{t('sensitiveTransmission')}</th>
                  <th>{t('sensitiveState')}</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((check) => (
                  <tr key={check.id}>
                    <td>{t(categoryKeys[check.category])}</td>
                    <td>{check.provider_id}</td>
                    <td>
                      {new Date(check.started_at).toLocaleDateString(
                        locale === 'fr' ? 'fr-FR' : 'en-GB',
                      )}
                    </td>
                    <td>
                      {t(
                        check.external_transmission
                          ? 'sensitiveExternal'
                          : 'sensitiveLocal',
                      )}
                    </td>
                    <td>
                      <span className="status">
                        {check.status === 'completed'
                          ? t('sensitiveCompleted')
                          : check.status === 'pending'
                            ? t('sensitivePending')
                            : t('sensitiveFailed')}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {checks.length === 0 && (
              <p className="py-8 text-center text-sm text-slate-500">
                {t('sensitiveNoChecks')}
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

const riskKeys: Record<SensitiveAlert['risk_level'], MessageKey> = {
  low: 'sensitiveRiskLow',
  medium: 'sensitiveRiskMedium',
  high: 'sensitiveRiskHigh',
  critical: 'sensitiveRiskCritical',
}

function Metric({
  value,
  label,
  safe = false,
}: {
  value: number
  label: string
  safe?: boolean
}) {
  return (
    <div className="panel">
      <div className="flex items-center gap-3">
        <span
          className={`grid size-10 place-items-center rounded-xl ${safe ? 'bg-emerald-100 text-emerald-700' : 'bg-teal-100 text-teal-700'}`}
        >
          {safe ? <CheckCircle2 size={20} /> : <LockKeyhole size={20} />}
        </span>
        <div>
          <p className="text-2xl font-semibold">{value}</p>
          <p className="text-sm text-slate-500">{label}</p>
        </div>
      </div>
    </div>
  )
}
function Empty({ t }: { t: (key: MessageKey) => string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
      <EyeOff className="mx-auto text-slate-400" />
      <p className="mt-3 font-medium">{t('sensitiveEmptyTitle')}</p>
      <p className="mt-1 text-sm text-slate-500">
        {t('sensitiveEmptyDescription')}
      </p>
    </div>
  )
}
