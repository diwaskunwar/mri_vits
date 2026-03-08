import axios from 'axios';
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

// ============================================
// HTTP Client Configuration
// ============================================

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Create axios instance
const httpClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// ============================================
// Request Interceptor - Add Auth Token
// ============================================

httpClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// ============================================
// Response Interceptor - Handle Errors
// ============================================

httpClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Don't redirect on 401 for GET requests or actual login request
    if (
      error.response?.status === 401 &&
      error.config?.method !== 'get' &&
      !error.config?.url?.includes('/api/auth/login')
    ) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ============================================
// Export
// ============================================

export default httpClient;
