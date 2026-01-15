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
    if (error.response?.status === 401) {
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
    skip?: number;
    limit?: number;
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
    const response = await api.get<Finding[]>(`/cases/${caseId}/findings`);
    return response.data;
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
    const response = await api.get<TimelineEvent[]>(`/cases/${caseId}/timeline`);
    return response.data;
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

export default api;
