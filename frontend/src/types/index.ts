export interface HukumItem {
  description: string
  legal_basis: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  legal_text_summary?: string
  doc_evidence?: string
}

export interface PerluDikonfirmasiItem {
  question: string
  why: string
  options?: string[]
  parameter_key: string
  type: 'select' | 'number' | 'text' | 'file'
}

export interface AnalisisBlock {
  text: string
  disclaimer: string
}

export interface ActionItem {
  description: string
  severity: string
  legal_basis: string
}

export interface ChatResponseBody {
  hukum: HukumItem[]
  analisis: AnalisisBlock | null
  perlu_dikonfirmasi: PerluDikonfirmasiItem[]
  actions: ActionItem[]
  quick_actions?: { label: string; prefill: string }[]
}

export interface ChatResponse {
  session_id: string
  response: ChatResponseBody
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  response?: ChatResponseBody
  timestamp: number
}

export interface SeveranceRequest {
  masa_kerja_bulan: number
  upah_pokok: number
  tunjangan_tetap: number
  alasan_phk: string
  tanggal_phk?: string
}

export interface SeveranceComponent {
  amount: number
  formula: string
  multiplier?: number
}

export interface SeveranceResponse {
  pesangon: SeveranceComponent
  penghargaan: SeveranceComponent
  penggantian_hak: SeveranceComponent
  total: number
  legal_basis: { pasal: string; description: string }[]
  comparison?: { old_law_total: number; difference: number; note: string }
}

export interface ProvisionChild {
  node_id: string
  type: string
  number: string
  text_preview?: string
}

export interface ProvisionResponse {
  node_id: string
  type: string
  number: string
  text?: string
  parent?: string
  children: ProvisionChild[]
  regulation?: Record<string, string>
  norms_derived: { id: string; description: string; severity: string }[]
}
