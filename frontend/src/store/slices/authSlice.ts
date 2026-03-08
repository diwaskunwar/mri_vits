import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { User } from '../../types';

// ============================================
// Auth Slice — manages user identity globally
// ============================================

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('access_token'),
  loading: true,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (state, action: PayloadAction<{ user: User; token: string }>) => {
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.loading = false;
    },
    clearCredentials: (state) => {
      state.user = null;
      state.token = null;
      state.loading = false;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
  },
});

export const { setCredentials, clearCredentials, setLoading } = authSlice.actions;

// Selectors
export const selectCurrentUser = (state: { auth: AuthState }) => state.auth.user;
export const selectIsAuthenticated = (state: { auth: AuthState }) => !!state.auth.user;
export const selectIsAdmin = (state: { auth: AuthState }) => state.auth.user?.role === 'admin';
export const selectIsDoctor = (state: { auth: AuthState }) => state.auth.user?.role === 'doctor';
export const selectIsPatient = (state: { auth: AuthState }) => state.auth.user?.role === 'patient';
export const selectIsStaff = (state: { auth: AuthState }) =>
  state.auth.user?.role === 'admin' || state.auth.user?.role === 'doctor';

export default authSlice.reducer;
