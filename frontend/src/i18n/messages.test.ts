import { describe, expect, it } from 'vitest'
import { messages, translate } from './messages'

describe('interface translations', () => {
  it('provides the same translation keys for French and English', () => {
    expect(Object.keys(messages.en).sort()).toEqual(
      Object.keys(messages.fr).sort(),
    )
  })

  it('uses French as the default language content', () => {
    expect(translate('fr', 'dashboard')).toBe('Tableau de bord')
    expect(translate('en', 'dashboard')).toBe('Dashboard')
  })
})
