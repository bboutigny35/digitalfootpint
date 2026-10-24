import { expect, test } from '@playwright/test'
import { readFile } from 'node:fs/promises'

test('initialise l’instance et crée un profil d’identité', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('button', { name: 'Première utilisation' }).click()
  await page.getByLabel('Adresse e-mail').fill('admin.e2e@example.com')
  await page.getByLabel('Mot de passe').fill('E2e-Only-Password-2026!')
  const bootstrapResponse = page.waitForResponse((response) =>
    response.url().endsWith('/api/v1/auth/bootstrap'),
  )
  await page.getByRole('button', { name: 'Initialiser l’instance' }).click()
  const bootstrap = await bootstrapResponse
  expect(bootstrap.status(), await bootstrap.text()).toBe(201)

  await expect(page.getByRole('heading', { name: 'Identités' })).toBeVisible()
  await page.getByLabel('Prénom').fill('Alice')
  await page.getByLabel('Nom', { exact: true }).fill('Exemple')
  await page
    .getByLabel('Pseudonymes séparés par des virgules')
    .fill('alice-test, aexemple')
  await page.getByRole('button', { name: 'Créer le profil' }).click()

  const profiles = page.getByRole('heading', { name: 'Profils enregistrés' })
  await expect(profiles.locator('..')).toContainText('Alice Exemple')
  await expect(profiles.locator('..')).toContainText('alice-test, aexemple')

  await page.getByRole('button', { name: 'Tableau de bord' }).click()
  await expect(
    page.getByRole('heading', { name: 'Tableau de bord' }),
  ).toBeVisible()
  await expect(page.getByText('1', { exact: true }).first()).toBeVisible()

  await page.getByRole('button', { name: 'Recherches' }).click()
  await page.getByLabel('Sélectionner un connecteur').selectOption('brave')
  await expect(page.getByRole('note')).toContainText('Brave Search')
  const pendingScanRequests: string[] = []
  page.on('request', (request) => {
    if (
      request.url().endsWith('/api/v1/scans') &&
      request.method() === 'POST'
    ) {
      pendingScanRequests.push(request.url())
    }
  })
  const confirmation = page.waitForEvent('dialog')
  const startBrave = page.getByRole('button', { name: 'Démarrer' }).click()
  const braveDisclosure = await confirmation
  expect(braveDisclosure.message()).toContain('Brave Search')
  await braveDisclosure.dismiss()
  await startBrave
  expect(pendingScanRequests).toEqual([])

  await page.getByLabel('Sélectionner un connecteur').selectOption('mock')
  const scanResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/scans') &&
      response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Démarrer' }).click()
  const scan = (await (await scanResponse).json()) as { id: string }

  await expect
    .poll(
      () =>
        page.evaluate(async (scanId) => {
          const response = await fetch(`/api/v1/scans/${scanId}`)
          return ((await response.json()) as { status: string }).status
        }, scan.id),
      { timeout: 15_000 },
    )
    .toBe('completed')

  await page.getByRole('button', { name: 'Résultats' }).click()
  const resultTitle = 'Profil public de alice-test'
  await expect(page.getByRole('link', { name: resultTitle })).toBeVisible()
  const validation = page.getByLabel(`Validation de ${resultTitle}`)
  await validation.selectOption('confirmed')
  await expect(validation).toHaveValue('confirmed')

  await page.getByRole('button', { name: 'Rapports' }).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'csv', exact: true }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(/\.csv$/)
  const path = await download.path()
  expect(path).not.toBeNull()
  expect(await readFile(path!, 'utf8')).toContain(resultTitle)
  await expect(
    page.getByRole('cell', { name: 'csv', exact: true }),
  ).toBeVisible()

  await page.getByRole('button', { name: 'Administration' }).click()
  page.once('dialog', (dialog) => dialog.accept())
  const backupPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Télécharger une sauvegarde' }).click()
  const backup = await backupPromise
  expect(backup.suggestedFilename()).toMatch(
    /digitalfootprint-backup-.*\.tar\.gz$/,
  )
  const backupPath = await backup.path()
  expect(backupPath).not.toBeNull()
  const backupBytes = await readFile(backupPath!)
  expect([...backupBytes.subarray(0, 2)]).toEqual([0x1f, 0x8b])
})
