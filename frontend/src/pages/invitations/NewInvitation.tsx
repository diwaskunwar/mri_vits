import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import httpClient from '../../services/http/http-client';
import { ArrowLeft, Send, Copy, Check, X } from 'lucide-react';

interface InvitationData {
  role: string;
  name: string;
  surname?: string;
  email?: string;
}

export default function NewInvitation() {
  const navigate = useNavigate();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [inviteLink, setInviteLink] = useState('');
  const [copied, setCopied] = useState(false);

  const [formData, setFormData] = useState<InvitationData>({
    role: 'patient',
    name: '',
    surname: '',
    email: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) {
      setError('Name is required');
      return;
    }

    setSending(true);
    setError('');

    try {
      const response = await httpClient.post('/api/invitations', formData);
      
      // Build invite URL
      const link = `${window.location.origin}/invite/${response.data.token}`;
      setInviteLink(link);
      setShowModal(true);
      setFormData({ role: 'patient', name: '', surname: '', email: '' });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create invitation');
    } finally {
      setSending(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/patients')}
        className="flex items-center gap-1.5 text-[13px] text-gray-500 hover:text-gray-900"
      >
        <ArrowLeft size={15} />
        Patients
      </button>

      <div>
        <h1 className="text-xl font-semibold text-gray-900">Invite Patient</h1>
        <p className="text-[13px] text-gray-500 mt-0.5">Send an invitation link to a new patient</p>
      </div>

      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-[13px] text-red-700">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-md mx-auto mt-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-[12px] font-semibold text-gray-500 mb-1.5 uppercase tracking-widest">
              Role
            </label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:border-gray-900"
            >
              <option value="patient">Patient</option>
              <option value="doctor">Doctor</option>
            </select>
          </div>

          <div>
            <label className="block text-[12px] font-semibold text-gray-500 mb-1.5 uppercase tracking-widest">
              Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-gray-900"
              placeholder="First name"
              required
            />
          </div>

          <div>
            <label className="block text-[12px] font-semibold text-gray-500 mb-1.5 uppercase tracking-widest">
              Surname
            </label>
            <input
              type="text"
              value={formData.surname}
              onChange={(e) => setFormData({ ...formData, surname: e.target.value })}
              className="w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-gray-900"
              placeholder="Last name"
            />
          </div>

          <div>
            <label className="block text-[12px] font-semibold text-gray-500 mb-1.5 uppercase tracking-widest">
              Email (optional)
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-gray-900"
              placeholder="email@example.com"
            />
          </div>

          <button
            type="submit"
            disabled={sending}
            className="w-full py-2.5 px-4 bg-black text-white rounded-lg text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {sending ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send size={15} />
                Send Invitation
              </>
            )}
          </button>
        </form>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Invitation Sent!</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Share this link with the patient:
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={inviteLink}
                readOnly
                className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-gray-50"
              />
              <button
                onClick={copyToClipboard}
                className="px-3 py-2 bg-gray-900 text-white rounded-lg flex items-center gap-1 text-sm"
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <button
              onClick={() => setShowModal(false)}
              className="w-full mt-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
