/**
 * React hooks for API interactions
 * Provides easy-to-use hooks for components to interact with the backend
 */

import { useState, useEffect, useCallback } from 'react';
import { apiClient, API_ENDPOINTS, type HealthResponse, type GradingRequest, type GradingResponse } from '../lib/api';

// Generic hook for API requests
export function useApi<T>(
  endpoint: string,
  options: {
    immediate?: boolean;
    dependencies?: any[];
  } = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiClient.get<T>(endpoint);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    if (options.immediate !== false) {
      execute();
    }
  }, options.dependencies || [execute]);

  return { data, loading, error, refetch: execute };
}

// Health check hook
export function useHealthCheck() {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    try {
      const health = await apiClient.healthCheck();
      setHealthData(health);
      setIsHealthy(health.status === 'healthy');
    } catch {
      setIsHealthy(false);
      setHealthData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  return { isHealthy, healthData, loading, checkHealth };
}

// Authentication hook
export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const response: any = await apiClient.post(API_ENDPOINTS.AUTH.LOGIN, {
        email,
        password,
      });
      
      if (response.access_token) {
        apiClient.setAuthToken(response.access_token);
        setIsAuthenticated(true);
        setUser(response.user);
      }
      
      return response;
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    apiClient.clearAuthToken();
    setIsAuthenticated(false);
    setUser(null);
  }, []);

  const register = useCallback(async (userData: any) => {
    setLoading(true);
    try {
      const response = await apiClient.post(API_ENDPOINTS.AUTH.REGISTER, userData);
      return response;
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // Check if user is authenticated on mount
  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (token) {
      setIsAuthenticated(true);
      // You might want to validate the token with the backend here
    }
  }, []);

  return {
    isAuthenticated,
    user,
    loading,
    login,
    logout,
    register,
  };
}

// Classes hook
export function useClasses() {
  const [classes, setClasses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchClasses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.get(API_ENDPOINTS.CLASSES.LIST);
      setClasses(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch classes');
    } finally {
      setLoading(false);
    }
  }, []);

  const createClass = useCallback(async (classData: any) => {
    try {
      const newClass = await apiClient.post(API_ENDPOINTS.CLASSES.CREATE, classData);
      setClasses((prev: any[]) => [...prev, newClass]);
      return newClass;
    } catch (error) {
      throw error;
    }
  }, []);

  useEffect(() => {
    fetchClasses();
  }, [fetchClasses]);

  return {
    classes,
    loading,
    error,
    refetch: fetchClasses,
    createClass,
  };
}

// AI Grading hook
export function useGrading() {
  const [gradingResults, setGradingResults] = useState<Map<string, GradingResponse>>(new Map());
  const [loading, setLoading] = useState(false);

  const submitGrading = useCallback(async (request: GradingRequest): Promise<GradingResponse> => {
    setLoading(true);
    try {
      const result = await apiClient.post<GradingResponse>(
        API_ENDPOINTS.GRADING.SUBMIT_SYNC,
        request
      );
      
      setGradingResults((prev: Map<string, GradingResponse>) => new Map(prev).set(request.submission_id, result));
      return result;
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const getGradingResult = useCallback(async (submissionId: string): Promise<GradingResponse> => {
    try {
      const result = await apiClient.get<GradingResponse>(
        API_ENDPOINTS.GRADING.RESULT(submissionId)
      );
      setGradingResults((prev: Map<string, GradingResponse>) => new Map(prev).set(submissionId, result));
      return result;
    } catch (error) {
      throw error;
    }
  }, []);

  const getCacheStats = useCallback(async () => {
    try {
      return await apiClient.get(API_ENDPOINTS.GRADING.CACHE_STATS);
    } catch (error) {
      throw error;
    }
  }, []);

  return {
    gradingResults,
    loading,
    submitGrading,
    getGradingResult,
    getCacheStats,
  };
}

// File upload hook
export function useFileUpload() {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const uploadFile = useCallback(async (
    file: File,
    type: 'image' | 'document' = 'image',
    additionalData?: Record<string, any>
  ) => {
    setUploading(true);
    setUploadProgress(0);

    try {
      const endpoint = type === 'image' ? API_ENDPOINTS.UPLOADS.IMAGE : API_ENDPOINTS.UPLOADS.DOCUMENT;
      
      // Note: For real progress tracking, you'd need to implement XMLHttpRequest
      // This is a simplified version
      const result = await apiClient.uploadFile(endpoint, file, additionalData);
      setUploadProgress(100);
      return result;
    } catch (error) {
      throw error;
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, []);

  return {
    uploading,
    uploadProgress,
    uploadFile,
  };
}

// WebSocket hook for real-time updates
export function useWebSocket(endpoint: string) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);

  useEffect(() => {
    const ws = apiClient.createWebSocketConnection(endpoint);
    
    ws.onopen = () => {
      setConnected(true);
      setSocket(ws);
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      } catch {
        setLastMessage(event.data);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setSocket(null);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [endpoint]);

  const sendMessage = useCallback((message: any) => {
    if (socket && connected) {
      socket.send(typeof message === 'string' ? message : JSON.stringify(message));
    }
  }, [socket, connected]);

  return {
    connected,
    lastMessage,
    sendMessage,
  };
}

// Assignments hook
export function useAssignments() {
  const [assignments, setAssignments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAssignments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.get(API_ENDPOINTS.ASSIGNMENTS.LIST);
      setAssignments(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch assignments');
    } finally {
      setLoading(false);
    }
  }, []);

  const createAssignment = useCallback(async (assignmentData: any) => {
    try {
      const newAssignment = await apiClient.post(API_ENDPOINTS.ASSIGNMENTS.CREATE, assignmentData);
      setAssignments((prev: any[]) => [...prev, newAssignment]);
      return newAssignment;
    } catch (error) {
      throw error;
    }
  }, []);

  useEffect(() => {
    fetchAssignments();
  }, [fetchAssignments]);

  return {
    assignments,
    loading,
    error,
    refetch: fetchAssignments,
    createAssignment,
  };
}