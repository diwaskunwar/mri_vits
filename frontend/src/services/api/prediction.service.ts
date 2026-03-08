import httpClient from '../http/http-client';
import type { Statistics, User, UserCreate } from '../../types';

// ============================================
// Scan Service (predictions now in scans)
// ============================================

export const predictionService = {
  // Get all scans
  getAll: async (skip = 0, limit = 100): Promise<any[]> => {
    const response = await httpClient.get<any[]>(`/api/scans?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  // Create user (admin)
  createUser: async (userData: UserCreate): Promise<User> => {
    const response = await httpClient.post<User>('/api/users', userData);
    return response.data;
  },

  // Delete user (admin only)
  deleteUser: async (id: number): Promise<void> => {
    await httpClient.delete(`/api/users/${id}`);
  },

  // Get scan by ID
  getById: async (id: number): Promise<any> => {
    const response = await httpClient.get<any>(`/api/scans/${id}`);
    return response.data;
  },

  // Make prediction (create scan with GradCAM)
  predict: async (
    userId: number,
    file: File,
    scanType?: string,
    notes?: string
  ): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId.toString());
    if (scanType) formData.append('scan_type', scanType);
    if (notes) formData.append('notes', notes);

    const response = await httpClient.post<any>('/api/predict', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Review scan prediction
  review: async (scanId: number, reviewNotes?: string): Promise<any> => {
    const formData = new FormData();
    if (reviewNotes) formData.append('review_notes', reviewNotes);

    const response = await httpClient.post<any>(`/api/scans/${scanId}/review`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Get statistics
  getStatistics: async (): Promise<Statistics> => {
    const response = await httpClient.get<Statistics>('/api/statistics');
    return response.data;
  },

  // Get patients (users with role=patient)
  getPatients: async (): Promise<any[]> => {
    const response = await httpClient.get<any[]>('/api/patients');
    return response.data;
  },

  // Delete scan (admin only)
  deleteScan: async (id: number): Promise<void> => {
    await httpClient.delete(`/api/scans/${id}`);
  },
};

export default predictionService;
