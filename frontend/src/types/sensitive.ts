export type SensitiveCategory =
  | 'nir'
  | 'payment_card'
  | 'iban'
  | 'phone'
  | 'postal_address'
  | 'id_document'

export interface SensitiveDescriptor {
  id: string
  category: SensitiveCategory
  masked_label: string
  metadata_json: Record<string, unknown>
  retention_expires_at: string | null
  created_at: string
}

export interface SensitiveCheck {
  id: string
  descriptor_id: string | null
  category: SensitiveCategory
  provider_id: string
  status: 'pending' | 'completed' | 'failed'
  external_transmission: boolean
  error_code: string | null
  started_at: string
  completed_at: string | null
}

export type SensitiveRisk = 'low' | 'medium' | 'high' | 'critical'

export interface SensitiveFinding {
  id: string
  check_id: string
  category: SensitiveCategory
  source_label: string
  risk_level: SensitiveRisk
  verification_status: 'confirmed' | 'needs_review' | 'false_positive'
  recommendation: string
  detected_at: string
}

export interface SensitiveAlert {
  id: string
  finding_id: string
  category: SensitiveCategory
  source_label: string
  risk_level: SensitiveRisk
  recommendation: string
  created_at: string
  acknowledged_at: string | null
}
