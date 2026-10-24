import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { AuthPage } from './AuthPage'

beforeEach(() => window.localStorage.clear())

it('ouvre une session sans exposer le mot de passe dans URL', async () => {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      void input
      void init
      return new Response(
        JSON.stringify({
          user: { id: 'user-1', email: 'admin@example.test', is_admin: true },
          csrf_token: 'synthetic-csrf-token',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  const authenticated = vi.fn()
  const user = userEvent.setup()
  render(<AuthPage onAuthenticated={authenticated} />)

  await user.type(screen.getByLabelText('Adresse e-mail'), 'admin@example.test')
  const password = 'synthetic-password'
  await user.type(screen.getByLabelText('Mot de passe'), password)
  await user.click(screen.getByRole('button', { name: 'Connexion' }))

  expect(authenticated).toHaveBeenCalledWith(
    expect.objectContaining({ email: 'admin@example.test' }),
  )
  const [url, init] = fetchMock.mock.calls[0]
  expect(String(url)).toBe('/api/v1/auth/login')
  expect(String(url)).not.toContain(password)
  expect(String(init?.body)).toContain(password)
  expect(document.body.textContent).not.toContain(password)
})

it('permet de choisir la langue avant connexion et traduit le bootstrap', async () => {
  const user = userEvent.setup()
  render(<AuthPage onAuthenticated={vi.fn()} />)

  await user.selectOptions(screen.getByLabelText('Langue'), 'en')
  expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  expect(screen.getByLabelText('Email address')).toBeInTheDocument()
  expect(window.localStorage.getItem('digitalfootprint.locale')).toBe('en')
  expect(document.documentElement.lang).toBe('en')

  await user.click(
    screen.getByRole('button', { name: 'First time here? Initialize' }),
  )
  expect(
    screen.getByRole('heading', { name: 'Create administrator account' }),
  ).toBeInTheDocument()
  expect(
    screen.getByRole('button', { name: 'Initialize instance' }),
  ).toBeInTheDocument()
})
