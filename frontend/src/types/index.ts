// ============================================
// User Types
// ============================================

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  total_scans?: number;
  last_scan_at?: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  role?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

// ============================================
// Patient Types
// ============================================

export interface Patient {
  id: number;
  name: string;
  user_id?: number;
  date_of_birth?: string;
  gender?: string;
  phone?: string;
  email?: string;
  address?: string;
  medical_history?: string;
  created_at: string;
  updated_at: string;
}

export interface PatientCreate {
  name: string;
  user_id?: number;
  date_of_birth?: string;
  gender?: string;
  phone?: string;
  email?: string;
  address?: string;
  medical_history?: string;
}

export interface PatientWithInvitation extends Patient {
  invitation_token: string;
  invitation_url: string;
}

// ============================================
// Scan Types
// ============================================

export interface Scan {
  id: number;
  patient_id: number;
  scan_type?: string;
  scan_date?: string;
  file_path?: string;
  notes?: string;
  created_at: string;
}

export interface ScanCreate {
  patient_id: number;
  scan_type?: string;
  scan_date?: string;
  notes?: string;
}

// ============================================
// Prediction Types
// ============================================

export interface Prediction {
  id: number;
  patient_id: number;
  patient_name?: string;
  scan_id: number;
  user_id: number;
  prediction_class?: string;
  confidence?: number;
  probabilities?: string;
  is_reviewed: boolean;
  reviewed_by?: number;
  review_notes?: string;
  review_timestamp?: string;
  created_at: string;
  gradcam_image?: string;
  input_image?: string;
  status: string;
  error_message?: string;
  queue_time_ms?: number;
  process_time_ms?: number;
  user?: {
    id: number;
    username: string;
    full_name?: string;
    email?: string;
  };
}

export interface PredictionReview {
  reviewed_by: number;
  review_notes?: string;
}

// ============================================
// Statistics Types
// ============================================

export interface Statistics {
  total_patients: number;
  total_scans: number;
  total_predictions: number;
  predictions_pending_review: number;
  predictions_reviewed: number;
  predictions_by_label: Record<string, number>;
  recent_predictions: Prediction[];
  avg_queue_time_ms?: number;
  avg_process_time_ms?: number;
}

// ============================================
// API Response Types
// ============================================

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  skip: number;
  limit: number;
}

// ============================================
// Auth Types
// ============================================

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ValidationResponse {
  valid: boolean;
  user: User;
}
