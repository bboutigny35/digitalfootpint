import type {
  SensitiveAlert,
  SensitiveCheck,
  SensitiveDescriptor,
  SensitiveFinding,
} from '../types/sensitive'

export interface AuthUser {
  id: string
  email: string
  is_admin: boolean
}

export interface IdentityProfile {
  id: string
  first_name: string
  last_name: string
  name_variants: string[]
  pseudonyms: string[]
  former_pseudonyms?: string[]
  emails: string[]
  phone_numbers?: string[]
  city_region?: string | null
  profession?: string | null
  employers?: string[]
  domains: string[]
  websites: string[]
  social_profiles: string[]
  confirmed_profiles?: string[]
  keywords: string[]
  exact_phrases?: string[]
  exclusions?: string[]
  context: string | null
  created_at: string
  updated_at: string
}

export type IdentityProfileInput = Omit<
  IdentityProfile,
  'id' | 'created_at' | 'updated_at'
>

export interface ConnectorStatus {
  identifier: string
  version: string
  capabilities: string[]
  accepted_identifiers: string[]
  enabled: boolean
  ready?: boolean
  health: string
  rate_limit_per_minute: number | null
  quota_status: string
  last_scan_at: string | null
  result_count: number
  error_count: number
}

export interface Scan {
  id: string
  profile_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  connector_ids: string[]
  progress: number
  error_code: string | null
  created_at: string
}

export interface OsintResult {
  id: string
  profile_id: string
  scan_id: string
  connector_id: string
  canonical_url: string
  domain: string
  title: string
  snippet: string
  verification_status:
    | 'confirmed'
    | 'probable'
    | 'uncertain'
    | 'false_positive'
    | 'ignored'
  relevance_score: number
  discovered_at: string
}

