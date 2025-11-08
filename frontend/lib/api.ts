/**
 * API Client Configuration for AI Education Platform
 * Handles communication between frontend and backend
 */

// Environment configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// API Client class
export class ApiClient {
  private baseURL: string;
  private defaultHeaders: HeadersInit;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  // Generic request method
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
      ...options,
    };

    // Add auth token if available
    const token = this.getAuthToken();
    if (token) {
      (config.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // GET request
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  // POST request
  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT request
  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE request
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // File upload
  async uploadFile<T>(endpoint: string, file: File, additionalData?: Record<string, any>): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, typeof value === 'string' ? value : JSON.stringify(value));
      });
    }

    const token = this.getAuthToken();
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  // Auth token management
  private getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token');
    }
    return null;
  }

  setAuthToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  clearAuthToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  // Health check
  async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    return this.get('/health');
  }

  // WebSocket connection
  createWebSocketConnection(endpoint: string): WebSocket {
    const wsUrl = `${WS_BASE_URL}${endpoint}`;
    return new WebSocket(wsUrl);
  }
}

// API endpoints
export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REGISTER: '/api/v1/auth/register',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
  },
  
  // Classes
  CLASSES: {
    LIST: '/api/v1/classes',
    CREATE: '/api/v1/classes',
    DETAIL: (id: string) => `/api/v1/classes/${id}`,
    UPDATE: (id: string) => `/api/v1/classes/${id}`,
    DELETE: (id: string) => `/api/v1/classes/${id}`,
  },
  
  // Assignments
  ASSIGNMENTS: {
    LIST: '/api/v1/assignments',
    CREATE: '/api/v1/assignments',
    DETAIL: (id: string) => `/api/v1/assignments/${id}`,
    UPDATE: (id: string) => `/api/v1/assignments/${id}`,
    DELETE: (id: string) => `/api/v1/assignments/${id}`,
  },
  
  // AI Grading
  GRADING: {
    SUBMIT_SYNC: '/api/v1/v2/grading/submit-sync',
    SUBMIT_ASYNC: '/api/v1/v2/grading/submit-async',
    STATUS: (submissionId: string) => `/api/v1/v2/grading/status/${submissionId}`,
    RESULT: (submissionId: string) => `/api/v1/v2/grading/result/${submissionId}`,
    CACHE_STATS: '/api/v1/v2/grading/cache/stats',
  },
  
  // File uploads
  UPLOADS: {
    IMAGE: '/api/v1/uploads/image',
    DOCUMENT: '/api/v1/uploads/document',
  },
  
  // Health
  HEALTH: '/health',
} as const;

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message?: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface GradingRequest {
  submission_id: string;
  assignment_id: string;
  mode: 'fast' | 'standard' | 'premium';
  max_score: number;
  config: {
    grading_standard: {
      criteria: string;
      answer: string;
    };
  };
}

export interface GradingResponse {
  submission_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    score: number;
    max_score: number;
    feedback: string;
    errors: Array<{
      type: string;
      message: string;
      location?: {
        x: number;
        y: number;
        width: number;
        height: number;
      };
    }>;
  };
}

// Create singleton instance
export const apiClient = new ApiClient();

// Utility functions
export const isApiAvailable = async (): Promise<boolean> => {
  try {
    await apiClient.healthCheck();
    return true;
  } catch {
    return false;
  }
};

export const getApiUrl = () => API_BASE_URL;
export const getWsUrl = () => WS_BASE_URL;