import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { RemovalRequestsPage } from './RemovalRequestsPage'
import { LocaleContext, translate } from '../i18n/messages'

it('prépare un courrier sans proposer d’envoi automatique', async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    let body: object = []
    if (url.endsWith('/removal-requests')) {
      body = [
        {
          id: 'request-1',
          result_id: null,
          organization: 'Exemple SARL',
          status: 'draft',
          requested_at: null,
          response_at: null,
          notes: null,
          response_notes: null,
          created_at: '2026-10-15T10:00:00Z',
          updated_at: '2026-10-15T10:00:00Z',
        },
      ]
    } else if (url.endsWith('/removal-requests/request-1/letter')) {
      body = {
        request_id: 'request-1',
        subject: "Demande d'effacement de données personnelles",
        body: "À l'attention de Exemple SARL",
        warning:
          "Modèle à vérifier et envoyer manuellement. Aucun envoi automatique n'est effectué.",
      }
    }
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<RemovalRequestsPage />)

  await user.click(
    await screen.findByRole('button', {
      name: 'Préparer le courrier pour Exemple SARL',
    }),
  )

  expect(
    await screen.findByText(/Aucun envoi automatique n'est effectué/),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: /envoyer/i }),
  ).not.toBeInTheDocument()
})

it('traduit le suivi des demandes lorsque l’interface est en anglais', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response('[]', { headers: { 'Content-Type': 'application/json' } }),
      ),
  )
  render(
    <LocaleContext.Provider
      value={{ locale: 'en', t: (key) => translate('en', key) }}
    >
      <RemovalRequestsPage />
    </LocaleContext.Provider>,
  )

  expect(
    await screen.findByRole('heading', { name: 'Removal requests' }),
  ).toBeInTheDocument()
  expect(
    screen.getByRole('heading', { name: 'Tracked requests' }),
  ).toBeInTheDocument()
})