export interface ResultPage {
  items: OsintResult[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface IdentityCorrelation {
  id: string
  result_id: string
  relevance_score: number
  attribution_score: number
  explanation: {
    warning?: string
    page_classification?: string
    risk_flags?: string[]
    [key: string]: unknown
  }
  contradictions: string[]
  evidence_count: number
  evidence: Array<{
    id: string
    evidence_type: string
    excerpt: string
    source_url: string
    source_hash: string
    provenance: Record<string, unknown>
    observed_at: string
    matches: Array<{
      criterion_type: string
      match_kind: string
      weight: number
      explanation: string
    }>
  }>
  validation: {
    id: string
    decision: 'confirmed' | 'rejected' | 'uncertain'
    exclusion_kind: 'homonym' | null
    attributed_profile_id: string | null
    reused_from_validation_id: string | null
    created_at: string
    updated_at: string
  } | null
}

export interface ReportExport {
  id: string
  profile_id: string | null
  export_format: string
  report_kind: string
  result_count: number
  created_at: string
}

export interface ScanSchedule {
  id: string
  profile_id: string
  connector_ids: string[]
  cadence: 'daily' | 'weekly' | 'monthly'
  enabled: boolean
  next_run_at: string
  last_run_at: string | null
  created_at: string
}

export type ComparisonCategory =
  | 'new'
  | 'known'
  | 'modified'
  | 'inaccessible'
  | 'not_reverified'
  | 'excluded_false_positive'

export interface ScanComparison {
  baseline_scan_id: string
  current_scan_id: string
  profile_id: string
  counts: Record<ComparisonCategory, number>
  items: Array<{
    category: ComparisonCategory
    canonical_url: string
    domain: string
    connector_id: string
    title: string
    baseline_result_id: string | null
    current_result_id: string | null
    changed_fields: string[]
  }>
  methodology_note: string
}

export type PlatformCheckStatus =
  | 'PUBLIC_MATCH'
  | 'POSSIBLE_MATCH'
  | 'NO_PUBLIC_RESULT'
  | 'USER_VERIFIED'
  | 'NOT_VERIFIABLE'
  | 'RATE_LIMITED'
  | 'ACCESS_RESTRICTED'
  | 'ERROR'

export interface PlatformCheckList {
  scan_id: string
  items: Array<{
    platform_identifier: string
    connector_id: string | null
    verification_method: string
    status: PlatformCheckStatus
    result_count: number
    error_code: string | null
    checked_at: string
  }>
  methodology_note: string
}

export type RemovalRequestStatus =
  | 'draft'
  | 'sent'
  | 'acknowledged'
  | 'completed'
  | 'rejected'
  | 'cancelled'

export interface RemovalRequest {
  id: string
  result_id: string | null
  organization: string
  status: RemovalRequestStatus
  requested_at: string | null
  response_at: string | null
  notes: string | null
  response_notes: string | null
  created_at: string
  updated_at: string
}

export interface RemovalLetter {
  request_id: string
  subject: string
  body: string
  warning: string
}

export interface AppNotification {
  id: string
  scan_id: string | null
  kind: string
  title: string
  message: string
  read_at: string | null
  created_at: string
}

export interface NotificationPreferences {
  notify_new_mentions: boolean
}

export interface DashboardSummary {
  total_mentions: number
  total_domains: number
  total_profiles: number
  new_mentions_7d: number
  needs_verification: number
  evolution: Array<{ date: string; mentions: number }>
}

export interface AdminOverview {
  application_version: string
  environment: string
  database_backend: string
  cookie_secure: boolean
  github_token_configured: boolean
  backup_command_available: boolean
}

export interface AuditEventPage {
  items: Array<{
    id: string
    actor_id: string | null
    action: string
    resource_type: string
    resource_id: string | null
    details: Record<string, unknown>
    created_at: string
  }>
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ConnectorSecretStatus {
  connector_id: string
  configured: boolean
  key_version: string | null
  updated_at: string | null
}

export interface PlatformCatalogEntry {
  identifier: string
  display_name: string
  category: string
  verification_method: string
  default_status: string
  connector_id: string | null
  priority: number
  limitations: string | null
  last_checked_at: string | null
  last_error_code: string | null
}

export interface WebSource {
  id: string
  domain: string
  base_url: string
  category: string
  access_method: string
  state: string
  priority: number
  cache_ttl_seconds: number
  rate_limit_per_minute: number
  restrictions: string[]
  discovered_url_count: number
  crawled_page_count: number
  last_checked_at: string | null
  last_error_code: string | null
  created_at: string
  updated_at: string
}

interface AuthSession {
  user: AuthUser
  csrf_token: string
}

let csrfToken: string | null = null

export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (csrfToken && init.method && init.method !== 'GET') {
    headers.set('X-CSRF-Token', csrfToken)
  }
  const requestInit: RequestInit = {
    ...init,
    credentials: 'include',
  }
  if (
    init.headers ||
    init.body ||
    (csrfToken && init.method && init.method !== 'GET')
  ) {
    requestInit.headers = headers
  }
  const response = await fetch(`/api/v1${path}`, requestInit)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string
    } | null
    throw new Error(body?.detail ?? `Erreur HTTP ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

async function download(
  path: string,
  init: RequestInit = {},
): Promise<{ blob: Blob; filename: string }> {
  const headers = new Headers(init.headers)
  if (csrfToken && init.method && init.method !== 'GET') {
    headers.set('X-CSRF-Token', csrfToken)
  }
  const requestInit: RequestInit = {
    ...init,
    credentials: 'include',
  }
  if (init.headers || (csrfToken && init.method && init.method !== 'GET')) {
    requestInit.headers = headers
  }
  const response = await fetch(`/api/v1${path}`, requestInit)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string
    } | null
    throw new Error(body?.detail ?? `Erreur HTTP ${response.status}`)
  }
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const filename =
    disposition.match(/filename="([^"]+)"/)?.[1] ?? 'digitalfootprint-report'
  return { blob: await response.blob(), filename }
}

export const authApi = {
  restore: async () => {
    const user = await request<AuthUser>('/auth/me')
    const token = await request<{ csrf_token: string }>('/auth/csrf')
    setCsrfToken(token.csrf_token)
    return user
  },
  login: async (email: string, password: string) => {
    const session = await request<AuthSession>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setCsrfToken(session.csrf_token)
    return session.user
  },
  bootstrap: async (email: string, password: string) => {
    const session = await request<AuthSession>('/auth/bootstrap', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setCsrfToken(session.csrf_token)
    return session.user
  },
  logout: async () => {
    await request<void>('/auth/logout', { method: 'POST' })
    setCsrfToken(null)
  },
}

export const sensitiveApi = {
  descriptors: () =>
    request<SensitiveDescriptor[]>('/sensitive-monitor/descriptors'),
  checks: () => request<SensitiveCheck[]>('/sensitive-monitor/checks'),
  findings: () => request<SensitiveFinding[]>('/sensitive-monitor/findings'),
  alerts: () => request<SensitiveAlert[]>('/sensitive-monitor/alerts'),
  acknowledgeAlert: (id: string) =>
    request<SensitiveAlert>(
      `/sensitive-monitor/alerts/${encodeURIComponent(id)}/acknowledge`,
      { method: 'POST' },
    ),
  validate: (category: 'nir' | 'id_document', value: string) =>
    request<{ valid: boolean; masked_value: string | null }>(
      '/sensitive-monitor/validate',
      {
        method: 'POST',
        body: JSON.stringify({ category, value }),
      },
    ),
  createDescriptor: (
    category: 'iban' | 'phone' | 'postal_address',
    value: string,
  ) =>
    request<SensitiveDescriptor>('/sensitive-monitor/descriptors', {
      method: 'POST',
      body: JSON.stringify({ category, value, retention_days: 90 }),
    }),
  createCard: (paymentNetwork: string, lastFour: string) =>
    request<SensitiveDescriptor>('/sensitive-monitor/cards', {
      method: 'POST',
      body: JSON.stringify({
        payment_network: paymentNetwork,
        last_four: lastFour,
      }),
    }),
  remove: (id: string) =>
    request<void>(`/sensitive-monitor/descriptors/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
  localCheck: (descriptorId: string) =>
    request<SensitiveCheck>('/sensitive-monitor/checks/local', {
      method: 'POST',
      body: JSON.stringify({ descriptor_id: descriptorId }),
    }),
}

export const osintApi = {
  profiles: () => request<IdentityProfile[]>('/profiles'),
  createProfile: (firstName: string, lastName: string, pseudonyms: string[]) =>
    request<IdentityProfile>('/profiles', {
      method: 'POST',
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        pseudonyms,
      }),
    }),
  updateProfile: (profileId: string, payload: IdentityProfileInput) =>
    request<IdentityProfile>(`/profiles/${encodeURIComponent(profileId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  removeProfile: (profileId: string) =>
    request<void>(`/profiles/${encodeURIComponent(profileId)}`, {
      method: 'DELETE',
    }),
  connectors: () => request<ConnectorStatus[]>('/connectors'),
  scans: () => request<Scan[]>('/scans'),
  startScan: (
    profileId: string,
    connectorIds: string[],
    externalSearchConsent = false,
  ) =>
    request<Scan>('/scans', {
      method: 'POST',
      body: JSON.stringify({
        profile_id: profileId,
        connector_ids: connectorIds,
        external_search_consent: externalSearchConsent,
      }),
    }),
  cancelScan: (scanId: string) =>
    request<Scan>(`/scans/${encodeURIComponent(scanId)}/cancel`, {
      method: 'POST',
    }),
  compareScans: (baselineScanId: string, currentScanId: string) =>
    request<ScanComparison>(
      `/scans/compare/results?baseline_scan_id=${encodeURIComponent(baselineScanId)}&current_scan_id=${encodeURIComponent(currentScanId)}`,
    ),
  platformChecks: (scanId: string) =>
    request<PlatformCheckList>(
      `/scans/${encodeURIComponent(scanId)}/platform-checks`,
    ),
  results: () => request<OsintResult[]>('/results?limit=200'),
  searchResults: (filters: {
    query?: string
    connector_id?: string
    domain?: string
    verification_status?: OsintResult['verification_status'] | ''
    sort_by?: 'date' | 'title' | 'score' | 'domain'
    sort_order?: 'asc' | 'desc'
    page?: number
    page_size?: number
  }) => {
    const parameters = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '')
        parameters.set(key, String(value))
    })
    return request<ResultPage>(`/results/search?${parameters.toString()}`)
  },
  verifyResult: (
    resultId: string,
    verificationStatus: OsintResult['verification_status'],
  ) =>
    request<OsintResult>(
      `/results/${encodeURIComponent(resultId)}/verification`,
      {
        method: 'PATCH',
        body: JSON.stringify({ verification_status: verificationStatus }),
      },
    ),
  resultCorrelation: (resultId: string) =>
    request<IdentityCorrelation>(
      `/results/${encodeURIComponent(resultId)}/correlation`,
    ),
  validateCorrelation: (
    resultId: string,
    payload: {
      decision: 'confirmed' | 'rejected' | 'uncertain'
      exclusion_kind?: 'homonym' | null
      attributed_profile_id?: string | null
      add_confirmed_profile?: boolean
    },
  ) =>
    request<IdentityCorrelation>(
      `/results/${encodeURIComponent(resultId)}/correlation/validation`,
      { method: 'PUT', body: JSON.stringify(payload) },
    ),
}

export const dashboardApi = {
  summary: () => request<DashboardSummary>('/dashboard'),
}

export const adminApi = {
  overview: () => request<AdminOverview>('/admin/overview'),
  auditEvents: (page = 1) =>
    request<AuditEventPage>(`/admin/audit-events?page=${page}&page_size=50`),
  connectorSecrets: () =>
    request<ConnectorSecretStatus[]>('/admin/connector-secrets'),
  platformCatalog: () =>
    request<PlatformCatalogEntry[]>('/admin/platform-catalog'),
  webSources: () => request<WebSource[]>('/admin/web-sources'),
  createWebSource: (baseUrl: string, category: string) =>
    request<WebSource>('/admin/web-sources', {
      method: 'POST',
      body: JSON.stringify({
        base_url: baseUrl,
        category,
        access_method: 'manual',
      }),
    }),
  setConnectorSecret: (connectorId: string, value: string) =>
    request<ConnectorSecretStatus>(
      `/admin/connector-secrets/${encodeURIComponent(connectorId)}`,
      { method: 'PUT', body: JSON.stringify({ value }) },
    ),
  deleteConnectorSecret: (connectorId: string) =>
    request<void>(
      `/admin/connector-secrets/${encodeURIComponent(connectorId)}`,
      { method: 'DELETE' },
    ),
  rotateConnectorSecrets: () =>
    request<{ rotated: number; active_key_version: string }>(
      '/admin/connector-secrets/rotate',
      { method: 'POST' },
    ),
  configureConnector: (connectorId: string, enabled: boolean) =>
    request<{ connector_id: string; enabled: boolean; updated_at: string }>(
      `/admin/connectors/${encodeURIComponent(connectorId)}`,
      { method: 'PATCH', body: JSON.stringify({ enabled }) },
    ),
  downloadBackup: () => download('/admin/backups/download', { method: 'POST' }),
}

export const reportApi = {
  history: () => request<ReportExport[]>('/reports'),
  download: (
    format: 'csv' | 'json' | 'xlsx' | 'html' | 'pdf',
    kind: 'summary' | 'detailed',
  ) => download(`/reports/export?format=${format}&kind=${kind}`),
}

export const monitoringApi = {
  schedules: () => request<ScanSchedule[]>('/schedules'),
  create: (profileId: string, cadence: ScanSchedule['cadence']) =>
    request<ScanSchedule>('/schedules', {
      method: 'POST',
      body: JSON.stringify({
        profile_id: profileId,
        connector_ids: ['github'],
        cadence,
        external_search_consent: false,
      }),
    }),
  setEnabled: (id: string, enabled: boolean) =>
    request<ScanSchedule>(`/schedules/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    }),
  remove: (id: string) =>
    request<void>(`/schedules/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}

export const removalApi = {
  list: () => request<RemovalRequest[]>('/removal-requests'),
  create: (organization: string, resultId: string | null, notes: string) =>
    request<RemovalRequest>('/removal-requests', {
      method: 'POST',
      body: JSON.stringify({
        organization,
        result_id: resultId || null,
        notes: notes || null,
      }),
    }),
  updateStatus: (id: string, status: RemovalRequestStatus) =>
    request<RemovalRequest>(`/removal-requests/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({
        status,
        requested_at: status === 'sent' ? new Date().toISOString() : undefined,
      }),
    }),
  letter: (id: string) =>
    request<RemovalLetter>(
      `/removal-requests/${encodeURIComponent(id)}/letter`,
    ),
  remove: (id: string) =>
    request<void>(`/removal-requests/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
}

export const notificationApi = {
  list: () => request<AppNotification[]>('/notifications'),
  preferences: () =>
    request<NotificationPreferences>('/notifications/preferences'),
  updatePreferences: (notifyNewMentions: boolean) =>
    request<NotificationPreferences>('/notifications/preferences', {
      method: 'PATCH',
      body: JSON.stringify({ notify_new_mentions: notifyNewMentions }),
    }),
  markRead: (id: string) =>
    request<AppNotification>(`/notifications/${encodeURIComponent(id)}/read`, {
      method: 'POST',
    }),
}
