// User types
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: 'admin' | 'auditor' | 'reviewer' | 'viewer';
  is_active: boolean;
  created_at: string;
}

export interface UserBrief {
  id: string;
  full_name: string;
  email: string;
}

// Auth types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  email: string;
  role: string;
  full_name: string;
}

// Case types
export type CaseStatus = 'OPEN' | 'IN_PROGRESS' | 'PENDING_REVIEW' | 'CLOSED' | 'ARCHIVED';
export type CaseType = 'USB' | 'EMAIL' | 'WEB' | 'POLICY';
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export interface Case {
  id: string;
  case_id: string;
  case_number: string;
  scope_code: string;
  case_type: CaseType;
  status: CaseStatus;
  severity: Severity;
  title: string;
  summary?: string;
  description?: string;
  subject_user?: string;
  subject_computer?: string;
  subject_devices?: string[];
  related_users?: string[];
  owner_id: string;
  owner?: UserBrief;
  assigned_to?: string | UserBrief;
  incident_date?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  evidence_count: number;
  findings_count: number;
  created_at: string;
  updated_at: string;
}

export interface CaseCreate {
  scope_code?: string;
  case_type?: CaseType;
  title: string;
  summary?: string;
  description?: string;
  severity?: Severity;
  status?: CaseStatus;
  subject_user?: string;
  subject_computer?: string;
  subject_devices?: string[];
  related_users?: string[];
  incident_date?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface CaseUpdate {
  title?: string;
  summary?: string;
  description?: string;
  status?: CaseStatus;
  severity?: Severity;
  subject_user?: string;
  subject_computer?: string;
  subject_devices?: string[];
  related_users?: string[];
  assigned_to?: string;
  incident_date?: string;
  tags?: string[];
}

// Evidence types
export type EvidenceType = 'DOCUMENT' | 'IMAGE' | 'VIDEO' | 'AUDIO' | 'LOG' | 'EMAIL' | 'OTHER';

export interface Evidence {
  id: string;
  case_id: string;
  file_name: string;
  file_path: string;
  file_size: number;
  file_type: string;
  mime_type: string;
  evidence_type: EvidenceType;
  file_hash?: string;
  description?: string;
  extracted_text?: string;
  uploaded_by: string;
  uploaded_at: string;
}

// Finding types
export type FindingType = 'VIOLATION' | 'OBSERVATION' | 'RECOMMENDATION' | 'NOTE';

export interface Finding {
  id: string;
  case_id: string;
  title: string;
  description: string;
  severity: Severity;
  finding_type: FindingType;
  evidence_ids?: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface FindingCreate {
  title: string;
  description: string;
  severity: Severity;
  evidence_ids?: string[];
}

// Timeline types
export interface TimelineEvent {
  id: string;
  case_id: string;
  title: string;
  event_time: string;
  event_type: string;
  description: string;
  source?: string;
  evidence_id?: string;
  created_by: string;
  created_at: string;
}

// Entity types
export interface Entity {
  id: string;
  case_id: string;
  entity_type: string;
  value: string;
  source?: string;
  occurrence_count: number;
  created_at: string;
}

// Scope types
export interface Scope {
  code: string;
  name: string;
  description?: string;
}

// AI types
export interface CaseSummary {
  case_id: string;
  summary: string;
  key_points: string[];
  risk_assessment: string;
  recommended_actions: string[];
  model_used: string;
  confidence_score: number;
  generated_at: string;
}

export interface SimilarCase {
  case_id: string;
  title: string;
  status: CaseStatus;
  severity: Severity;
  similarity_score: number;
}

// Report types
export type ReportTemplate = 'STANDARD' | 'EXECUTIVE_SUMMARY' | 'DETAILED' | 'COMPLIANCE';

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

// API Error
export interface ApiError {
  detail: string | { msg: string; type: string }[];
}
