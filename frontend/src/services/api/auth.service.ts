import httpClient from '../http/http-client';
import type { AuthResponse, User, LoginCredentials, UserCreate, ValidationResponse } from '../../types';

// ============================================
// Auth Service
// ============================================

export const authService = {
  // Login
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await httpClient.post<AuthResponse>(
      '/api/auth/login',
      new URLSearchParams({
        username: credentials.username,
        password: credentials.password,
      }),
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      }
    );
    return response.data;
  },

  // Register
  register: async (userData: UserCreate): Promise<User> => {
    const response = await httpClient.post<User>('/api/register', userData);
    return response.data;
  },

  // Get current user
  getMe: async (): Promise<User> => {
    const response = await httpClient.get<User>('/api/auth/me');
    return response.data;
  },

  // Validate token
  validateToken: async (): Promise<ValidationResponse> => {
    const response = await httpClient.get<ValidationResponse>('/api/auth/validate');
    return response.data;
  },

  // Get all users (admin)
  getUsers: async (): Promise<User[]> => {
    const response = await httpClient.get<User[]>('/api/users');
    return response.data;
  },

  // Create user (admin)
  createUser: async (userData: UserCreate): Promise<User> => {
    const response = await httpClient.post<User>('/api/users', userData);
    return response.data;
  },
};

export default authService;
