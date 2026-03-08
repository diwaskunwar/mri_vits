import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Menu, X, Home, Users, ScanLine, LogOut, Brain, FileText } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

// ============================================
// Navigation items based on role
// ============================================

const ADMIN_NAV = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/patients', label: 'Patients', icon: Users },
  { path: '/scans/new', label: 'New Scan', icon: ScanLine },
  { path: '/predictions', label: 'Predictions', icon: FileText },
];

const DOCTOR_NAV = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/patients', label: 'Patients', icon: Users },
  { path: '/scans/new', label: 'New Scan', icon: ScanLine },
  { path: '/predictions', label: 'Predictions', icon: FileText },
];

const PATIENT_NAV = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/predictions', label: 'My Scans', icon: ScanLine },
  { path: '/scans/new', label: 'Add Scan', icon: Brain },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, isAdmin, isPatient, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Get navigation items based on role
  const getNavItems = () => {
    if (isAdmin) return ADMIN_NAV;
    if (isPatient) return PATIENT_NAV;
    return DOCTOR_NAV;
  };

  const NAV_ITEMS = getNavItems();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* ── Sidebar ── */}
      <aside
        className={`
          fixed top-0 left-0 h-full w-60 flex flex-col z-40
          bg-[#0A0A0A]
          transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
      >
        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/[0.07]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-white rounded-md flex items-center justify-center shrink-0">
              <Brain size={14} className="text-black" />
            </div>
            <span className="text-white font-semibold text-[14px] tracking-tight">
              Candor Dust
            </span>
          </div>
        </div>

        {/* Role badge */}
        {user && (
          <div className="px-4 py-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${user.role === 'admin' ? 'bg-red-100 text-red-800' :
              user.role === 'doctor' ? 'bg-blue-100 text-blue-800' :
                'bg-green-100 text-green-800'
              }`}>
              {user.role.toUpperCase()}
            </span>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-px">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-2.5 px-3 py-2.5 rounded-lg
                  text-[13px] font-medium transition-all duration-150
                  ${active
                    ? 'bg-white text-[#0A0A0A]'
                    : 'text-[#909090] hover:text-white hover:bg-white/[0.08]'
                  }
                `}
              >
                <Icon size={15} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User info + Logout */}
        <div className="px-3 py-3 border-t border-white/[0.07] space-y-0.5">
          {user && (
            <div className="px-3 py-2">
              <p className="text-[10px] font-semibold text-[#484848] uppercase tracking-widest">
                Account
              </p>
              <p className="text-[12.5px] text-[#C8C8C8] mt-0.5 truncate">
                {user.full_name || user.username}
              </p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2.5 px-3 py-2.5 w-full rounded-lg
              text-[13px] font-medium text-[#909090]
              hover:text-white hover:bg-white/[0.08] transition-all duration-150"
          >
            <LogOut size={15} />
            Log out
          </button>
        </div>
      </aside>

      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Mobile top bar */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-14 bg-white border-b border-gray-200 flex items-center px-4 z-50">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="ml-3 flex items-center gap-2">
          <div className="w-6 h-6 bg-black rounded flex items-center justify-center">
            <Brain size={12} className="text-white" />
          </div>
          <span className="font-semibold text-[14px]">Candor Dust</span>
        </div>
      </header>

      {/* Main content — fade-in on route change */}
      <main className="flex-1 lg:ml-60 pt-14 lg:pt-0 min-h-screen flex flex-col">
        <div className="p-5 lg:p-8 animate-fade-in flex-1">
          {children}
        </div>

        {/* Disclaimer footer */}
        <footer className="lg:ml-0 px-5 lg:px-8 py-3 border-t border-gray-200 bg-gray-50">
          <p className="text-[11px] text-gray-400 text-center">
            ⚠️ Research prototype only — NOT a certified medical device. Not for clinical use.
            Always consult qualified healthcare professionals for medical decisions.
          </p>
        </footer>
      </main>
    </div>
  );
}
