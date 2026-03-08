import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { predictionService } from '../../services/api';
import { PageLoader } from '../../components/ui/Spinner';
import { TumorBadge, ProcessStatusBadge } from '../../components/ui/Badge';
import { useAuth } from '../../hooks/useAuth';
import { ArrowLeft, User, Mail, Calendar, Activity, Trash2 } from 'lucide-react';
import { ConfirmDeleteModal } from '../../components/ui/ConfirmDeleteModal';

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const [patient, setPatient] = useState<any>(null);
  const [scans, setScans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  useEffect(() => {
    if (id) loadData();
  }, [id]);

  const loadData = async () => {
    try {
      // Get all patients and find this one (simplest since we don't have a specific getPatientByID endpoint yet)
      const allPatients = await predictionService.getPatients();
      const p = allPatients.find((p: any) => p.id === parseInt(id!));
      setPatient(p);

      // Get all scans and filter for this patient
      const allScans = await predictionService.getAll();
      const pScans = allScans.filter((s: any) => s.user_id === parseInt(id!));
      setScans(pScans);
    } catch (err) {
      console.error('Failed to load patient data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <PageLoader />;
  if (!patient) return <div className="p-8 text-center text-gray-500">Patient not found</div>;

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/patients')}
          className="flex items-center gap-1.5 text-[13px] text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft size={15} />
          Back to Patients
        </button>

        {isAdmin && (
          <button
            onClick={() => setIsDeleteModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-bold text-red-500 hover:bg-red-50 rounded-lg transition-colors uppercase tracking-widest border border-red-100"
          >
            <Trash2 size={14} />
            Delete Patient
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Patient Profile Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm animate-slide-up">
          <div className="flex flex-col items-center text-center">
            <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center border-4 border-white shadow-sm mb-4">
              <User size={32} className="text-gray-400" />
            </div>
            <h1 className="text-xl font-bold text-gray-900">{patient.full_name || patient.username}</h1>
            <p className="text-[13px] text-gray-500 mt-1">{patient.email || 'No email provided'}</p>
          </div>

          <div className="mt-8 space-y-4 pt-6 border-t border-gray-50">
            <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">General Information</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-[13px]">
                <Mail size={16} className="text-gray-400" />
                <span className="text-gray-600">{patient.email || 'N/A'}</span>
              </div>
              <div className="flex items-center gap-3 text-[13px]">
                <Calendar size={16} className="text-gray-400" />
                <span className="text-gray-600">Patient ID: #{patient.id}</span>
              </div>
              <div className="flex items-center gap-3 text-[13px]">
                <Activity size={16} className="text-gray-400" />
                <span className="text-gray-600">{scans.length} Scans recorded</span>
              </div>
            </div>
          </div>
        </div>

        {/* Scan History List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <h2 className="text-[14px] font-bold mb-4 uppercase tracking-wider text-gray-400">Scan History</h2>

            {scans.length > 0 ? (
              <div className="space-y-3">
                {scans.map((scan) => (
                  <Link
                    key={scan.id}
                    to={`/predictions/${scan.id}`}
                    className="flex items-center justify-between p-4 bg-gray-50/50 rounded-xl border border-gray-100 hover:border-gray-300 hover:bg-white transition-all group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-white rounded-lg border border-gray-100 flex items-center justify-center shadow-sm">
                        <Activity size={18} className="text-gray-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[14px] font-bold text-gray-900">Scan #{scan.id}</span>
                          <ProcessStatusBadge status={scan.status} />
                        </div>
                        <p className="text-[12px] text-gray-500 mt-0.5">
                          {new Date(scan.created_at).toLocaleDateString()} at {new Date(scan.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      {scan.status === 'COMPLETED' && (
                        <div className="hidden sm:flex flex-col items-end">
                          <TumorBadge label={scan.prediction_class!} />
                          <span className="text-[11px] font-medium text-gray-400 mt-1">{(scan.confidence! * 100).toFixed(0)}% Conf.</span>
                        </div>
                      )}
                      <span className="text-gray-300 group-hover:text-gray-900 transition-colors">→</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-gray-400 border-2 border-dashed border-gray-50 rounded-xl">
                <p className="text-[13px]">No scan history found for this patient.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <ConfirmDeleteModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={async () => {
          try {
            await predictionService.deleteUser(patient.id);
            navigate('/patients');
          } catch (err) {
            console.error('Failed to delete patient:', err);
            alert('Failed to delete patient. Ensure you are not deleting your own account.');
          }
        }}
        title="Delete Patient Account"
        message="Are you sure you want to delete the account for"
        itemName={patient.full_name || patient.username}
      />
    </div>
  );
}
