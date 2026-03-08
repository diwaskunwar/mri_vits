import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { predictionService } from '../../services/api';
import type { Statistics } from '../../types';
import { PageLoader } from '../../components/ui/Spinner';
import { TumorBadge, ConfidenceBadge, ProcessStatusBadge } from '../../components/ui/Badge';
import { useAuth } from '../../hooks/useAuth';
import {
  Users,
  ImageIcon,
  CheckCircle2,
  Clock,
  Plus
} from 'lucide-react';
import { Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js';

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
);

// ============================================
// Design tokens — B&W chart palette
// ============================================

const CHART_COLORS: Record<string, string> = {
  glioma: '#111111',
  meningioma: '#525252',
  notumor: '#A3A3A3',
  pituitary: '#D4D4D4',
};

const getLabelColor = (label: string) => CHART_COLORS[label] || '#737373';

// ============================================
// Dashboard Page
// ============================================

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const { user, isPatient } = useAuth();

  useEffect(() => { loadStats(); }, [user]);

  const loadStats = async () => {
    try {
      const data = await predictionService.getStatistics();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <PageLoader />;
  if (!stats) return <div className="p-8 text-center text-gray-500">Failed to load statistics.</div>;

  const labelChartData = {
    labels: Object.keys(stats.predictions_by_label || {}),
    datasets: [{
      data: Object.values(stats.predictions_by_label || {}),
      backgroundColor: Object.keys(stats.predictions_by_label || {}).map(getLabelColor),
      borderWidth: 0,
    }],
  };

  const reviewChartData = {
    labels: ['Reviewed', 'Pending'],
    datasets: [{
      data: [stats.predictions_reviewed || 0, stats.predictions_pending_review || 0],
      backgroundColor: ['#111111', '#D4D4D4'],
      borderWidth: 0,
    }],
  };

  const getStatCards = () => {
    if (isPatient) {
      return [
        { label: 'Total Scans', value: stats.total_scans, icon: ImageIcon, delay: 0 },
        { label: 'Doctor Reviewed', value: stats.predictions_reviewed, icon: CheckCircle2, delay: 0.05 },
        { label: 'Awaiting Review', value: stats.predictions_pending_review, icon: Clock, delay: 0.1 },
        { label: 'Avg A.I. Speed', value: `${stats.avg_process_time_ms?.toFixed(0) || 0}ms`, icon: CheckCircle2, delay: 0.15 },
        { label: 'Avg System Wait', value: `${stats.avg_queue_time_ms?.toFixed(0) || 0}ms`, icon: Clock, delay: 0.2 },
      ];
    }
    return [
      { label: 'Total Patients', value: stats.total_patients, icon: Users, delay: 0 },
      { label: 'Total Scans', value: stats.total_scans, icon: ImageIcon, delay: 0.06 },
      { label: 'Pending Review', value: stats.predictions_pending_review, icon: Clock, delay: 0.12 },
      { label: 'Avg Process', value: `${stats.avg_process_time_ms?.toFixed(0) || 0}ms`, icon: CheckCircle2, delay: 0.18 },
      { label: 'Avg Queue', value: `${stats.avg_queue_time_ms?.toFixed(0) || 0}ms`, icon: Clock, delay: 0.24 },
    ];
  };

  const statCards = getStatCards();

  const { title, subtitle } = (() => {
    if (isPatient) return { title: 'My Health Dashboard', subtitle: 'View your scan results and predictions.' };
    return { title: 'Health Performance Dashboard', subtitle: 'Overview of patient data and medical performance.' };
  })();

  return (
    <div className="space-y-7 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 tracking-tight">{title}</h1>
          <p className="text-[13px] text-gray-500 mt-0.5">{subtitle}</p>
        </div>
        {!isPatient && (
          <div className="flex gap-3">
            <Link
              to="/patients"
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-900 rounded-lg transition-all text-[13px] font-medium hover:border-gray-900 shadow-sm"
            >
              <Users size={14} />
              Manage Patients
            </Link>
            <Link
              to="/scans/new"
              className="flex items-center gap-2 px-4 py-2 bg-[#0A0A0A] hover:bg-black text-white rounded-lg transition-colors text-[13px] font-medium shadow-sm"
            >
              <Plus size={14} />
              New Scan
            </Link>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {statCards.map(({ label, value, icon: Icon, delay }) => (
          <div
            key={label}
            className="bg-white rounded-xl border border-gray-200 p-5 animate-slide-up shadow-sm hover:shadow-md transition-shadow"
            style={{ animationDelay: `${delay}s` }}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest">{label}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2 tabular-nums">{value}</p>
              </div>
              <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                <Icon size={16} className="text-gray-500" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-gray-200 p-6 animate-slide-up shadow-sm" style={{ animationDelay: '0.2s' }}>
          <h2 className="text-[13px] font-bold text-gray-900 uppercase tracking-widest mb-5">
            {isPatient ? 'My Result Distribution' : 'Review Status Distribution'}
          </h2>
          <div className="h-[220px] flex items-center justify-center">
            <Pie
              data={reviewChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'right' as const, labels: { boxWidth: 12, font: { size: 11, family: 'Inter' }, padding: 15 } },
                  tooltip: { cornerRadius: 8, padding: 10 }
                }
              }}
            />
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6 animate-slide-up shadow-sm" style={{ animationDelay: '0.25s' }}>
          <h2 className="text-[13px] font-bold text-gray-900 uppercase tracking-widest mb-5">
            {isPatient ? 'My Diagnoses Summary' : 'Predictions by Label'}
          </h2>
          <div className="h-[220px] flex items-center justify-center">
            <Pie
              data={labelChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: 'right' as const, labels: { boxWidth: 12, font: { size: 11, family: 'Inter' }, padding: 15 } },
                  tooltip: { cornerRadius: 8, padding: 10 }
                }
              }}
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm animate-slide-up" style={{ animationDelay: '0.3s' }}>
        <div className="px-6 py-5 border-b border-gray-50 flex items-center justify-between bg-white">
          <h2 className="text-[13px] font-bold text-gray-900 uppercase tracking-widest">
            {isPatient ? 'My Recent Results' : 'Recent Case Flow'}
          </h2>
          {!isPatient && (
            <Link to="/predictions" className="text-[11px] font-bold text-gray-400 hover:text-gray-900 transition-colors uppercase tracking-widest flex items-center gap-1.5 group">
              View All Scans
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
          )}
        </div>

        {stats.recent_predictions && stats.recent_predictions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/30">
                  <th className="text-left py-3 px-6 text-[11px] font-semibold text-gray-400 uppercase tracking-widest">
                    {isPatient ? 'Scan Date' : 'Patient'}
                  </th>
                  <th className="text-left py-3 px-4 text-[11px] font-semibold text-gray-400 uppercase tracking-widest">A.I. Prediction</th>
                  <th className="text-left py-3 px-4 text-[11px] font-semibold text-gray-400 uppercase tracking-widest">Confidence</th>
                  <th className="text-left py-3 px-4 text-[11px] font-semibold text-gray-400 uppercase tracking-widest">Efficiency</th>
                  {!isPatient && <th className="text-left py-3 px-4 text-[11px] font-semibold text-gray-400 uppercase tracking-widest">Date</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {stats.recent_predictions.map((pred) => (
                  <tr
                    key={pred.id}
                    className="hover:bg-gray-50/80 transition-colors cursor-pointer group"
                    onClick={() => navigate(`/predictions/${pred.id}`)}
                  >
                    <td className="py-4 px-6">
                      {isPatient ? (
                        <span className="text-[13px] font-medium text-gray-900 group-hover:underline">{new Date(pred.created_at).toLocaleDateString()}</span>
                      ) : (
                        <Link to={`/patients/${pred.user_id}`}
                          className="text-[13px] font-bold text-gray-900 hover:underline hover:text-black"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {pred.user?.full_name || pred.user?.username || `Patient #${pred.user_id}`}
                        </Link>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex flex-col gap-1.5">
                        <div className="flex items-center gap-2">
                          {pred.status === 'COMPLETED' ? <TumorBadge label={pred.prediction_class || 'N/A'} /> : <ProcessStatusBadge status={pred.status} />}
                          {pred.status === 'COMPLETED' && (
                            <span className="px-1.5 py-0.5 rounded bg-green-50 text-[9px] font-bold text-green-700 uppercase tracking-tighter">Done</span>
                          )}
                        </div>
                        <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">System: {pred.status}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      {pred.status === 'COMPLETED' ? <ConfidenceBadge confidence={pred.confidence || 0} /> : <span className="text-[12px] text-gray-400">---</span>}
                    </td>
                    <td className="py-4 px-4">
                      {pred.status === 'COMPLETED' && pred.process_time_ms ? (
                        <div className="flex flex-col text-[11px] text-gray-500">
                          <div className="flex items-center gap-1.5">
                            <span className="w-1 h-1 rounded-full bg-green-500"></span>
                            <span className="font-medium text-gray-700">{pred.process_time_ms.toFixed(0)}ms</span>
                          </div>
                          {pred.queue_time_ms && <span className="text-[10px] text-gray-400 mt-0.5 ml-2.5">Wait: {pred.queue_time_ms.toFixed(0)}ms</span>}
                        </div>
                      ) : <span className="text-[12px] text-gray-400">---</span>}
                    </td>
                    {!isPatient && <td className="py-4 px-4 text-[12px] text-gray-500 tabular-nums">{new Date(pred.created_at).toLocaleDateString()}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-[13px] text-gray-400">
            {isPatient ? "No scans yet." : "No predictions yet."}
          </div>
        )}
      </div>
    </div>
  );
}
