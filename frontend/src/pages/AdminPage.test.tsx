import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { AdminPage } from './AdminPage'
import { LocaleContext, translate } from '../i18n/messages'

it('affiche uniquement les métadonnées administratives non sensibles', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/admin/overview')) {
      return Response.json({
        application_version: '0.1.0-dev',
        environment: 'test',
        database_backend: 'sqlite',
        cookie_secure: false,
        github_token_configured: true,
        backup_command_available: true,
      })
    }
    if (url.endsWith('/connectors')) {
      return Response.json([
        {
          identifier: 'github',
          version: '1.0',
          enabled: true,
          health: 'available',
          result_count: 4,
          error_count: 0,
        },
      ])
    }
    if (url.endsWith('/admin/connector-secrets')) {
      return Response.json([
        {
          connector_id: 'github',
          configured: true,
          key_version: 'v1',
          updated_at: '2026-10-15T10:00:00Z',
        },
      ])
    }
    if (url.endsWith('/admin/platform-catalog')) {
      return Response.json([
        {
          identifier: 'netflix',
          display_name: 'Netflix',
          category: 'streaming',
          verification_method: 'none',
          default_status: 'NOT_VERIFIABLE',
          connector_id: null,
          priority: 200,
          limitations: 'No public account directory.',
          last_checked_at: null,
          last_error_code: null,
        },
      ])
    }
    if (url.endsWith('/admin/web-sources')) return Response.json([])
    return Response.json({
      items: [
        {
          id: 'event-1',
          actor_id: 'user-1',
          action: 'profile.update',
          resource_type: 'profile',
          resource_id: 'profile-1',
          details: {},
          created_at: '2026-10-15T10:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
      pages: 1,
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<AdminPage />)

  expect(await screen.findByText('0.1.0-dev')).toBeInTheDocument()
  expect(screen.getByText('Configuré')).toBeInTheDocument()
  expect(screen.getByText('profile.update')).toBeInTheDocument()
  expect(
    screen.queryByText(/token-value|database_url/i),
  ).not.toBeInTheDocument()
})

it('traduit les libellés administratifs en anglais', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/admin/overview')) {
        return Response.json({
          application_version: '0.1.0-dev',
          environment: 'test',
          database_backend: 'sqlite',
          cookie_secure: true,
          github_token_configured: false,
          backup_command_available: true,
        })
      }
      if (String(input).endsWith('/admin/connector-secrets')) {
        return Response.json([])
      }
      if (String(input).includes('/admin/audit-events?')) {
        return Response.json({
          items: [],
          total: 0,
          page: 1,
          page_size: 50,
          pages: 1,
        })
      }
      return Response.json([])
    }),
  )
  render(
    <LocaleContext.Provider
      value={{ locale: 'en', t: (key) => translate('en', key) }}
    >
      <AdminPage />
    </LocaleContext.Provider>,
  )

  expect(
    await screen.findByRole('heading', { name: 'Administration' }),
  ).toBeInTheDocument()
  expect(await screen.findByText('0.1.0-dev')).toBeInTheDocument()
  expect(
    screen.getByRole('heading', { name: 'Connectors' }),
  ).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Backups' })).toBeInTheDocument()
  expect(screen.getByText('Enabled')).toBeInTheDocument()
})
