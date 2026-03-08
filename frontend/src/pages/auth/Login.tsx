import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { authService } from '../../services/api';
import { Eye, EyeOff, Brain } from 'lucide-react';

// ============================================
// Login Page — split B&W layout
// ============================================

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await authService.login({ username, password });
      login(response.user, response.access_token);
      navigate('/');
    } catch {
      setError('Invalid username or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* ── Left: Brand panel ── */}
      <div className="hidden lg:flex w-[42%] bg-[#0A0A0A] flex-col justify-between p-10 shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 animate-slide-left">
          <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
            <Brain size={16} className="text-black" />
          </div>
          <span className="text-white font-semibold text-[14px] tracking-tight">Candor Dust</span>
        </div>

        {/* Center copy */}
        <div className="animate-slide-up" style={{ animationDelay: '0.1s' }}>
          <h1 className="text-[2.6rem] font-bold text-white leading-[1.2] tracking-tight">
            Brain Tumor<br />Detection<br />System
          </h1>
          <p className="text-[#666666] mt-5 text-[14.5px] leading-relaxed max-w-xs">
            AI-powered MRI analysis for accurate tumor classification, clinical review and patient management.
          </p>
        </div>

        {/* Footer */}
        <p className="text-[#333333] text-[11px]">© 2026 Candor Dust. All rights reserved.</p>
      </div>

      {/* ── Right: Form panel ── */}
      <div className="flex-1 bg-white flex items-center justify-center p-8">
        <div className="w-full max-w-sm animate-slide-up">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
              <Brain size={16} className="text-white" />
            </div>
            <span className="font-semibold text-[14px]">Candor Dust</span>
          </div>

          <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Welcome back</h2>
          <p className="text-[13.5px] text-gray-500 mt-1">Sign in to your account to continue.</p>

          {error && (
            <div className="mt-5 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-[13px] text-gray-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-7 space-y-4">
            <div>
              <label className="block text-[12.5px] font-medium text-gray-700 mb-1.5 uppercase tracking-wide">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg bg-white
                  text-gray-900 placeholder:text-gray-400
                  focus:outline-none focus:border-gray-900 transition-colors"
                placeholder="Enter your username"
                required
                autoComplete="username"
              />
            </div>

            <div>
              <label className="block text-[12.5px] font-medium text-gray-700 mb-1.5 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 pr-11 text-sm border border-gray-300 rounded-lg bg-white
                    text-gray-900 placeholder:text-gray-400
                    focus:outline-none focus:border-gray-900 transition-colors"
                  placeholder="Enter your password"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-[#0A0A0A] hover:bg-black text-white
                font-medium rounded-lg transition-all duration-150 text-[13.5px]
                disabled:opacity-50 disabled:cursor-not-allowed mt-2
                flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-[13px] text-gray-500">
            Don't have an account?{' '}
            <Link to="/register" className="text-gray-900 font-medium hover:underline">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
