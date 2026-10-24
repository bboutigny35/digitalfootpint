import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { setCsrfToken } from '../services/api'
import { OsintWorkspacePage } from './OsintWorkspacePage'
import { LocaleContext, translate } from '../i18n/messages'

it('lance uniquement le connecteur GitHub pour le profil sélectionné', async () => {
  const calls: Array<[string, RequestInit | undefined]> = []
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      calls.push([url, init])
      let body: object = []
      if (url.endsWith('/profiles')) {
        body = [
          {
            id: 'profile-1',
            first_name: 'Alice',
            last_name: 'Martin',
            pseudonyms: ['alice-public'],
            created_at: '2026-10-14T20:00:00Z',
            updated_at: '2026-10-14T20:00:00Z',
          },
        ]
      } else if (url.endsWith('/connectors')) {
        body = [
          {
            identifier: 'github',
            version: '1.0',
            capabilities: ['public_profiles'],
            accepted_identifiers: ['pseudonym'],
            enabled: true,
            health: 'not_checked',
            rate_limit_per_minute: 1,
            quota_status: 'provider_managed',
            last_scan_at: null,
            result_count: 0,
            error_count: 0,
          },
        ]
      } else if (url.endsWith('/scans') && init?.method === 'POST') {
        body = {
          id: 'scan-1',
          profile_id: 'profile-1',
          status: 'queued',
          connector_ids: ['github'],
          progress: 0,
          error_code: null,
          created_at: '2026-10-14T20:00:00Z',
        }
      }
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  setCsrfToken('synthetic-csrf')
  const user = userEvent.setup()
  render(<OsintWorkspacePage section="scans" />)

  await screen.findByText('Alice Martin')
  expect(
    screen.getByRole('button', { name: 'Recherche globale' }),
  ).toBeDisabled()
  expect(screen.getByRole('status')).toHaveTextContent(
    'Aucun moteur Web généraliste n’est prêt',
  )
  await user.click(screen.getByRole('button', { name: 'Démarrer' }))

  const scanCall = calls.find(
    ([url, init]) => url.endsWith('/scans') && init?.method === 'POST',
  )
  expect(scanCall).toBeDefined()
  expect(JSON.parse(String(scanCall?.[1]?.body))).toEqual({
    profile_id: 'profile-1',
    connector_ids: ['github'],
    external_search_consent: false,
  })
  expect(new Headers(scanCall?.[1]?.headers).get('X-CSRF-Token')).toBe(
    'synthetic-csrf',
  )
})

it('lance les sources configurées pertinentes avec la recherche globale', async () => {
  const calls: Array<[string, RequestInit | undefined]> = []
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      calls.push([url, init])
      let body: object = []
      if (url.endsWith('/profiles')) {
        body = [
          {
            id: 'profile-global',
            first_name: 'Alice',
            last_name: 'Martin',
            pseudonyms: ['alice-public'],
            domains: [],
            websites: [],
            created_at: '2026-10-14T20:00:00Z',
            updated_at: '2026-10-14T20:00:00Z',
          },
        ]
      } else if (url.endsWith('/connectors')) {
        body = [
          {
            identifier: 'brave',
            version: '1.0',
            capabilities: ['web_search'],
            accepted_identifiers: ['name', 'pseudonym'],
            enabled: true,
            ready: true,
            health: 'not_checked',
            rate_limit_per_minute: 5,
            quota_status: 'provider_managed',
            last_scan_at: null,
            result_count: 0,
            error_count: 0,
          },
          {
            identifier: 'github',
            version: '1.0',
            capabilities: ['public_profiles'],
            accepted_identifiers: ['pseudonym'],
            enabled: true,
            ready: true,
            health: 'not_checked',
            rate_limit_per_minute: 10,
            quota_status: 'provider_managed',
            last_scan_at: null,
            result_count: 0,
            error_count: 0,
          },
          {
            identifier: 'searxng',
            version: '1.0',
            capabilities: ['web_search'],
            accepted_identifiers: ['name', 'pseudonym'],
            enabled: true,
            ready: true,
            health: 'not_checked',
            rate_limit_per_minute: 5,
            quota_status: 'provider_managed',
            last_scan_at: null,
            result_count: 0,
            error_count: 0,
          },
        ]
      } else if (url.endsWith('/scans') && init?.method === 'POST') {
        body = {
          id: 'global-scan',
          profile_id: 'profile-global',
          status: 'queued',
          connector_ids: ['brave', 'github', 'searxng'],
          progress: 0,
          error_code: null,
          created_at: '2026-10-14T20:00:00Z',
        }
      }
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  setCsrfToken('synthetic-csrf')
  const user = userEvent.setup()
  render(<OsintWorkspacePage section="scans" />)

  await screen.findByText('Alice Martin')
  await user.click(screen.getByRole('button', { name: 'Recherche globale' }))

  const scanCall = calls.find(
    ([url, init]) => url.endsWith('/scans') && init?.method === 'POST',
  )
  expect(JSON.parse(String(scanCall?.[1]?.body))).toEqual({
    profile_id: 'profile-global',
    connector_ids: ['brave', 'github', 'searxng'],
    external_search_consent: true,
  })
  expect(window.confirm).toHaveBeenCalledTimes(2)
})

