import { useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from '../store';
import {
  setCredentials,
  clearCredentials,
  selectCurrentUser,
  selectIsAdmin,
  selectIsDoctor,
  selectIsPatient,
  selectIsStaff
} from '../store/slices/authSlice';
import type { User } from '../types';

// ============================================
// useAuth — Redux-backed auth hook
// ============================================

export const useAuth = () => {
  const dispatch = useDispatch<AppDispatch>();
  const user = useSelector(selectCurrentUser);
  const isAdmin = useSelector(selectIsAdmin);
  const isDoctor = useSelector(selectIsDoctor);
  const isPatient = useSelector(selectIsPatient);
  const isStaff = useSelector(selectIsStaff);
  const loading = useSelector((state: RootState) => state.auth.loading);

  const login = (userData: User, token: string) => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    dispatch(setCredentials({ user: userData, token }));
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    dispatch(clearCredentials());
  };

  return { user, loading, login, logout, isAdmin, isDoctor, isPatient, isStaff };
};
