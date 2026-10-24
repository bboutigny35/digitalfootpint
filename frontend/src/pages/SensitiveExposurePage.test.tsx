import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SensitiveExposurePage } from './SensitiveExposurePage'
import { LocaleContext, translate } from '../i18n/messages'

describe('SensitiveExposurePage', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (
          url.endsWith('/descriptors') &&
          (!init?.method || init.method === 'GET')
        )
          return new Response('[]', { status: 200 })
        if (url.endsWith('/checks')) return new Response('[]', { status: 200 })
        if (url.endsWith('/findings'))
          return new Response('[]', { status: 200 })
        if (url.endsWith('/alerts')) return new Response('[]', { status: 200 })
        if (url.endsWith('/validate'))
          return new Response(
            JSON.stringify({
              valid: true,
              masked_value: '1 ** ** ***** *** **',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          )
        return new Response('{}', {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )
  })

  it('affiche une alerte masquée et permet sa prise en compte', async () => {
    const alert = {
      id: 'alert-1',
      finding_id: 'finding-1',
      category: 'phone',
      source_label: 'source-test-autorisée',
      risk_level: 'high',
      recommendation: 'Sécuriser le compte auprès de l’opérateur.',
      created_at: '2026-10-14T10:00:00Z',
      acknowledged_at: null,
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        if (
          url.endsWith('/alerts/alert-1/acknowledge') &&
          init?.method === 'POST'
        ) {
          return new Response(
            JSON.stringify({
              ...alert,
              acknowledged_at: '2026-10-14T11:00:00Z',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          )
        }
        if (url.endsWith('/alerts'))
          return new Response(JSON.stringify([alert]), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        return new Response('[]', { status: 200 })
      }),
    )
    const user = userEvent.setup()
    render(<SensitiveExposurePage />)
    expect(await screen.findByText('Risque élevé')).toBeInTheDocument()
    expect(screen.getByText(/sécuriser le compte/i)).toBeInTheDocument()
    await user.click(
      screen.getByRole('button', { name: 'Marquer comme traitée' }),
    )
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/sensitive-monitor/alerts/alert-1/acknowledge',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
    expect(document.body.textContent).not.toMatch(/\+33|\d{12,}/)
  })

  it('affiche les limites de détection', async () => {
    render(<SensitiveExposurePage />)
    expect(
      await screen.findByText(/absence d’alerte ne prouve pas/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/valeurs complètes ne sont ni affichées ni conservées/i),
    ).toBeInTheDocument()
  })

  it('valide un NIR dans le corps de requête sans le placer dans URL', async () => {
    const user = userEvent.setup()
    render(<SensitiveExposurePage />)
    await screen.findByText(/aucune donnée surveillée/i)
    await user.click(screen.getByRole('button', { name: 'Éphémère' }))
    const synthetic = '100019999999975'
    await user.type(screen.getByLabelText('Valeur'), synthetic)
    await user.click(
      screen.getByRole('button', { name: /valider localement/i }),
    )
    await waitFor(() =>
      expect(screen.getByText(/format valide/i)).toBeInTheDocument(),
    )
    const calls = vi.mocked(fetch).mock.calls
    const validation = calls.find(([url]) => String(url).endsWith('/validate'))
    expect(String(validation?.[0])).not.toContain(synthetic)
    expect(String(validation?.[1]?.body)).toContain(synthetic)
    expect(document.body.textContent).not.toContain(synthetic)
  })

  it('traduit la page en anglais sans révéler de valeur complète', async () => {
    render(
      <LocaleContext.Provider
        value={{ locale: 'en', t: (key) => translate('en', key) }}
      >
        <SensitiveExposurePage />
      </LocaleContext.Provider>,
    )
    expect(
      await screen.findByRole('heading', { name: 'Sensitive data exposure' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Monitored items' }),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Card' }))
    expect(screen.getByText(/Never enter the full number/)).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('100019999999975')
  })
})
