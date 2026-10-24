import { FilePenLine, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  osintApi,
  removalApi,
  type OsintResult,
  type RemovalLetter,
  type RemovalRequest,
  type RemovalRequestStatus,
} from '../services/api'
import { useTranslation, type MessageKey } from '../i18n/messages'

export function RemovalRequestsPage() {
  const { locale, t } = useTranslation()
  const [requests, setRequests] = useState<RemovalRequest[]>([])
  const [results, setResults] = useState<OsintResult[]>([])
  const [organization, setOrganization] = useState('')
  const [resultId, setResultId] = useState('')
  const [notes, setNotes] = useState('')
  const [letter, setLetter] = useState<RemovalLetter | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [nextRequests, nextResults] = await Promise.all([
        removalApi.list(),
        osintApi.results(),
      ])
      setRequests(nextRequests)
      setResults(nextResults)
      setError(null)
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('removalLoadFailed'),
      )
    }
  }, [t])

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(task)
  }, [load])

  async function create(event: FormEvent) {
    event.preventDefault()
    try {
      await removalApi.create(organization, resultId || null, notes)
      setOrganization('')
      setResultId('')
      setNotes('')
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('removalCreateFailed'),
      )
    }
  }

  return (
    <div className="px-4 py-8 sm:px-8 xl:px-12">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-semibold text-teal-700 dark:text-teal-400">
          {t('removalRights')}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          {t('removalTitle')}
        </h1>
        <p className="mt-3 max-w-3xl text-slate-600 dark:text-slate-300">
          {t('removalIntro')}
        </p>
        {error && <p className="error-message mt-5">{error}</p>}
        <div className="mt-8 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <form
            className="panel space-y-4"
            onSubmit={(event) => void create(event)}
          >
            <h2 className="section-title">
              <Plus className="inline" size={20} /> {t('removalNew')}
            </h2>
            <label className="field-label">
              {t('removalOrganization')}
              <input
                required
                maxLength={255}
                value={organization}
                onChange={(event) => setOrganization(event.target.value)}
              />
            </label>
            <label className="field-label">
              {t('removalAssociatedMention')}
              <select
                value={resultId}
                onChange={(event) => setResultId(event.target.value)}
              >
                <option value="">{t('removalNoMention')}</option>
                {results.map((result) => (
                  <option key={result.id} value={result.id}>
                    {result.title} — {result.domain}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              {t('removalNotes')}
              <textarea
                maxLength={5000}
                rows={4}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
            </label>
            <button className="primary-button">
              {t('removalCreateDraft')}
            </button>
          </form>
          <section className="panel overflow-x-auto">
            <h2 className="section-title">{t('removalTracked')}</h2>
            <table className="mt-4">
              <thead>
                <tr>
                  <th>{t('removalOrganization')}</th>
                  <th>{t('removalStatus')}</th>
                  <th>{t('removalUpdated')}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {requests.map((item) => (
                  <tr key={item.id}>
                    <td>{item.organization}</td>
                    <td>
                      <select
                        aria-label={`${t('removalStatusFor')} ${item.organization}`}
                        value={item.status}
                        onChange={(event) =>
                          void removalApi
                            .updateStatus(
                              item.id,
                              event.target.value as RemovalRequestStatus,
                            )
                            .then(load)
                        }
                      >
                        {statusOptions.map(([value, key]) => (
                          <option key={value} value={value}>
                            {t(key)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      {new Date(item.updated_at).toLocaleDateString(
                        locale === 'fr' ? 'fr-FR' : 'en-GB',
                      )}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button
                          className="icon-button"
                          aria-label={`${t('removalPrepareLetterFor')} ${item.organization}`}
                          onClick={() =>
                            void removalApi.letter(item.id).then(setLetter)
                          }
                        >
                          <FilePenLine size={16} />
                        </button>
                        <button
                          className="icon-button danger"
                          aria-label={`${t('removalDeleteRequestFor')} ${item.organization}`}
                          onClick={() =>
                            void removalApi.remove(item.id).then(load)
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
            {requests.length === 0 && (
              <p className="py-8 text-center text-sm text-slate-500">
                {t('removalEmpty')}
              </p>
            )}
          </section>
        </div>
        {letter && (
          <section className="panel mt-6">
            <h2 className="section-title">{letter.subject}</h2>
            <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
              {letter.warning}
            </p>
            <pre className="mt-4 whitespace-pre-wrap font-sans text-sm">
              {letter.body}
            </pre>
          </section>
        )}
      </div>
    </div>
  )
}

const statusOptions: [RemovalRequestStatus, MessageKey][] = [
  ['draft', 'removalStatusDraft'],
  ['sent', 'removalStatusSent'],
  ['acknowledged', 'removalStatusAcknowledged'],
  ['completed', 'removalStatusCompleted'],
  ['rejected', 'removalStatusRejected'],
  ['cancelled', 'removalStatusCancelled'],
]
