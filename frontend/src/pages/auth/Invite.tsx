import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import httpClient from '../../services/http/http-client';
import { ArrowLeft, Eye, EyeOff, Loader2 } from 'lucide-react';

interface InvitationData {
  id: number;
  token: string;
  role: string;
  name: string;
  surname: string | null;
  email: string | null;
  invited_by_user_id: number;
  is_used: boolean;
  expires_at: string;
  created_at: string;
}

// ============================================
// Invite Page - Accept Invitation
// ============================================

const inputClass =
  'w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg bg-white ' +
  'text-gray-900 placeholder:text-gray-400 ' +
  'focus:outline-none focus:border-gray-900 transition-colors';

const labelClass = 'block text-[12px] font-semibold text-gray-500 mb-1.5 uppercase tracking-widest';

export default function Invite() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invitation, setInvitation] = useState<InvitationData | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  useEffect(() => {
    const verifyInvitation = async () => {
      if (!token) {
        setError('Invalid invitation token');
        setLoading(false);
        return;
      }

      try {
        const response = await httpClient.get<InvitationData>(`/api/invitations/verify/${token}`);
        setInvitation(response.data);
      } catch (err: any) {
        if (err.response?.status === 404) {
          setError('Invalid invitation token');
        } else if (err.response?.status === 400) {
          setError(err.response.data.detail || 'Invitation unavailable');
        } else {
          setError('Failed to verify invitation');
        }
      } finally {
        setLoading(false);
      }
    };

    verifyInvitation();
  }, [token]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    setSubmitting(true);
    setError(null);

    try {
      await httpClient.post('/api/invitations/accept', {
        token,
        username: formData.username,
        password: formData.password,
      });

      // Redirect to login with success message
      navigate('/login', { state: { message: 'Account created! Please login.' } });
    } catch (err: any) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to create account');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error || !invitation) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <ArrowLeft className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="text-xl font-semibold text-gray-900 mb-2">Invalid Invitation</h1>
          <p className="text-gray-500 mb-6">{error || 'This invitation is not available'}</p>
          <button
            onClick={() => navigate('/login')}
            className="px-6 py-2.5 bg-[#0A0A0A] hover:bg-black text-white font-medium rounded-lg transition-colors"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  const fullName = invitation.surname
    ? `${invitation.name} ${invitation.surname}`
    : invitation.name;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">🎉</span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">You're Invited!</h1>
          <p className="text-gray-500 mt-1">Create your account to get started</p>
        </div>

        {/* Invitation Info */}
        <div className="bg-gray-50 rounded-xl p-4 mb-6">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Name</p>
              <p className="font-medium text-gray-900">{fullName}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Role</p>
              <p className="font-medium text-gray-900 capitalize">{invitation.role}</p>
            </div>
            {invitation.email && (
              <div className="col-span-2">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Email</p>
                <p className="font-medium text-gray-900">{invitation.email}</p>
              </div>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Username *</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              className={inputClass}
              placeholder="Choose a username"
            />
          </div>

          <div>
            <label className={labelClass}>Password *</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                minLength={6}
                className={inputClass}
                placeholder="Create a password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 bg-[#0A0A0A] hover:bg-black text-white font-medium rounded-lg transition-colors text-[13.5px] flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Creating Account...
              </>
            ) : (
              'Create Account'
            )}
          </button>
        </form>

        <p className="text-xs text-gray-400 text-center mt-4">
          Already have an account?{' '}
          <button onClick={() => navigate('/login')} className="text-gray-900 hover:underline">
            Login
          </button>
        </p>
      </div>
    </div>
  );
}
