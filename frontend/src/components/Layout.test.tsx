import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Layout } from './Layout'
import { ReportsPage } from '../pages/ReportsPage'

describe('Layout language preference', () => {
  beforeEach(() => window.localStorage.clear())

  it('switches navigation language and persists the choice', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('[]', {
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    render(
      <Layout
        userEmail="test@example.invalid"
        isAdmin={false}
        onLogout={vi.fn()}
        activePage="identities"
        onNavigate={vi.fn()}
      >
        <ReportsPage />
      </Layout>,
    )

    fireEvent.change(screen.getAllByLabelText('Langue')[0], {
      target: { value: 'en' },
    })

    expect(screen.getByRole('button', { name: 'Dashboard' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Reports' })).toBeTruthy()
    expect(window.localStorage.getItem('digitalfootprint.locale')).toBe('en')
    expect(document.documentElement.lang).toBe('en')
  })
})
