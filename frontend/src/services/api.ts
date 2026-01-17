import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  Case,
  CaseCreate,
  CaseUpdate,
  CaseSummary,
  Evidence,
  Finding,
  FindingCreate,
  LoginRequest,
  LoginResponse,
  PaginatedResponse,
  Scope,
  SimilarCase,
  TimelineEvent,
  Entity,
  ReportTemplate,
  User,
  UserCreate,
  UserUpdate,
  UsersListResponse,
  DashboardOverview,
  CaseStatsResponse,
  TrendsResponse,
  EvidenceFindingsStats,
  EntityInsightsResponse,
  UserActivityResponse,
  FullAnalyticsResponse,
  Notification,
  NotificationListResponse,
  NotificationCountResponse,
  WorkflowRule,
  WorkflowRuleCreate,
  WorkflowRuleUpdate,
  WorkflowRuleListResponse,
  WorkflowAction,
  WorkflowHistory,
  WorkflowHistoryListResponse,
  SearchEntityType,
  SearchMode,
  SearchResponse,
  SearchSuggestResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Only redirect on 401 if NOT the login endpoint (login failures should show error, not redirect)
    const isLoginEndpoint = error.config?.url?.includes('/auth/login');
    if (error.response?.status === 401 && !isLoginEndpoint) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await api.post<LoginResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  getMe: async (): Promise<LoginResponse> => {
    const response = await api.get<LoginResponse>('/auth/me');
    return response.data;
  },

  register: async (data: {
    email: string;
    username: string;
    password: string;
    full_name: string;
    role?: string;
  }): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/register', data);
    return response.data;
  },
};

// Cases API
export const casesApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    severity?: string;
    scope_code?: string;
    case_type?: string;
    search?: string;
  }): Promise<PaginatedResponse<Case>> => {
    const response = await api.get<PaginatedResponse<Case>>('/cases', { params });
    return response.data;
  },

  get: async (caseId: string): Promise<Case> => {
    const response = await api.get<Case>(`/cases/${caseId}`);
    return response.data;
  },

  create: async (data: CaseCreate): Promise<Case> => {
    const response = await api.post<Case>('/cases', data);
    return response.data;
  },

  update: async (caseId: string, data: CaseUpdate): Promise<Case> => {
    const response = await api.patch<Case>(`/cases/${caseId}`, data);
    return response.data;
  },

  delete: async (caseId: string): Promise<void> => {
    await api.delete(`/cases/${caseId}`);
  },
};