it('compare deux scans terminés sans présenter une absence comme supprimée', async () => {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      let body: object = []
      if (url.endsWith('/profiles')) {
        body = []
      } else if (url.endsWith('/connectors')) {
        body = []
      } else if (url.endsWith('/scans') && !init?.method) {
        body = [
          {
            id: 'scan-current',
            profile_id: 'profile-1',
            status: 'completed',
            connector_ids: ['github'],
            progress: 1,
            error_code: null,
            created_at: '2026-10-15T10:00:00Z',
          },
          {
            id: 'scan-baseline',
            profile_id: 'profile-1',
            status: 'completed',
            connector_ids: ['github'],
            progress: 1,
            error_code: null,
            created_at: '2026-10-14T10:00:00Z',
          },
        ]
      } else if (url.includes('/scans/compare/results?')) {
        body = {
          baseline_scan_id: 'scan-baseline',
          current_scan_id: 'scan-current',
          profile_id: 'profile-1',
          counts: {
            new: 0,
            known: 0,
            modified: 0,
            inaccessible: 0,
            not_reverified: 1,
            excluded_false_positive: 0,
          },
          items: [],
          methodology_note:
            "Une URL absente n'est jamais considérée comme supprimée.",
        }
      }
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<OsintWorkspacePage section="scans" />)

  await screen.findByText('Comparer deux recherches')
  await waitFor(() =>
    expect(
      screen.getByLabelText<HTMLSelectElement>('Scan de référence').options,
    ).toHaveLength(3),
  )
  await user.selectOptions(
    screen.getByLabelText('Scan de référence'),
    'scan-baseline',
  )
  await user.selectOptions(screen.getByLabelText('Scan récent'), 'scan-current')
  await user.click(screen.getByRole('button', { name: 'Comparer' }))

  expect(
    await screen.findByText(
      "Une URL absente n'est jamais considérée comme supprimée.",
    ),
  ).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(
      'baseline_scan_id=scan-baseline&current_scan_id=scan-current',
    ),
    expect.objectContaining({ credentials: 'include' }),
  )
})

it('affiche les contrôles de plateformes sans interpréter un résultat négatif', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    let body: object = []
    if (url.endsWith('/scans')) {
      body = [
        {
          id: 'scan-platforms',
          profile_id: 'profile-1',
          status: 'completed',
          connector_ids: ['bluesky'],
          progress: 1,
          error_code: null,
          created_at: '2026-10-24T10:00:00Z',
        },
      ]
    } else if (url.endsWith('/scans/scan-platforms/platform-checks')) {
      body = {
        scan_id: 'scan-platforms',
        items: [
          {
            platform_identifier: 'bluesky',
            connector_id: 'bluesky',
            verification_method: 'official_api',
            status: 'NO_PUBLIC_RESULT',
            result_count: 0,
            error_code: null,
            checked_at: '2026-10-24T10:01:00Z',
          },
        ],
        methodology_note:
          "Aucun résultat public ne prouve pas l'absence d'un compte.",
      }
    }
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<OsintWorkspacePage section="scans" />)

  await user.click(await screen.findByRole('button', { name: 'Contrôles' }))

  expect(await screen.findByText('Contrôles des plateformes')).toBeVisible()
  expect(screen.getAllByText('bluesky')).toHaveLength(2)
  expect(screen.getByText('Aucun résultat public observé')).toBeVisible()
  expect(
    screen.getByText(
      "Aucun résultat public ne prouve pas l'absence d'un compte.",
    ),
  ).toBeVisible()
})

it('filtre les résultats avec une pagination serveur', async () => {
  const calls: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    calls.push(url)
    if (url.includes('/results/search?')) {
      return Response.json({
        items: [],
        total: 0,
        page: 1,
        page_size: 25,
        pages: 0,
      })
    }
    return Response.json([])
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<OsintWorkspacePage section="results" />)

  await user.type(
    await screen.findByLabelText('Filtrer par domaine'),
    'github.com',
  )
  await user.selectOptions(
    screen.getByLabelText('Filtrer par statut'),
    'confirmed',
  )
  await user.click(screen.getByRole('button', { name: 'Filtrer' }))

  await waitFor(() =>
    expect(calls).toContainEqual(
      expect.stringContaining(
        'domain=github.com&verification_status=confirmed',
      ),
    ),
  )
})

