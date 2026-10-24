import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ReportsPage } from './ReportsPage'

it('télécharge un rapport synthétique sans placer de donnée dans URL', async () => {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      void init
      if (String(input).endsWith('/reports')) {
        return new Response('[]', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(new Blob(['%PDF-synthetic']), {
        status: 200,
        headers: {
          'Content-Disposition':
            'attachment; filename="digitalfootprint-summary.pdf"',
        },
      })
    },
  )
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:synthetic-report'),
    revokeObjectURL: vi.fn(),
  })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(
    () => undefined,
  )
  const user = userEvent.setup()
  render(<ReportsPage />)

  await user.click(screen.getByRole('button', { name: 'Synthétique' }))
  await user.click(screen.getByRole('button', { name: 'pdf' }))

  expect(fetchMock).toHaveBeenCalledWith(
    '/api/v1/reports/export?format=pdf&kind=summary',
    { credentials: 'include' },
  )
  expect(
    fetchMock.mock.calls.every(([url]) => !String(url).includes('Alice')),
  ).toBe(true)
})