// Evidence API
export const evidenceApi = {
  list: async (caseId: string): Promise<Evidence[]> => {
    const response = await api.get<{ items: Evidence[]; total: number; case_id: string }>(`/evidence/cases/${caseId}`);
    return response.data.items;
  },

  upload: async (caseId: string, file: File, description?: string): Promise<Evidence> => {
    const formData = new FormData();
    formData.append('file', file);
    if (description) {
      formData.append('description', description);
    }

    const response = await api.post<Evidence>(`/evidence/cases/${caseId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  download: async (evidenceId: string): Promise<Blob> => {
    const response = await api.get(`/evidence/${evidenceId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  delete: async (evidenceId: string): Promise<void> => {
    await api.delete(`/evidence/${evidenceId}`);
  },
};

// Findings API
export const findingsApi = {
  list: async (caseId: string): Promise<Finding[]> => {
    const response = await api.get<{ items: Finding[]; total: number }>(`/cases/${caseId}/findings`);
    return response.data.items || [];
  },

  create: async (caseId: string, data: FindingCreate): Promise<Finding> => {
    const response = await api.post<Finding>(`/cases/${caseId}/findings`, data);
    return response.data;
  },

  update: async (caseId: string, findingId: string, data: Partial<FindingCreate>): Promise<Finding> => {
    const response = await api.patch<Finding>(`/cases/${caseId}/findings/${findingId}`, data);
    return response.data;
  },

  delete: async (caseId: string, findingId: string): Promise<void> => {
    await api.delete(`/cases/${caseId}/findings/${findingId}`);
  },
};

// Timeline API
export const timelineApi = {
  list: async (caseId: string): Promise<TimelineEvent[]> => {
    const response = await api.get<{ items: TimelineEvent[]; total: number }>(`/cases/${caseId}/timeline`);
    return response.data.items || [];
  },

  create: async (caseId: string, data: {
    event_time: string;
    event_type: string;
    description: string;
    source?: string;
  }): Promise<TimelineEvent> => {
    const response = await api.post<TimelineEvent>(`/cases/${caseId}/timeline`, data);
    return response.data;
  },
};

// Entities API
export const entitiesApi = {
  list: async (caseId: string): Promise<Entity[]> => {
    const response = await api.get<Entity[]>(`/entities/case/${caseId}`);
    return response.data;
  },

  summary: async (caseId: string): Promise<Record<string, number>> => {
    const response = await api.get<Record<string, number>>(`/entities/case/${caseId}/summary`);
    return response.data;
  },

  search: async (value: string, entityType?: string): Promise<Entity[]> => {
    const response = await api.get<Entity[]>('/entities/search', {
      params: { value, entity_type: entityType },
    });
    return response.data;
  },
};

// Scopes API
export const scopesApi = {
  list: async (): Promise<Scope[]> => {
    const response = await api.get<Scope[]>('/scopes');
    return response.data;
  },
};

// AI API
export const aiApi = {
  summarize: async (caseId: string): Promise<CaseSummary> => {
    const response = await api.post<CaseSummary>(`/ai/summarize/${caseId}`);
    return response.data;
  },

  findSimilar: async (caseId: string, params?: {
    limit?: number;
    min_similarity?: number;
    same_scope_only?: boolean;
  }): Promise<SimilarCase[]> => {
    const response = await api.get<SimilarCase[]>(`/ai/similar-cases/${caseId}`, { params });
    return response.data;
  },

  generateEmbeddings: async (caseId: string): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(`/ai/embed/case/${caseId}`);
    return response.data;
  },

  health: async (): Promise<{
    ollama_available: boolean;
    ollama_models: string[];
    rag_available: boolean;
  }> => {
    const response = await api.get('/ai/health');
    return response.data;
  },
};

// Reports API
export const reportsApi = {
  generate: async (caseId: string, options?: {
    template?: ReportTemplate;
    include_evidence?: boolean;
    include_similar?: boolean;
    include_ai_summary?: boolean;
    watermark?: string;
  }): Promise<Blob> => {
    const params = new URLSearchParams();
    if (options?.template) params.append('template', options.template);
    if (options?.include_evidence !== undefined) params.append('include_evidence', String(options.include_evidence));
    if (options?.include_similar !== undefined) params.append('include_similar', String(options.include_similar));
    if (options?.include_ai_summary !== undefined) params.append('include_ai_summary', String(options.include_ai_summary));
    if (options?.watermark) params.append('watermark', options.watermark);

    const response = await api.get(`/reports/case/${caseId}.docx?${params.toString()}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  templates: async (): Promise<{ templates: Array<{ name: string; description: string }> }> => {
    const response = await api.get('/reports/templates');
    return response.data;
  },
};

// Sync API
export const syncApi = {
  status: async (): Promise<{ paperless_available: boolean }> => {
    const response = await api.get('/sync/status');
    return response.data;
  },

  syncCase: async (caseId: string): Promise<{ synced: number; failed: number }> => {
    const response = await api.post(`/sync/case/${caseId}`);
    return response.data;
  },
};

// Nextcloud API
export const nextcloudApi = {
  health: async (): Promise<{
    available: boolean;
    installed?: boolean;
    version?: string;
    maintenance?: boolean;
  }> => {
    const response = await api.get('/nextcloud/health');
    return response.data;
  },

  createCaseFolder: async (caseId: string): Promise<{
    case_id: string;
    folders_created: string[];
    success: boolean;
    folder_url?: string;
  }> => {
    const response = await api.post(`/nextcloud/case/${caseId}/folder`);
    return response.data;
  },

  getCaseFolderUrl: async (caseId: string): Promise<{ case_id: string; url: string }> => {
    const response = await api.get(`/nextcloud/case/${caseId}/url`);
    return response.data;
  },

  listCaseFiles: async (caseId: string, subfolder?: string): Promise<{
    path: string;
    items: Array<{
      name: string;
      path: string;
      is_directory: boolean;
      content_type?: string;
      size: number;
      last_modified?: string;
    }>;
    count: number;
  }> => {
    const params = subfolder ? { subfolder } : {};
    const response = await api.get(`/nextcloud/case/${caseId}/files`, { params });
    return response.data;
  },

  uploadToCaseFolder: async (caseId: string, file: File, subfolder: string = 'Evidence'): Promise<{ message: string }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post(`/nextcloud/case/${caseId}/upload?subfolder=${subfolder}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

// ONLYOFFICE API
export const onlyofficeApi = {
  health: async (): Promise<{
    available: boolean;
    version?: string;
    build?: string;
    external_url?: string;
    error?: string;
  }> => {
    const response = await api.get('/onlyoffice/health');
    return response.data;
  },

  getExtensions: async (): Promise<{
    documents: string[];
    spreadsheets: string[];
    presentations: string[];
    editable: string[];
  }> => {
    const response = await api.get('/onlyoffice/extensions');
    return response.data;
  },

  getEditUrl: async (filePath: string): Promise<{
    file_path: string;
    edit_url: string;
    document_type?: string;
    is_editable: boolean;
    is_viewable: boolean;
  }> => {
    const response = await api.get('/onlyoffice/edit-url', {
      params: { file_path: filePath },
    });
    return response.data;
  },

  getCaseDocuments: async (caseId: string, subfolder?: string): Promise<{
    case_id: string;
    documents: Array<{
      file_path: string;
      edit_url: string;
      document_type?: string;
      is_editable: boolean;
      is_viewable: boolean;
    }>;
    total: number;
  }> => {
    const params = subfolder ? { subfolder } : {};
    const response = await api.get(`/onlyoffice/case/${caseId}/documents`, { params });
    return response.data;
  },

  getEditorUrl: async (): Promise<{ editor_url: string }> => {
    const response = await api.get('/onlyoffice/editor-url');
    return response.data;
  },
};

// Users API (Admin only)
export const usersApi = {
  list: async (params?: { skip?: number; limit?: number }): Promise<UsersListResponse> => {
    const response = await api.get<UsersListResponse>('/auth/users', { params });
    return response.data;
  },

  get: async (userId: string): Promise<User> => {
    const response = await api.get<User>(`/auth/users/${userId}`);
    return response.data;
  },

  create: async (data: UserCreate): Promise<User> => {
    const response = await api.post<User>('/auth/register', data);
    return response.data;
  },

  update: async (userId: string, data: UserUpdate): Promise<User> => {
    const response = await api.patch<User>(`/auth/users/${userId}`, data);
    return response.data;
  },

  deactivate: async (userId: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/auth/users/${userId}`);
    return response.data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};

// Analytics API
export const analyticsApi = {
  getOverview: async (): Promise<DashboardOverview> => {
    const response = await api.get<DashboardOverview>('/analytics/overview');
    return response.data;
  },

  getCaseStats: async (scope?: string): Promise<CaseStatsResponse> => {
    const params = scope ? { scope } : {};
    const response = await api.get<CaseStatsResponse>('/analytics/cases', { params });
    return response.data;
  },

  getTrends: async (days: number = 30, granularity: string = 'day'): Promise<TrendsResponse> => {
    const response = await api.get<TrendsResponse>('/analytics/trends', {
      params: { days, granularity },
    });
    return response.data;
  },

  getEvidenceFindings: async (): Promise<EvidenceFindingsStats> => {
    const response = await api.get<EvidenceFindingsStats>('/analytics/evidence-findings');
    return response.data;
  },

  getEntityInsights: async (entityType?: string, limit: number = 10): Promise<EntityInsightsResponse> => {
    const params: Record<string, string | number> = { limit };
    if (entityType) params.entity_type = entityType;
    const response = await api.get<EntityInsightsResponse>('/analytics/entities', { params });
    return response.data;
  },

  getUserActivity: async (days: number = 30, limit: number = 10): Promise<UserActivityResponse> => {
    const response = await api.get<UserActivityResponse>('/analytics/activity', {
      params: { days, limit },
    });
    return response.data;
  },

  getFullAnalytics: async (days: number = 30): Promise<FullAnalyticsResponse> => {
    const response = await api.get<FullAnalyticsResponse>('/analytics/full', {
      params: { days },
    });
    return response.data;
  },
};

// Notifications API
export const notificationsApi = {
  list: async (params?: {
    page?: number;
    page_size?: number;
    unread_only?: boolean;
  }): Promise<NotificationListResponse> => {
    const response = await api.get<NotificationListResponse>('/notifications', { params });
    return response.data;
  },

  getUnreadCount: async (): Promise<NotificationCountResponse> => {
    const response = await api.get<NotificationCountResponse>('/notifications/unread-count');
    return response.data;
  },

  get: async (id: string): Promise<Notification> => {
    const response = await api.get<Notification>(`/notifications/${id}`);
    return response.data;
  },

  markAsRead: async (id: string): Promise<{ message: string; marked_count: number }> => {
    const response = await api.patch<{ message: string; marked_count: number }>(
      `/notifications/${id}/read`
    );
    return response.data;
  },

  markAllAsRead: async (): Promise<{ message: string; marked_count: number }> => {
    const response = await api.post<{ message: string; marked_count: number }>(
      '/notifications/mark-all-read'
    );
    return response.data;
  },

  delete: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/notifications/${id}`);
    return response.data;
  },
};

// Workflows API (Admin only)
export const workflowsApi = {
  // Rules
  listRules: async (params?: {
    page?: number;
    page_size?: number;
    is_enabled?: boolean;
    trigger_type?: string;
  }): Promise<WorkflowRuleListResponse> => {
    const response = await api.get<WorkflowRuleListResponse>('/workflows/rules', { params });
    return response.data;
  },

  getRule: async (id: string): Promise<WorkflowRule> => {
    const response = await api.get<WorkflowRule>(`/workflows/rules/${id}`);
    return response.data;
  },

  createRule: async (data: WorkflowRuleCreate): Promise<WorkflowRule> => {
    const response = await api.post<WorkflowRule>('/workflows/rules', data);
    return response.data;
  },

  updateRule: async (id: string, data: WorkflowRuleUpdate): Promise<WorkflowRule> => {
    const response = await api.patch<WorkflowRule>(`/workflows/rules/${id}`, data);
    return response.data;
  },

  deleteRule: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/workflows/rules/${id}`);
    return response.data;
  },

  toggleRule: async (id: string, enabled: boolean): Promise<WorkflowRule> => {
    const response = await api.post<WorkflowRule>(`/workflows/rules/${id}/toggle`, { enabled });
    return response.data;
  },

  // Actions
  getRuleActions: async (ruleId: string): Promise<WorkflowAction[]> => {
    const response = await api.get<WorkflowAction[]>(`/workflows/rules/${ruleId}/actions`);
    return response.data;
  },

  addAction: async (
    ruleId: string,
    data: { action_type: string; action_config: Record<string, unknown>; sequence?: number }
  ): Promise<WorkflowAction> => {
    const response = await api.post<WorkflowAction>(`/workflows/rules/${ruleId}/actions`, data);
    return response.data;
  },

  updateAction: async (
    actionId: string,
    data: { action_config?: Record<string, unknown>; sequence?: number }
  ): Promise<WorkflowAction> => {
    const response = await api.patch<WorkflowAction>(`/workflows/actions/${actionId}`, data);
    return response.data;
  },

  deleteAction: async (actionId: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/workflows/actions/${actionId}`);
    return response.data;
  },

  // History
  getRuleHistory: async (
    ruleId: string,
    params?: { page?: number; page_size?: number }
  ): Promise<WorkflowHistoryListResponse> => {
    const response = await api.get<WorkflowHistoryListResponse>(
      `/workflows/rules/${ruleId}/history`,
      { params }
    );
    return response.data;
  },

  getAllHistory: async (params?: {
    page?: number;
    page_size?: number;
    rule_id?: string;
    case_id?: string;
    success?: boolean;
  }): Promise<WorkflowHistoryListResponse> => {
    const response = await api.get<WorkflowHistoryListResponse>('/workflows/history', { params });
    return response.data;
  },

  // Manual trigger
  triggerRule: async (ruleId: string, caseId: string): Promise<WorkflowHistory> => {
    const response = await api.post<WorkflowHistory>(
      `/workflows/rules/${ruleId}/trigger/${caseId}`
    );
    return response.data;
  },
};

// Search API
export const searchApi = {
  search: async (params: {
    q: string;
    entity_types?: SearchEntityType[];
    mode?: SearchMode;
    scope_code?: string;
    severity?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Promise<SearchResponse> => {
    const response = await api.get<SearchResponse>('/search', { params });
    return response.data;
  },

  suggest: async (q: string, limit?: number): Promise<SearchSuggestResponse> => {
    const response = await api.get<SearchSuggestResponse>('/search/suggest', {
      params: { q, limit },
    });
    return response.data;
  },
};

export default api;
