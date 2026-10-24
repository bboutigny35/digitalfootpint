import {
  ExternalLink,
  Pencil,
  Play,
  RefreshCw,
  Trash2,
  UserPlus,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  dashboardApi,
  osintApi,
  type ConnectorStatus,
  type ComparisonCategory,
  type DashboardSummary,
  type IdentityProfile,
  type IdentityProfileInput,
  type OsintResult,
  type PlatformCheckList,
  type PlatformCheckStatus,
  type ResultPage,
  type Scan,
  type ScanComparison,
} from '../services/api'
import { useTranslation, type MessageKey } from '../i18n/messages'

export type WorkspaceSection = 'dashboard' | 'identities' | 'scans' | 'results'

const scanLabelKeys: Record<Scan['status'], MessageKey> = {
  queued: 'workspaceScanQueued',
  running: 'workspaceScanRunning',
  completed: 'workspaceScanCompleted',
  failed: 'workspaceScanFailed',
  cancelled: 'workspaceScanCancelled',
}

const comparisonLabelKeys: Record<ComparisonCategory, MessageKey> = {
  new: 'workspaceCompareNew',
  known: 'workspaceCompareKnown',
  modified: 'workspaceCompareModified',
  inaccessible: 'workspaceCompareInaccessible',
  not_reverified: 'workspaceCompareNotReverified',
  excluded_false_positive: 'workspaceCompareFalsePositive',
}

const platformStatusLabelKeys: Record<PlatformCheckStatus, MessageKey> = {
  PUBLIC_MATCH: 'workspacePlatformPublicMatch',
  POSSIBLE_MATCH: 'workspacePlatformPossibleMatch',
  NO_PUBLIC_RESULT: 'workspacePlatformNoPublicResult',
  USER_VERIFIED: 'workspacePlatformUserVerified',
  NOT_VERIFIABLE: 'workspacePlatformNotVerifiable',
  RATE_LIMITED: 'workspacePlatformRateLimited',
  ACCESS_RESTRICTED: 'workspacePlatformAccessRestricted',
  ERROR: 'workspacePlatformError',
}

type ProfileDraft = Record<
  | 'first_name'
  | 'last_name'
  | 'name_variants'
  | 'pseudonyms'
  | 'former_pseudonyms'
  | 'emails'
  | 'phone_numbers'
  | 'city_region'
  | 'profession'
  | 'employers'
  | 'domains'
  | 'websites'
  | 'social_profiles'
  | 'confirmed_profiles'
  | 'keywords'
  | 'exact_phrases'
  | 'exclusions'
  | 'context',
  string
>

