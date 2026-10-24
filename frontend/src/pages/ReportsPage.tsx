import { Download, FileText } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { reportApi, type ReportExport } from '../services/api'
import { useTranslation } from '../i18n/messages'

const formats = ['csv', 'json', 'xlsx', 'html', 'pdf'] as const

export function ReportsPage() {
  const { locale, t } = useTranslation()
  const [kind, setKind] = useState<'summary' | 'detailed'>('detailed')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [history, setHistory] = useState<ReportExport[]>([])

  const loadHistory = useCallback(async () => {
    try {
      setHistory(await reportApi.history())
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : t('reportHistoryUnavailable'),
      )
    }
  }, [t])

  useEffect(() => {
    const task = window.setTimeout(() => void loadHistory(), 0)
    return () => window.clearTimeout(task)
  }, [loadHistory])

  async function exportReport(format: (typeof formats)[number]) {
    setBusy(format)
    setError(null)
    try {
      const { blob, filename } = await reportApi.download(format, kind)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename
      link.click()
      URL.revokeObjectURL(objectUrl)
      await loadHistory()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('reportExportFailed'),
      )
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="px-4 py-8 sm:px-8 xl:px-12">
      <div className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold text-teal-700 dark:text-teal-400">
          {t('reportDocumentation')}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          {t('reportTitle')}
        </h1>
        <p className="mt-3 max-w-3xl text-slate-600 dark:text-slate-300">
          {t('reportIntro')}
        </p>
        {error && <p className="error-message mt-5">{error}</p>}
        <section className="panel mt-8">
          <div className="flex items-center gap-3">
            <FileText className="text-teal-700" />
            <div>
              <h2 className="section-title">{t('reportDetailLevel')}</h2>
              <p className="section-copy">{t('reportSummaryDescription')}</p>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
            {(
              [
                ['summary', t('reportSummary')],
                ['detailed', t('reportDetailed')],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                className={`rounded-lg px-3 py-2 text-sm font-semibold ${kind === value ? 'bg-white shadow-sm dark:bg-slate-700' : ''}`}
                onClick={() => setKind(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {formats.map((format) => (
              <button
                key={format}
                className="secondary-button uppercase"
                disabled={busy !== null}
                onClick={() => void exportReport(format)}
              >
                <Download size={17} />
                {busy === format ? t('reportCreating') : format}
              </button>
            ))}
          </div>
          <p className="notice mt-6">{t('reportCaveat')}</p>
        </section>
        <section className="panel mt-6 overflow-x-auto">
          <h2 className="section-title">{t('reportHistory')}</h2>
          <p className="section-copy">{t('reportMetadataOnly')}</p>
          <table className="mt-4">
            <thead>
              <tr>
                <th>{t('reportDate')}</th>
                <th>{t('reportFormat')}</th>
                <th>{t('reportType')}</th>
                <th>{t('reportResults')}</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.id}>
                  <td>
                    {new Date(item.created_at).toLocaleString(
                      locale === 'fr' ? 'fr-FR' : 'en-GB',
                    )}
                  </td>
                  <td className="uppercase">{item.export_format}</td>
                  <td>
                    {item.report_kind === 'summary'
                      ? t('reportSummary')
                      : t('reportDetailed')}
                  </td>
                  <td>{item.result_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {history.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-500">
              {t('reportEmpty')}
            </p>
          )}
        </section>
      </div>
    </div>
  )
}
