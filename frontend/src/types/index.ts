// User types
export type UserRole = 'admin' | 'auditor' | 'reviewer' | 'viewer';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: UserRole;
  department?: string;
  is_active: boolean;
  created_at?: string;
}

export interface UserBrief {
  id: string;
  full_name: string;
  email: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  full_name: string;
  role?: UserRole;
  department?: string;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: UserRole;
  department?: string;
  is_active?: boolean;
}

export interface UsersListResponse {
  items: User[];
  total: number;
  skip: number;
  limit: number;
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
  case_id_str?: string;
  file_name: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  file_hash?: string;
  description?: string;
  extracted_text?: string;
  uploaded_by: string;
  uploaded_by_name?: string;
  created_at: string;
  updated_at: string;
}

// Helper to derive evidence type from mime_type
export function getEvidenceType(mimeType?: string): EvidenceType {
  if (!mimeType) return 'OTHER';
  if (mimeType.startsWith('image/')) return 'IMAGE';
  if (mimeType.startsWith('video/')) return 'VIDEO';
  if (mimeType.startsWith('audio/')) return 'AUDIO';
  if (mimeType.includes('pdf') || mimeType.includes('document') || mimeType.includes('word')) return 'DOCUMENT';
  if (mimeType.includes('text/')) return 'LOG';
  if (mimeType.includes('message') || mimeType.includes('email')) return 'EMAIL';
  return 'OTHER';
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

// Analytics types
export interface StatusCount {
  status: string;
  count: number;
  percentage: number;
}

export interface SeverityCount {
  severity: string;
  count: number;
  percentage: number;
}

export interface TypeCount {
  type: string;
  count: number;
  percentage: number;
}

export interface ScopeCount {
  scope_code: string;
  scope_name: string;
  count: number;
  percentage: number;
}

export interface TrendDataPoint {
  date: string;
  created: number;
  closed: number;
}

export interface EntityTypeStats {
  entity_type: string;
  count: number;
  unique_values: number;
}

export interface TopEntity {
  value: string;
  entity_type: string;
  occurrence_count: number;
  case_count: number;
}

export interface UserActivityStat {
  user_id: string;
  user_email: string;
  action_count: number;
  last_activity: string;
}

export interface ActionCount {
  action: string;
  count: number;
}

export interface DashboardOverview {
  total_cases: number;
  open_cases: number;
  in_progress_cases: number;
  closed_cases: number;
  critical_cases: number;
  high_severity_cases: number;
  total_evidence: number;
  total_findings: number;
  total_entities: number;
  avg_resolution_days: number | null;
}

export interface CaseStatsResponse {
  by_status: StatusCount[];
  by_severity: SeverityCount[];
  by_type: TypeCount[];
  by_scope: ScopeCount[];
  total: number;
}

export interface TrendsResponse {
  data: TrendDataPoint[];
  period_days: number;
  granularity: string;
  total_created: number;
  total_closed: number;
}

export interface EvidenceFindingsStats {
  evidence_by_type: TypeCount[];
  evidence_by_status: StatusCount[];
  findings_by_severity: SeverityCount[];
  findings_by_status: StatusCount[];
  total_evidence: number;
  total_findings: number;
}

export interface EntityInsightsResponse {
  by_type: EntityTypeStats[];
  top_entities: TopEntity[];
  total_entities: number;
}

export interface UserActivityResponse {
  by_action: ActionCount[];
  top_users: UserActivityStat[];
  total_actions: number;
  period_days: number;
}

export interface FullAnalyticsResponse {
  overview: DashboardOverview;
  case_stats: CaseStatsResponse;
  trends: TrendsResponse;
  evidence_findings: EvidenceFindingsStats;
  entities: EntityInsightsResponse;
  user_activity: UserActivityResponse;
}
