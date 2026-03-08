import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { predictionService } from '../../services/api';
import { PageLoader } from '../../components/ui/Spinner';
import { TumorBadge, ProcessStatusBadge } from '../../components/ui/Badge';
import { useAuth } from '../../hooks/useAuth';
import { ArrowLeft, Check, Clock, AlertTriangle, Shield, Info, Trash2 } from 'lucide-react';

const PROB_COLORS: Record<string, string> = {
  glioma: '#111111',
  meningioma: '#525252',
  notumor: '#A3A3A3',
  pituitary: '#D4D4D4',
};

export default function PredictionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAdmin, isStaff } = useAuth();
  const [scan, setScan] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');

  useEffect(() => { loadScan(); }, [id]);

  const loadScan = async () => {
    if (!id) return;
    try {
      const data = await predictionService.getById(parseInt(id));
      setScan(data);
    } catch (err) {
      console.error('Failed to load scan:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async () => {
    if (!id) return;
    setReviewing(true);
    try {
      await predictionService.review(parseInt(id), reviewNotes);
      loadScan();
    } catch (err) {
      console.error('Failed to review:', err);
    } finally {
      setReviewing(false);
    }
  };

  if (loading) return <PageLoader />;
  if (!scan) return <div>Scan not found</div>;

  const probabilities = scan.probabilities ? JSON.parse(scan.probabilities) : null;
  const confidencePct = scan.confidence ? Math.round(scan.confidence * 100) : 0;
  const uncertaintyPct = scan.uncertainty ? (scan.uncertainty * 100).toFixed(1) : null;

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/predictions')}
          className="flex items-center gap-1.5 text-[13px] text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft size={15} />
          Back to Scans
        </button>

        {isAdmin && (
          <button
            onClick={async () => {
              if (window.confirm('Are you sure you want to delete this scan? This action cannot be undone.')) {
                try {
                  await predictionService.deleteScan(scan.id);
                  navigate('/predictions');
                } catch (err) {
                  console.error('Failed to delete scan:', err);
                  alert('Failed to delete scan.');
                }
              }
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-bold text-red-500 hover:bg-red-50 rounded-lg transition-colors uppercase tracking-widest border border-red-100"
          >
            <Trash2 size={14} />
            Delete Scan
          </button>
        )}
      </div>

      {/* ⚠️ Disclaimer Banner - Compact */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 flex items-center gap-3">
        <AlertTriangle size={14} className="text-amber-600 shrink-0" />
        <p className="text-[11px] text-amber-800 leading-tight">
          <span className="font-bold">Research Prototype:</span> This output is NOT a clinical diagnosis.
          Consult healthcare professionals for medical decisions.
        </p>
      </div>

      {/* 🔴 Human Review Alert */}
      {scan.requires_human_review && !scan.is_reviewed && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <Shield size={18} className="text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-[13px] font-semibold text-red-800">
              Requires Human Review
            </p>
            <p className="text-[12px] text-red-700 mt-0.5">
              This prediction has low confidence or high uncertainty.
              It must be reviewed by an authorized healthcare professional before any clinical action.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Column 1: Scan Info & Metadata & Review */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-[14px] font-bold mb-3 uppercase tracking-wider text-gray-400">Scan Details</h2>
            <div className="space-y-2.5 text-[13px]">
              <div className="flex justify-between">
                <span className="text-gray-500">ID</span>
                <span className="text-gray-900 font-medium">#{scan.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Date</span>
                <span className="text-gray-900 font-medium">
                  {new Date(scan.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">Queue Status</span>
                <ProcessStatusBadge status={scan.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Review Status</span>
                <span className={scan.is_reviewed ? 'text-green-600 font-medium' : 'text-amber-600 font-medium'}>
                  {scan.is_reviewed ? 'Reviewed' : 'Pending Review'}
                </span>
              </div>
              {scan.status === 'COMPLETED' && (
                <div className="pt-2 mt-2 border-t border-gray-50 space-y-2">
                  <div className="flex justify-between text-[12px]">
                    <span className="text-gray-400">Wait / Process</span>
                    <span className="text-gray-900">{scan.queue_time_ms?.toFixed(0)}ms / {scan.process_time_ms?.toFixed(0)}ms</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Inline Review Section */}
          {isStaff && !scan.is_reviewed && (
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <h3 className="text-[14px] font-bold mb-3 uppercase tracking-wider text-gray-400">Action</h3>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Clinical notes..."
                className="w-full p-2.5 border border-gray-200 rounded-lg text-[13px] mb-3 focus:border-gray-900 focus:outline-none min-h-[80px]"
              />
              <button
                onClick={handleReview}
                disabled={reviewing}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm hover:bg-black disabled:opacity-50 transition-colors"
              >
                {reviewing ? <Clock size={16} className="animate-spin" /> : <Check size={16} />}
                Sign Off
              </button>
            </div>
          )}

          {scan.is_reviewed && scan.review_notes && (
            <div className="bg-gray-50 rounded-xl border border-gray-100 p-4">
              <h3 className="text-[12px] font-bold text-gray-400 uppercase mb-2">Review Notes</h3>
              <p className="text-[13px] text-gray-700 leading-relaxed">{scan.review_notes}</p>
            </div>
          )}
        </div>

        {/* Column 2: Prediction Results */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-[14px] font-bold mb-4 uppercase tracking-wider text-gray-400">Prediction</h2>

          <div className="flex items-center gap-3 mb-5">
            <TumorBadge label={scan.prediction_class || 'N/A'} />
            <span className="text-3xl font-bold text-gray-900">
              {confidencePct}%
            </span>
          </div>

          {/* Uncertainty */}
          {uncertaintyPct && (
            <div className="flex items-center gap-2 mb-5 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
              <Info size={14} className="text-gray-400" />
              <span className="text-[12px] text-gray-500">
                Uncertainty: <span className="font-semibold text-gray-700">{uncertaintyPct}%</span>
              </span>
              <span className="text-[10px] text-gray-400 ml-auto uppercase font-medium">MC Dropout</span>
            </div>
          )}

          {probabilities && (
            <div className="space-y-4">
              {Object.entries(probabilities).map(([label, prob]) => (
                <div key={label}>
                  <div className="flex justify-between text-[12px] mb-1.5">
                    <span className="capitalize text-gray-500 font-medium">{label}</span>
                    <span className="font-bold text-gray-900">
                      {((prob as number) * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-1000"
                      style={{
                        width: `${(prob as number) * 100}%`,
                        backgroundColor: PROB_COLORS[label] || '#737373',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Column 3: Images */}
        <div className="space-y-4">
          {scan.input_image && (
            <div className="bg-[#0A0A0A] rounded-xl border border-gray-800 p-1.5 shadow-inner">
              <p className="text-[9px] text-gray-500 mb-1 uppercase tracking-widest font-bold ml-1">MRI Input</p>
              <img src={scan.input_image} alt="Input" className="w-full rounded-lg aspect-square object-cover" />
            </div>
          )}

          {scan.gradcam_image && (
            <div className="bg-[#0A0A0A] rounded-xl border border-gray-800 p-1.5 shadow-inner">
              <p className="text-[9px] text-gray-500 mb-1 uppercase tracking-widest font-bold ml-1">A.I. Attention</p>
              <img src={scan.gradcam_image} alt="Grad-CAM" className="w-full rounded-lg aspect-square object-cover" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
