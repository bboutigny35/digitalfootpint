import {
  Bell,
  CalendarClock,
  Check,
  Pause,
  Play,
  Plus,
  Trash2,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import {
  monitoringApi,
  notificationApi,
  osintApi,
  type AppNotification,
  type IdentityProfile,
  type ScanSchedule,
} from '../services/api'
import { useTranslation, type MessageKey } from '../i18n/messages'

export function MonitoringPage() {
  const { locale, t } = useTranslation()
  const [profiles, setProfiles] = useState<IdentityProfile[]>([])
  const [schedules, setSchedules] = useState<ScanSchedule[]>([])
  const [profileId, setProfileId] = useState('')
  const [cadence, setCadence] = useState<ScanSchedule['cadence']>('weekly')
  const [notifications, setNotifications] = useState<AppNotification[]>([])
  const [notifyNewMentions, setNotifyNewMentions] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [nextProfiles, nextSchedules, nextNotifications, preferences] =
        await Promise.all([
          osintApi.profiles(),
          monitoringApi.schedules(),
          notificationApi.list(),
          notificationApi.preferences(),
        ])
      setProfiles(nextProfiles)
      setSchedules(nextSchedules)
      setNotifications(nextNotifications)
      setNotifyNewMentions(preferences.notify_new_mentions)
      setProfileId((current) => current || nextProfiles[0]?.id || '')
      setError(null)
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('monitoringLoadFailed'),
      )
    }
  }, [t])

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(task)
  }, [load])

  return (
    <div className="px-4 py-8 sm:px-8 xl:px-12">
      <div className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold text-teal-700 dark:text-teal-400">
          {t('monitoringAutomation')}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          {t('monitoringTitle')}
        </h1>
        <p className="mt-3 max-w-3xl text-slate-600 dark:text-slate-300">
          {t('monitoringIntro')}
        </p>
        {error && <p className="error-message mt-5">{error}</p>}
        <section className="panel mt-8">
          <h2 className="section-title">
            <Plus className="inline" size={20} /> {t('monitoringNewSchedule')}
          </h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <label className="field-label">
              {t('monitoringProfile')}
              <select
                value={profileId}
                onChange={(event) => setProfileId(event.target.value)}
              >
                <option value="">{t('monitoringSelectProfile')}</option>
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.first_name} {profile.last_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              {t('monitoringCadence')}
              <select
                value={cadence}
                onChange={(event) =>
                  setCadence(event.target.value as ScanSchedule['cadence'])
                }
              >
                {cadenceOptions.map(([value, key]) => (
                  <option key={value} value={value}>
                    {t(key)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="primary-button"
              disabled={!profileId}
              onClick={() =>
                void monitoringApi
                  .create(profileId, cadence)
                  .then(load)
                  .catch((caught: unknown) =>
                    setError(
                      caught instanceof Error
                        ? caught.message
                        : t('monitoringCreateFailed'),
                    ),
                  )
              }
            >
              <CalendarClock size={17} /> {t('monitoringSchedule')}
            </button>
          </div>
        </section>
        <section className="panel mt-6 overflow-x-auto">
          <h2 className="section-title">{t('monitoringActiveSchedules')}</h2>
          <table className="mt-4">
            <thead>
              <tr>
                <th>{t('monitoringProfile')}</th>
                <th>{t('monitoringCadence')}</th>
                <th>{t('monitoringNextRun')}</th>
                <th>{t('monitoringState')}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {schedules.map((schedule) => (
                <tr key={schedule.id}>
                  <td>
                    {profiles.find(
                      (profile) => profile.id === schedule.profile_id,
                    )?.first_name ?? t('monitoringProfile')}
                  </td>
                  <td>{t(cadenceMessageKeys[schedule.cadence])}</td>
                  <td>
                    {new Date(schedule.next_run_at).toLocaleString(
                      locale === 'fr' ? 'fr-FR' : 'en-GB',
                    )}
                  </td>
                  <td>
                    {t(
                      schedule.enabled
                        ? 'monitoringActive'
                        : 'monitoringPaused',
                    )}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button
                        className="icon-button"
                        aria-label={t(
                          schedule.enabled
                            ? 'monitoringPause'
                            : 'monitoringResume',
                        )}
                        onClick={() =>
                          void monitoringApi
                            .setEnabled(schedule.id, !schedule.enabled)
                            .then(load)
                        }
                      >
                        {schedule.enabled ? (
                          <Pause size={16} />
                        ) : (
                          <Play size={16} />
                        )}
                      </button>
                      <button
                        className="icon-button danger"
                        aria-label={t('monitoringDeleteSchedule')}
                        onClick={() =>
                          void monitoringApi.remove(schedule.id).then(load)
                        }
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {schedules.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-500">
              {t('monitoringNoSchedules')}
            </p>
          )}
        </section>
        <div className="mt-6 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <section className="panel">
            <h2 className="section-title">
              <Bell className="inline" size={20} />{' '}
              {t('monitoringInternalAlerts')}
            </h2>
            <label className="mt-5 flex items-start gap-3 text-sm">
              <input
                className="mt-1 size-4"
                type="checkbox"
                checked={notifyNewMentions}
                onChange={(event) => {
                  const enabled = event.target.checked
                  setNotifyNewMentions(enabled)
                  void notificationApi
                    .updatePreferences(enabled)
                    .catch((caught: unknown) => {
                      setNotifyNewMentions(!enabled)
                      setError(
                        caught instanceof Error
                          ? caught.message
                          : t('monitoringUpdateFailed'),
                      )
                    })
                }}
              />
              <span>{t('monitoringNotifyNewMentions')}</span>
            </label>
            <p className="mt-3 text-xs text-slate-500">
              {t('monitoringPrivacyNote')}
            </p>
          </section>
          <section className="panel">
            <h2 className="section-title">{t('monitoringAlertHistory')}</h2>
            <div className="mt-4 space-y-3">
              {notifications.map((notification) => (
                <article
                  className="rounded-xl border border-slate-200 p-4 dark:border-slate-700"
                  key={notification.id}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold">{notification.title}</p>
                      <p className="mt-1 text-sm text-slate-500">
                        {notification.message}
                      </p>
                      <p className="mt-2 text-xs text-slate-400">
                        {new Date(notification.created_at).toLocaleString(
                          locale === 'fr' ? 'fr-FR' : 'en-GB',
                        )}
                      </p>
                    </div>
                    {!notification.read_at && (
                      <button
                        className="icon-button"
                        aria-label={`${t('monitoringMarkRead')} ${notification.title}`}
                        onClick={() =>
                          void notificationApi
                            .markRead(notification.id)
                            .then(load)
                        }
                      >
                        <Check size={16} />
                      </button>
                    )}
                  </div>
                </article>
              ))}
              {notifications.length === 0 && (
                <p className="py-6 text-center text-sm text-slate-500">
                  {t('monitoringNoAlerts')}
                </p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

const cadenceMessageKeys: Record<ScanSchedule['cadence'], MessageKey> = {
  daily: 'monitoringCadenceDaily',
  weekly: 'monitoringCadenceWeekly',
  monthly: 'monitoringCadenceMonthly',
}

const cadenceOptions = Object.entries(cadenceMessageKeys) as [
  ScanSchedule['cadence'],
  MessageKey,
][]
