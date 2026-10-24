import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { setCsrfToken } from '../services/api'
import { MonitoringPage } from './MonitoringPage'
import { LocaleContext, translate } from '../i18n/messages'

it('crée une surveillance GitHub hebdomadaire avec CSRF', async () => {
  const calls: Array<[string, RequestInit | undefined]> = []
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      calls.push([url, init])
      if (url.endsWith('/profiles')) {
        return Response.json([
          {
            id: 'profile-1',
            first_name: 'Alice',
            last_name: 'Martin',
            pseudonyms: ['alice'],
            created_at: '2026-10-15T06:00:00Z',
            updated_at: '2026-10-15T06:00:00Z',
          },
        ])
      }
      if (url.endsWith('/schedules') && init?.method === 'POST') {
        return Response.json({ id: 'schedule-1' }, { status: 201 })
      }
      if (url.endsWith('/notifications/preferences')) {
        return Response.json({ notify_new_mentions: true })
      }
      return Response.json([])
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  setCsrfToken('synthetic-csrf')
  const user = userEvent.setup()
  render(<MonitoringPage />)

  await screen.findByText('Alice Martin')
  await user.click(screen.getByRole('button', { name: 'Planifier' }))

  const creation = calls.find(
    ([url, init]) => url.endsWith('/schedules') && init?.method === 'POST',
  )
  expect(JSON.parse(String(creation?.[1]?.body))).toEqual({
    profile_id: 'profile-1',
    connector_ids: ['github'],
    cadence: 'weekly',
    external_search_consent: false,
  })
  expect(new Headers(creation?.[1]?.headers).get('X-CSRF-Token')).toBe(
    'synthetic-csrf',
  )
})

it('permet de désactiver les alertes de nouvelles mentions', async () => {
  const calls: Array<[string, RequestInit | undefined]> = []
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      calls.push([url, init])
      if (url.endsWith('/notifications/preferences')) {
        return Response.json({ notify_new_mentions: init?.method !== 'PATCH' })
      }
      return Response.json([])
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  setCsrfToken('synthetic-csrf')
  const user = userEvent.setup()
  render(<MonitoringPage />)

  const checkbox = await screen.findByRole('checkbox')
  await user.click(checkbox)

  const update = calls.find(
    ([url, init]) =>
      url.endsWith('/notifications/preferences') && init?.method === 'PATCH',
  )
  expect(JSON.parse(String(update?.[1]?.body))).toEqual({
    notify_new_mentions: false,
  })
  expect(new Headers(update?.[1]?.headers).get('X-CSRF-Token')).toBe(
    'synthetic-csrf',
  )
})

it('traduit les contrôles de surveillance en anglais', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/notifications/preferences')) {
        return Response.json({ notify_new_mentions: true })
      }
      return Response.json([])
    }),
  )
  render(
    <LocaleContext.Provider
      value={{ locale: 'en', t: (key) => translate('en', key) }}
    >
      <MonitoringPage />
    </LocaleContext.Provider>,
  )

  expect(
    await screen.findByRole('heading', { name: 'Monitoring' }),
  ).toBeInTheDocument()
  expect(
    screen.getByRole('heading', { name: 'Active schedules' }),
  ).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Schedule' })).toBeDisabled()
})