it('modifie tous les critères d’un profil avec CSRF', async () => {
  const calls: Array<[string, RequestInit | undefined]> = []
  const profile = {
    id: 'profile-1',
    first_name: 'Alice',
    last_name: 'Martin',
    name_variants: ['Alice M.'],
    pseudonyms: ['alice'],
    emails: ['alice@example.test'],
    domains: ['example.test'],
    websites: ['https://example.test'],
    social_profiles: ['https://social.example.test/alice'],
    keywords: ['développement'],
    context: 'Lyon',
    created_at: '2026-10-15T10:00:00Z',
    updated_at: '2026-10-15T10:00:00Z',
  }
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      calls.push([url, init])
      if (url.endsWith('/profiles')) return Response.json([profile])
      if (url.endsWith('/profiles/profile-1') && init?.method === 'PUT') {
        return Response.json({ ...profile, ...JSON.parse(String(init.body)) })
      }
      return Response.json([])
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  setCsrfToken('synthetic-csrf')
  const user = userEvent.setup()
  render(<OsintWorkspacePage section="identities" />)

  await user.click(
    await screen.findByRole('button', { name: 'Modifier Alice Martin' }),
  )
  const context = screen.getByLabelText(
    'Contexte pour distinguer les homonymes',
  )
  await user.clear(context)
  await user.type(context, 'Lyon, développeuse Python')
  await user.click(
    screen.getByRole('button', { name: 'Enregistrer les modifications' }),
  )

  await waitFor(() =>
    expect(
      calls.find(
        ([url, init]) =>
          url.endsWith('/profiles/profile-1') && init?.method === 'PUT',
      ),
    ).toBeDefined(),
  )
  const update = calls.find(
    ([url, init]) =>
      url.endsWith('/profiles/profile-1') && init?.method === 'PUT',
  )
  const payload = JSON.parse(String(update?.[1]?.body)) as Record<
    string,
    unknown
  >
  expect(payload).toMatchObject({
    name_variants: ['Alice M.'],
    emails: ['alice@example.test'],
    domains: ['example.test'],
    context: 'Lyon, développeuse Python',
  })
  expect(new Headers(update?.[1]?.headers).get('X-CSRF-Token')).toBe(
    'synthetic-csrf',
  )
})

it('affiche les agrégats complets et le graphique du tableau de bord', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/dashboard')) {
      return Response.json({
        total_mentions: 1250,
        total_domains: 42,
        total_profiles: 3,
        new_mentions_7d: 7,
        needs_verification: 12,
        evolution: [
          { date: '2026-10-14', mentions: 2 },
          { date: '2026-10-15', mentions: 5 },
        ],
      })
    }
    return Response.json([])
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<OsintWorkspacePage section="dashboard" />)

  expect(await screen.findByText('1250')).toBeInTheDocument()
  expect(screen.getByText('nouvelles sur 7 jours')).toBeInTheDocument()
  expect(
    screen.getByRole('img', {
      name: 'Évolution des mentions sur 30 jours, 7 mention(s)',
    }),
  ).toBeInTheDocument()
})

it('traduit les vues du tableau de bord et des profils en anglais', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).endsWith('/dashboard')) {
      return Response.json({
        total_mentions: 0,
        total_domains: 0,
        total_profiles: 0,
        new_mentions_7d: 0,
        needs_verification: 0,
        evolution: [],
      })
    }
    return Response.json([])
  })
  vi.stubGlobal('fetch', fetchMock)
  const { rerender } = render(
    <LocaleContext.Provider
      value={{ locale: 'en', t: (key) => translate('en', key) }}
    >
      <OsintWorkspacePage section="dashboard" />
    </LocaleContext.Provider>,
  )

  expect(
    await screen.findByRole('heading', { name: 'Dashboard' }),
  ).toBeInTheDocument()
  expect(screen.getByText('public mentions')).toBeInTheDocument()
  expect(screen.getByText('No trend data.')).toBeInTheDocument()

  rerender(
    <LocaleContext.Provider
      value={{ locale: 'en', t: (key) => translate('en', key) }}
    >
      <OsintWorkspacePage section="identities" />
    </LocaleContext.Provider>,
  )
  expect(
    await screen.findByRole('heading', { name: 'Identities' }),
  ).toBeInTheDocument()
  expect(
    screen.getByRole('heading', { name: 'New profile' }),
  ).toBeInTheDocument()
})