export function OsintWorkspacePage({ section }: { section: WorkspaceSection }) {
  const { locale, t } = useTranslation()
  const [profiles, setProfiles] = useState<IdentityProfile[]>([])
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [scans, setScans] = useState<Scan[]>([])
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [resultPage, setResultPage] = useState<ResultPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: 25,
    pages: 0,
  })
  const [resultQuery, setResultQuery] = useState('')
  const [resultConnector, setResultConnector] = useState('')
  const [resultDomain, setResultDomain] = useState('')
  const [resultStatus, setResultStatus] = useState<
    OsintResult['verification_status'] | ''
  >('')
  const [resultSort, setResultSort] = useState<
    'date' | 'title' | 'score' | 'domain'
  >('date')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [pseudonyms, setPseudonyms] = useState('')
  const [selectedProfile, setSelectedProfile] = useState('')
  const [selectedConnector, setSelectedConnector] = useState('')
  const [baselineScan, setBaselineScan] = useState('')
  const [currentScan, setCurrentScan] = useState('')
  const [comparison, setComparison] = useState<ScanComparison | null>(null)
  const [platformChecks, setPlatformChecks] =
    useState<PlatformCheckList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null)
  const [profileDraft, setProfileDraft] = useState<ProfileDraft | null>(null)

  const load = useCallback(async () => {
    try {
      const [nextProfiles, nextConnectors, nextScans, nextDashboard] =
        await Promise.all([
          osintApi.profiles(),
          osintApi.connectors(),
          osintApi.scans(),
          dashboardApi.summary(),
        ])
      setProfiles(nextProfiles)
      setConnectors(nextConnectors)
      setScans(nextScans)
      setDashboard(nextDashboard)
      setSelectedProfile((current) => current || nextProfiles[0]?.id || '')
      setSelectedConnector(
        (current) =>
          current ||
          nextConnectors.find((item) => item.enabled && item.ready !== false)
            ?.identifier ||
          nextConnectors[0]?.identifier ||
          '',
      )
      setError(null)
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('workspaceLoadFailed'),
      )
    }
  }, [t])

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(task)
  }, [load])

  const loadResultPage = useCallback(
    async (page = 1) => {
      try {
        setResultPage(
          await osintApi.searchResults({
            query: resultQuery,
            connector_id: resultConnector,
            domain: resultDomain,
            verification_status: resultStatus,
            sort_by: resultSort,
            sort_order:
              resultSort === 'title' || resultSort === 'domain'
                ? 'asc'
                : 'desc',
            page,
            page_size: 25,
          }),
        )
        setError(null)
      } catch (caught) {
        setError(
          caught instanceof Error ? caught.message : t('workspaceSearchFailed'),
        )
      }
    },
    [resultConnector, resultDomain, resultQuery, resultSort, resultStatus, t],
  )

  useEffect(() => {
    if (section !== 'results') return
    const task = window.setTimeout(() => {
      void osintApi
        .searchResults({
          sort_by: 'date',
          sort_order: 'desc',
          page: 1,
          page_size: 25,
        })
        .then(setResultPage)
        .catch((caught: unknown) =>
          setError(
            caught instanceof Error
              ? caught.message
              : t('workspaceSearchFailed'),
          ),
        )
    }, 0)
    return () => window.clearTimeout(task)
  }, [section, t])

  async function createProfile(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const created = await osintApi.createProfile(
        firstName,
        lastName,
        pseudonyms
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean),
      )
      setFirstName('')
      setLastName('')
      setPseudonyms('')
      setSelectedProfile(created.id)
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('workspaceCreateFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  const activeProfile = profiles.find(
    (profile) => profile.id === selectedProfile,
  )
  const globalConnectorIds = connectors
    .filter((connector) => {
      if (!connector.enabled || connector.ready === false) return false
      const canSearchName =
        connector.accepted_identifiers.includes('name') &&
        Boolean(activeProfile?.first_name && activeProfile.last_name)
      const canSearchPseudonym =
        connector.accepted_identifiers.includes('pseudonym') &&
        Boolean(activeProfile?.pseudonyms.length)
      const canSearchDomain =
        connector.accepted_identifiers.includes('domain') &&
        Boolean(activeProfile?.domains.length || activeProfile?.websites.length)
      return canSearchName || canSearchPseudonym || canSearchDomain
    })
    .map((connector) => connector.identifier)
  const globalSearchAvailable = globalConnectorIds.some((connectorId) =>
    connectors.some(
      (connector) =>
        connector.identifier === connectorId &&
        connector.capabilities.includes('web_search'),
    ),
  )

  async function startScan(connectorIds: string[] = [selectedConnector]) {
    if (!selectedProfile || !connectorIds.length || connectorIds.includes(''))
      return
    if (
      connectorIds.includes('brave') &&
      !window.confirm(t('workspaceBraveDisclosure'))
    ) {
      return
    }
    if (
      connectorIds.includes('searxng') &&
      !window.confirm(t('workspaceSearxngDisclosure'))
    ) {
      return
    }
    const externalSearchConsent = connectorIds.some((connectorId) =>
      ['brave', 'searxng'].includes(connectorId),
    )
    setBusy(true)
    try {
      await osintApi.startScan(
        selectedProfile,
        connectorIds,
        externalSearchConsent,
      )
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('workspaceStartFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  function beginProfileEdit(profile: IdentityProfile) {
    setEditingProfileId(profile.id)
    setProfileDraft({
      first_name: profile.first_name,
      last_name: profile.last_name,
      name_variants: profile.name_variants.join('\n'),
      pseudonyms: profile.pseudonyms.join('\n'),
      former_pseudonyms: (profile.former_pseudonyms ?? []).join('\n'),
      emails: profile.emails.join('\n'),
      phone_numbers: (profile.phone_numbers ?? []).join('\n'),
      city_region: profile.city_region ?? '',
      profession: profile.profession ?? '',
      employers: (profile.employers ?? []).join('\n'),
      domains: profile.domains.join('\n'),
      websites: profile.websites.join('\n'),
      social_profiles: profile.social_profiles.join('\n'),
      confirmed_profiles: (profile.confirmed_profiles ?? []).join('\n'),
      keywords: profile.keywords.join('\n'),
      exact_phrases: (profile.exact_phrases ?? []).join('\n'),
      exclusions: (profile.exclusions ?? []).join('\n'),
      context: profile.context ?? '',
    })
  }

  async function saveProfile(event: FormEvent) {
    event.preventDefault()
    if (!editingProfileId || !profileDraft) return
    const payload: IdentityProfileInput = {
      first_name: profileDraft.first_name.trim(),
      last_name: profileDraft.last_name.trim(),
      name_variants: splitProfileValues(profileDraft.name_variants),
      pseudonyms: splitProfileValues(profileDraft.pseudonyms),
      former_pseudonyms: splitProfileValues(profileDraft.former_pseudonyms),
      emails: splitProfileValues(profileDraft.emails),
      phone_numbers: splitProfileValues(profileDraft.phone_numbers),
      city_region: profileDraft.city_region.trim() || null,
      profession: profileDraft.profession.trim() || null,
      employers: splitProfileValues(profileDraft.employers),
      domains: splitProfileValues(profileDraft.domains),
      websites: splitProfileValues(profileDraft.websites),
      social_profiles: splitProfileValues(profileDraft.social_profiles),
      confirmed_profiles: splitProfileValues(profileDraft.confirmed_profiles),
      keywords: splitProfileValues(profileDraft.keywords),
      exact_phrases: splitProfileValues(profileDraft.exact_phrases),
      exclusions: splitProfileValues(profileDraft.exclusions),
      context: profileDraft.context.trim() || null,
    }
    setBusy(true)
    try {
      await osintApi.updateProfile(editingProfileId, payload)
      setEditingProfileId(null)
      setProfileDraft(null)
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('workspaceUpdateFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function removeProfile(profile: IdentityProfile) {
    const confirmed = window.confirm(
      formatMessage(t('workspaceConfirmDeleteProfile'), {
        name: `${profile.first_name} ${profile.last_name}`,
      }),
    )
    if (!confirmed) return
    try {
      await osintApi.removeProfile(profile.id)
      if (editingProfileId === profile.id) {
        setEditingProfileId(null)
        setProfileDraft(null)
      }
      await load()
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('workspaceDeleteFailed'),
      )
    }
  }

  async function compareScans() {
    if (!baselineScan || !currentScan) return
    setBusy(true)
    try {
      setComparison(await osintApi.compareScans(baselineScan, currentScan))
      setError(null)
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : t('workspaceCompareFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  async function showPlatformChecks(scanId: string) {
    setBusy(true)
    try {
      setPlatformChecks(await osintApi.platformChecks(scanId))
      setError(null)
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : t('workspacePlatformChecksFailed'),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="px-4 py-8 sm:px-8 xl:px-12">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold text-teal-700 dark:text-teal-400">
              {t('workspaceTagline')}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              {section === 'dashboard'
                ? t('workspaceDashboard')
                : section === 'identities'
                  ? t('workspaceIdentities')
                  : section === 'scans'
                    ? t('workspaceSearches')
                    : t('workspaceResults')}
            </h1>
          </div>
          <button className="secondary-button" onClick={() => void load()}>
            <RefreshCw size={17} /> {t('workspaceRefresh')}
          </button>
        </div>
        {error && <p className="error-message mt-5">{error}</p>}

        {section === 'dashboard' && (
          <div className="mt-8 space-y-6">
            <section
              className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
              aria-label={t('workspaceSummary')}
            >
              <Metric
                value={dashboard?.total_mentions ?? 0}
                label={t('workspacePublicMentions')}
              />
              <Metric
                value={dashboard?.total_domains ?? 0}
                label={t('workspaceDomains')}
              />
              <Metric
                value={dashboard?.total_profiles ?? 0}
                label={t('workspaceProfiles')}
              />
              <Metric
                value={dashboard?.new_mentions_7d ?? 0}
                label={t('workspaceNewSevenDays')}
              />
              <Metric
                value={dashboard?.needs_verification ?? 0}
                label={t('workspaceNeedsReview')}
              />
            </section>
            <section className="panel">
              <h2 className="section-title">{t('workspaceEvolution30Days')}</h2>
              <EvolutionChart
                points={dashboard?.evolution ?? []}
                locale={locale}
                t={t}
              />
            </section>
            <div className="grid gap-6 lg:grid-cols-2">
              <section className="panel">
                <h2 className="section-title">
                  {t('workspaceRecentSearches')}
                </h2>
                <div className="mt-4 space-y-3">
                  {scans.slice(0, 5).map((scan) => (
                    <div
                      key={scan.id}
                      className="flex justify-between rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700"
                    >
                      <span>{scan.connector_ids.join(', ')}</span>
                      <span>{t(scanLabelKeys[scan.status])}</span>
                    </div>
                  ))}
                  {scans.length === 0 && (
                    <Empty text={t('workspaceNoSearches')} />
                  )}
                </div>
              </section>
              <section className="panel">
                <h2 className="section-title">
                  {t('workspaceConnectorStatus')}
                </h2>
                <div className="mt-4 space-y-3">
                  {connectors.map((connector) => (
                    <div
                      key={connector.identifier}
                      className="flex justify-between rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700"
                    >
                      <span className="font-semibold">
                        {connector.identifier}
                      </span>
                      <span>{connector.health}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        )}

        {section === 'identities' && (
          <div className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <form
              className="panel space-y-4"
              onSubmit={(event) => void createProfile(event)}
            >
              <h2 className="section-title">
                <UserPlus className="inline" size={20} />{' '}
                {t('workspaceNewProfile')}
              </h2>
              <label className="field-label">
                {t('workspaceFirstName')}
                <input
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </label>
              <label className="field-label">
                {t('workspaceLastName')}
                <input
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </label>
              <label className="field-label">
                {t('workspacePseudonymsComma')}
                <input
                  value={pseudonyms}
                  onChange={(e) => setPseudonyms(e.target.value)}
                />
              </label>
              <button className="primary-button" disabled={busy}>
                {t('workspaceCreateProfile')}
              </button>
            </form>
            <section className="panel">
              <h2 className="section-title">{t('workspaceSavedProfiles')}</h2>
              <div className="mt-4 space-y-3">
                {profiles.length === 0 ? (
                  <Empty text={t('workspaceNoProfiles')} />
                ) : (
                  profiles.map((profile) => (
                    <article
                      key={profile.id}
                      className="rounded-xl border border-slate-200 p-4 dark:border-slate-700"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold">
                            {profile.first_name} {profile.last_name}
                          </p>
                          <p className="mt-1 text-sm text-slate-500">
                            {profile.pseudonyms.join(', ') ||
                              t('workspaceNoPseudonym')}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            className="icon-button"
                            aria-label={formatMessage(
                              t('workspaceConfirmEditProfile'),
                              {
                                name: `${profile.first_name} ${profile.last_name}`,
                              },
                            )}
                            onClick={() => beginProfileEdit(profile)}
                          >
                            <Pencil size={16} />
                          </button>
                          <button
                            className="icon-button danger"
                            aria-label={formatMessage(
                              t('workspaceConfirmDeleteProfileButton'),
                              {
                                name: `${profile.first_name} ${profile.last_name}`,
                              },
                            )}
                            onClick={() => void removeProfile(profile)}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </article>
                  ))
                )}
              </div>
            </section>
            {editingProfileId && profileDraft && (
              <form
                className="panel space-y-4 lg:col-span-2"
                onSubmit={(event) => void saveProfile(event)}
              >
                <div className="flex items-center justify-between gap-3">
                  <h2 className="section-title">{t('workspaceEditProfile')}</h2>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => {
                      setEditingProfileId(null)
                      setProfileDraft(null)
                    }}
                  >
                    {t('workspaceCancel')}
                  </button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <ProfileField
                    label={t('workspaceFirstName')}
                    field="first_name"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                    required
                  />
                  <ProfileField
                    label={t('workspaceLastName')}
                    field="last_name"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                    required
                  />
                  <ProfileTextarea
                    label={t('workspaceNameVariants')}
                    field="name_variants"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspacePseudonyms')}
                    field="pseudonyms"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceFormerPseudonyms')}
                    field="former_pseudonyms"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceEmails')}
                    field="emails"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspacePhoneNumbers')}
                    field="phone_numbers"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileField
                    label={t('workspaceCityRegion')}
                    field="city_region"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileField
                    label={t('workspaceProfession')}
                    field="profession"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceEmployers')}
                    field="employers"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceDomainsPersonal')}
                    field="domains"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceWebsites')}
                    field="websites"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceSocialProfiles')}
                    field="social_profiles"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceConfirmedProfiles')}
                    field="confirmed_profiles"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceKeywords')}
                    field="keywords"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceExactPhrases')}
                    field="exact_phrases"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceExclusions')}
                    field="exclusions"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                  <ProfileTextarea
                    label={t('workspaceContext')}
                    field="context"
                    draft={profileDraft}
                    setDraft={setProfileDraft}
                  />
                </div>
                <p className="text-xs text-slate-500">
                  {t('workspaceOneValuePerLine')}
                </p>
                <button className="primary-button" disabled={busy}>
                  {t('workspaceSaveChanges')}
                </button>
              </form>
            )}
          </div>
        )}

        {section === 'scans' && (
          <div className="mt-8 space-y-6">
            <section className="panel">
              <h2 className="section-title">{t('workspaceStartSearch')}</h2>
              <p className="section-copy">{t('workspacePseudonymCaveat')}</p>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                {t('workspaceGlobalSearchDescription')}
              </p>
              {!globalSearchAvailable && (
                <p
                  className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100"
                  role="status"
                >
                  {t('workspaceGlobalSearchUnavailable')}
                </p>
              )}
              {selectedConnector === 'brave' && (
                <p
                  className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100"
                  role="note"
                >
                  {t('workspaceBraveNotice')}
                </p>
              )}
              {selectedConnector === 'searxng' && (
                <p role="note">{t('workspaceSearxngNotice')}</p>
              )}
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <select
                  aria-label={t('workspaceSelectProfile')}
                  value={selectedProfile}
                  onChange={(e) => setSelectedProfile(e.target.value)}
                >
                  <option value="">{t('workspaceSelectProfile')}</option>
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.first_name} {profile.last_name}
                    </option>
                  ))}
                </select>
                <select
                  aria-label={t('workspaceSelectConnector')}
                  value={selectedConnector}
                  onChange={(e) => setSelectedConnector(e.target.value)}
                >
                  <option value="">{t('workspaceSelectConnector')}</option>
                  {connectors.map((connector) => (
                    <option
                      key={connector.identifier}
                      value={connector.identifier}
                      disabled={!connector.enabled || connector.ready === false}
                    >
                      {connector.identifier}
                      {connector.ready === false
                        ? ` · ${t('workspaceNotConfigured')}`
                        : ''}
                    </option>
                  ))}
                </select>
                <button
                  className="primary-button shrink-0"
                  disabled={!selectedProfile || !selectedConnector || busy}
                  onClick={() => void startScan()}
                >
                  <Play size={17} /> {t('workspaceStart')}
                </button>
                <button
                  className="secondary-button shrink-0"
                  disabled={!selectedProfile || !globalSearchAvailable || busy}
                  onClick={() => void startScan(globalConnectorIds)}
                >
                  <Play size={17} /> {t('workspaceStartGlobal')}
                </button>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                {t('workspaceConnector')}{' '}
                {connectors
                  .map(
                    (item) =>
                      `${item.identifier} · ${item.health}${item.ready === false ? ` · ${t('workspaceNotConfigured')}` : ''}`,
                  )
                  .join(', ') || t('workspaceUnavailable')}
              </p>
            </section>
            <section className="panel overflow-x-auto">
              <h2 className="section-title">{t('workspaceHistory')}</h2>
              <table className="mt-4">
                <thead>
                  <tr>
                    <th>{t('workspaceDate')}</th>
                    <th>{t('workspaceSources')}</th>
                    <th>{t('workspaceStatus')}</th>
                    <th>{t('workspaceProgress')}</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {scans.map((scan) => (
                    <tr key={scan.id}>
                      <td>
                        {new Date(scan.created_at).toLocaleString(
                          locale === 'fr' ? 'fr-FR' : 'en-GB',
                        )}
                      </td>
                      <td>{scan.connector_ids.join(', ')}</td>
                      <td>{t(scanLabelKeys[scan.status])}</td>
                      <td>{Math.round(scan.progress * 100)} %</td>
                      <td>
                        {['queued', 'running'].includes(scan.status) && (
                          <button
                            className="icon-button danger"
                            aria-label={t('workspaceCancelScan')}
                            onClick={() =>
                              void osintApi.cancelScan(scan.id).then(load)
                            }
                          >
                            <XCircle size={17} />
                          </button>
                        )}
                        {scan.status === 'completed' && (
                          <button
                            className="secondary-button whitespace-nowrap"
                            disabled={busy}
                            onClick={() => void showPlatformChecks(scan.id)}
                          >
                            {t('workspacePlatformChecks')}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {scans.length === 0 && <Empty text={t('workspaceNoSearches')} />}
            </section>
            {platformChecks && (
              <section className="panel overflow-x-auto" aria-live="polite">
                <h2 className="section-title">
                  {t('workspacePlatformChecksTitle')}
                </h2>
                <p className="section-copy">
                  {platformChecks.methodology_note}
                </p>
                <table className="mt-4">
                  <thead>
                    <tr>
                      <th>{t('workspacePlatform')}</th>
                      <th>{t('workspaceMethod')}</th>
                      <th>{t('workspaceStatus')}</th>
                      <th>{t('workspaceResultsCount')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {platformChecks.items.map((check) => (
                      <tr key={check.platform_identifier}>
                        <td className="font-semibold">
                          {check.platform_identifier}
                        </td>
                        <td>{check.verification_method}</td>
                        <td>{t(platformStatusLabelKeys[check.status])}</td>
                        <td>{check.result_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {platformChecks.items.length === 0 && (
                  <Empty text={t('workspaceNoPlatformChecks')} />
                )}
              </section>
            )}
            <section className="panel">
              <h2 className="section-title">{t('workspaceCompareSearches')}</h2>
              <p className="section-copy">{t('workspaceCompareDescription')}</p>
              <div className="mt-5 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                <select
                  aria-label={t('workspaceBaselineScan')}
                  value={baselineScan}
                  onChange={(event) => setBaselineScan(event.target.value)}
                >
                  <option value="">{t('workspaceBaselineScan')}</option>
                  {scans
                    .filter((scan) => scan.status === 'completed')
                    .map((scan) => (
                      <option key={scan.id} value={scan.id}>
                        {new Date(scan.created_at).toLocaleString(
                          locale === 'fr' ? 'fr-FR' : 'en-GB',
                        )}
                      </option>
                    ))}
                </select>
                <select
                  aria-label={t('workspaceRecentScan')}
                  value={currentScan}
                  onChange={(event) => setCurrentScan(event.target.value)}
                >
                  <option value="">{t('workspaceRecentScan')}</option>
                  {scans
                    .filter((scan) => scan.status === 'completed')
                    .map((scan) => (
                      <option key={scan.id} value={scan.id}>
                        {new Date(scan.created_at).toLocaleString(
                          locale === 'fr' ? 'fr-FR' : 'en-GB',
                        )}
                      </option>
                    ))}
                </select>
                <button
                  className="primary-button"
                  disabled={
                    busy ||
                    !baselineScan ||
                    !currentScan ||
                    baselineScan === currentScan
                  }
                  onClick={() => void compareScans()}
                >
                  {t('workspaceCompare')}
                </button>
              </div>
              {comparison && (
                <div className="mt-6">
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {Object.entries(comparisonLabelKeys).map(
                      ([category, key]) => (
                        <div
                          className="rounded-xl border border-slate-200 p-3 dark:border-slate-700"
                          key={category}
                        >
                          <p className="text-2xl font-semibold">
                            {comparison.counts[category as ComparisonCategory]}
                          </p>
                          <p className="text-sm text-slate-500">{t(key)}</p>
                        </div>
                      ),
                    )}
                  </div>
                  <p className="mt-4 text-xs text-slate-500">
                    {comparison.methodology_note}
                  </p>
                  <div className="mt-4 overflow-x-auto">
                    <table>
                      <thead>
                        <tr>
                          <th>{t('workspaceEvolution')}</th>
                          <th>{t('workspaceSource')}</th>
                          <th>{t('workspaceMention')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparison.items.map((item) => (
                          <tr key={`${item.category}-${item.canonical_url}`}>
                            <td>{t(comparisonLabelKeys[item.category])}</td>
                            <td>{item.connector_id}</td>
                            <td>
                              <a
                                className="font-semibold text-teal-700"
                                href={item.canonical_url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {item.title}
                              </a>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {section === 'results' && (
          <section className="panel mt-8">
            <h2 className="section-title">{t('workspaceFoundMentions')}</h2>
            <form
              className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5"
              onSubmit={(event) => {
                event.preventDefault()
                void loadResultPage(1)
              }}
            >
              <input
                aria-label={t('workspaceSearchInResults')}
                placeholder={t('workspaceTitleSnippetUrl')}
                value={resultQuery}
                onChange={(event) => setResultQuery(event.target.value)}
              />
              <select
                aria-label={t('workspaceFilterConnector')}
                value={resultConnector}
                onChange={(event) => setResultConnector(event.target.value)}
              >
                <option value="">{t('workspaceAllSources')}</option>
                {connectors.map((connector) => (
                  <option
                    key={connector.identifier}
                    value={connector.identifier}
                  >
                    {connector.identifier}
                  </option>
                ))}
              </select>
              <input
                aria-label={t('workspaceFilterDomain')}
                placeholder={t('workspaceExactDomain')}
                value={resultDomain}
                onChange={(event) => setResultDomain(event.target.value)}
              />
              <select
                aria-label={t('workspaceFilterStatus')}
                value={resultStatus}
                onChange={(event) =>
                  setResultStatus(
                    event.target.value as
                      | OsintResult['verification_status']
                      | '',
                  )
                }
              >
                <option value="">{t('workspaceAllStatuses')}</option>
                <option value="uncertain">{t('workspaceUncertain')}</option>
                <option value="probable">{t('workspaceProbable')}</option>
                <option value="confirmed">{t('workspaceConfirmed')}</option>
                <option value="false_positive">
                  {t('workspaceFalsePositive')}
                </option>
                <option value="ignored">{t('workspaceIgnored')}</option>
              </select>
              <div className="flex gap-2">
                <select
                  aria-label={t('workspaceSortResults')}
                  value={resultSort}
                  onChange={(event) =>
                    setResultSort(
                      event.target.value as
                        | 'date'
                        | 'title'
                        | 'score'
                        | 'domain',
                    )
                  }
                >
                  <option value="date">Date</option>
                  <option value="score">{t('workspaceScore')}</option>
                  <option value="title">{t('workspaceTitle')}</option>
                  <option value="domain">{t('workspaceDomain')}</option>
                </select>
                <button className="primary-button" type="submit">
                  {t('workspaceFilter')}
                </button>
              </div>
            </form>
            <p className="mt-4 text-sm text-slate-500">
              {formatMessage(t('workspaceCount'), { count: resultPage.total })}
            </p>
            <div className="overflow-x-auto">
              <table className="mt-4">
                <thead>
                  <tr>
                    <th>{t('workspaceSource')}</th>
                    <th>{t('workspaceMention')}</th>
                    <th>{t('workspaceScore')}</th>
                    <th>{t('workspaceValidation')}</th>
                  </tr>
                </thead>
                <tbody>
                  {resultPage.items.map((result) => (
                    <tr key={result.id}>
                      <td>{result.connector_id}</td>
                      <td>
                        <a
                          className="font-semibold text-teal-700"
                          href={result.canonical_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {result.title}{' '}
                          <ExternalLink className="inline" size={14} />
                        </a>
                        <p className="mt-1 max-w-xl text-xs text-slate-500">
                          {result.snippet}
                        </p>
                      </td>
                      <td>{Math.round(result.relevance_score * 100)} %</td>
                      <td>
                        <select
                          aria-label={formatMessage(
                            t('workspaceResultValidation'),
                            { title: result.title },
                          )}
                          value={result.verification_status}
                          onChange={(e) =>
                            void osintApi
                              .verifyResult(
                                result.id,
                                e.target
                                  .value as OsintResult['verification_status'],
                              )
                              .then(() => loadResultPage(resultPage.page))
                          }
                        >
                          <option value="uncertain">
                            {t('workspaceUncertain')}
                          </option>
                          <option value="probable">
                            {t('workspaceProbable')}
                          </option>
                          <option value="confirmed">
                            {t('workspaceConfirmed')}
                          </option>
                          <option value="false_positive">
                            {t('workspaceFalsePositive')}
                          </option>
                          <option value="ignored">
                            {t('workspaceIgnored')}
                          </option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {resultPage.items.length === 0 && (
              <Empty text={t('workspaceNoResults')} />
            )}
            {resultPage.pages > 1 && (
              <div className="mt-5 flex items-center justify-between">
                <button
                  className="secondary-button"
                  disabled={resultPage.page <= 1}
                  onClick={() => void loadResultPage(resultPage.page - 1)}
                >
                  {t('workspacePrevious')}
                </button>
                <span className="text-sm text-slate-500">
                  {formatMessage(t('workspacePageOf'), {
                    page: resultPage.page,
                    pages: resultPage.pages,
                  })}
                </span>
                <button
                  className="secondary-button"
                  disabled={resultPage.page >= resultPage.pages}
                  onClick={() => void loadResultPage(resultPage.page + 1)}
                >
                  {t('workspaceNext')}
                </button>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return <p className="py-8 text-center text-sm text-slate-500">{text}</p>
}

function Metric({ value, label }: { value: number; label: string }) {
  return (
    <div className="panel">
      <p className="text-3xl font-semibold">{value}</p>
      <p className="mt-1 text-sm text-slate-500">{label}</p>
    </div>
  )
}

function splitProfileValues(value: string): string[] {
  return [
    ...new Set(
      value
        .split(/[\n,]/)
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ]
}

function updateDraft(
  setDraft: (draft: ProfileDraft) => void,
  draft: ProfileDraft,
  field: keyof ProfileDraft,
  value: string,
) {
  setDraft({ ...draft, [field]: value })
}

function ProfileField({
  label,
  field,
  draft,
  setDraft,
  required = false,
}: {
  label: string
  field: keyof ProfileDraft
  draft: ProfileDraft
  setDraft: (draft: ProfileDraft) => void
  required?: boolean
}) {
  return (
    <label className="field-label">
      {label}
      <input
        required={required}
        value={draft[field]}
        onChange={(event) =>
          updateDraft(setDraft, draft, field, event.target.value)
        }
      />
    </label>
  )
}

function ProfileTextarea({
  label,
  field,
  draft,
  setDraft,
}: {
  label: string
  field: keyof ProfileDraft
  draft: ProfileDraft
  setDraft: (draft: ProfileDraft) => void
}) {
  return (
    <label className="field-label">
      {label}
      <textarea
        rows={3}
        value={draft[field]}
        onChange={(event) =>
          updateDraft(setDraft, draft, field, event.target.value)
        }
      />
    </label>
  )
}

function EvolutionChart({
  points,
  locale,
  t,
}: {
  points: DashboardSummary['evolution']
  locale: 'fr' | 'en'
  t: (key: MessageKey) => string
}) {
  const maximum = Math.max(1, ...points.map((point) => point.mentions))
  if (points.length === 0) return <Empty text={t('workspaceNoEvolution')} />
  return (
    <div
      className="mt-5 flex h-48 items-end gap-1"
      role="img"
      aria-label={formatMessage(t('workspaceChartDescription'), {
        count: points.reduce((sum, point) => sum + point.mentions, 0),
      })}
    >
      {points.map((point) => (
        <div
          key={point.date}
          className="group relative flex h-full min-w-0 flex-1 items-end"
        >
          <div
            className="w-full rounded-t bg-teal-600/80 transition-colors group-hover:bg-teal-500"
            style={{
              height: `${Math.max(point.mentions > 0 ? 6 : 1, (point.mentions / maximum) * 100)}%`,
            }}
            title={`${new Date(point.date).toLocaleDateString(locale === 'fr' ? 'fr-FR' : 'en-GB')} : ${point.mentions}`}
          />
        </div>
      ))}
    </div>
  )
}

function formatMessage(
  message: string,
  values: Record<string, string | number>,
): string {
  return message.replace(/\{(\w+)\}/g, (placeholder, key: string) =>
    Object.hasOwn(values, key) ? String(values[key]) : placeholder,
  )
}
