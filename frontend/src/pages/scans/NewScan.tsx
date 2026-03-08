import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { predictionService } from '../../services/api';
import { ArrowLeft, Upload, Brain, ArrowRight, AlertTriangle, Shield, Info } from 'lucide-react';
import { TumorBadge } from '../../components/ui/Badge';
import { useAuth } from '../../hooks/useAuth';

// ============================================
// New Scan Page
// ============================================

const PROB_COLORS: Record<string, string> = {
  glioma: '#111111',
  meningioma: '#525252',
  notumor: '#A3A3A3',
  pituitary: '#D4D4D4',
};

const inputClass =
  'w-full px-3.5 py-2.5 text-sm border border-gray-300 rounded-lg bg-white ' +
  'text-gray-900 placeholder:text-gray-400 ' +
  'focus:outline-none focus:border-gray-900 transition-colors';

const labelClass = 'block text-[12px] font-semibold text-gray-500 mb-1.5 uppercase tracking-widest';

export default function NewScan() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null);

  const isPatient = user?.role === 'patient';

  const [formData, setFormData] = useState({
    scanType: 'MRI',
    notes: '',
    file: null as File | null,
    preview: null as string | null,
  });

  // Load patients for doctor/admin
  useEffect(() => {
    if (user?.role === 'admin' || user?.role === 'doctor') {
      predictionService.getPatients().then(setPatients).catch(console.error);
    }
  }, [user?.role]);

  // Auto-select current user if patient
  useEffect(() => {
    if (isPatient && user?.id) {
      setSelectedPatientId(user.id);
    }
  }, [isPatient, user?.id]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFormData({ ...formData, file, preview: URL.createObjectURL(file) });
      setError('');
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setFormData({ ...formData, file, preview: URL.createObjectURL(file) });
      setError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const patientId = selectedPatientId || user?.id;
    if (!patientId || !formData.file) {
      setError('Please select a patient and upload a scan image.');
      return;
    }
    setUploading(true);
    setError('');
    setResult(null);
    try {
      const initResult = await predictionService.predict(
        patientId,
        formData.file,
        formData.scanType,
        formData.notes || undefined
      );

      if (initResult.status === 'PENDING') {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const wsUrl = apiUrl.replace(/^http/, 'ws') + `/api/ws/scans/${initResult.id}`;

        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            if (data.status === 'FAILED') {
              setError(data.error || 'Failed to process image');
              setResult(null);
            } else {
              setResult({ ...initResult, ...data });
            }
            setUploading(false);
            ws.close();
          }
        };

        ws.onerror = (err) => {
          console.error("WebSocket error:", err);
          setError('Lost connection to processing server. Please refresh and check scan history.');
          setUploading(false);
          ws.close();
        };

      } else {
        setResult(initResult);
        setUploading(false);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process image. Please try again.');
      setUploading(false);
    }
  };

  const showResult = result !== null;
  const probabilities = result?.probabilities ? JSON.parse(result.probabilities) : null;
  const confidencePct = result?.confidence ? Math.round(result.confidence * 100) : 0;
  const uncertaintyPct = result?.uncertainty ? (result.uncertainty * 100).toFixed(1) : null;

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in">
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-1.5 text-[13px] text-gray-500 hover:text-gray-900 transition-colors"
      >
        <ArrowLeft size={15} />
        Dashboard
      </button>

      <div>
        <h1 className="text-xl font-semibold text-gray-900 tracking-tight">New Brain Scan</h1>
        <p className="text-[13px] text-gray-500 mt-0.5">Upload an MRI scan for AI analysis.</p>
      </div>

      {/* Disclaimer before upload */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 flex items-center gap-3 animate-slide-up">
        <AlertTriangle size={14} className="text-amber-600 shrink-0" />
        <p className="text-[11px] text-amber-800 leading-tight">
          <span className="font-bold">Research Prototype:</span> This output is NOT a clinical diagnosis.
          Consult healthcare professionals for medical decisions.
        </p>
      </div>

      {error && (
        <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg animate-fade-in text-[13px] text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Form */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm animate-slide-up" style={{ animationDelay: '0.05s' }}>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="p-3 bg-gray-50/50 rounded-lg text-sm border border-gray-100">
              <span className="text-gray-500 text-[12px] font-bold uppercase tracking-widest block mb-1">Patient Profile</span>
              {isPatient ? (
                <span className="font-bold text-gray-900">{user?.full_name || user?.username}</span>
              ) : (
                <select
                  value={selectedPatientId || ''}
                  onChange={(e) => setSelectedPatientId(Number(e.target.value))}
                  className="w-full mt-1 bg-white border border-gray-200 rounded-lg px-2 py-1.5 text-[13px] focus:outline-none focus:border-gray-900"
                  required
                >
                  <option value="">Select patient...</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.full_name || p.username} (ID: #{p.id})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className={labelClass}>Clinical Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
                className={inputClass}
                placeholder="Observed symptoms, medical history..."
              />
            </div>

            <div>
              <label className={labelClass}>MRI Scan Image *</label>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                className="block cursor-pointer border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-gray-900 transition-colors bg-gray-50/20"
              >
                {formData.preview ? (
                  <div>
                    <img src={formData.preview} alt="Preview" className="max-h-48 mx-auto rounded-lg shadow-sm" />
                    <p className="mt-3 text-[11px] font-bold text-gray-400 uppercase tracking-widest">Click to replace</p>
                  </div>
                ) : (
                  <div>
                    <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center border border-gray-100 mx-auto mb-3 shadow-sm">
                      <Upload size={20} className="text-gray-400" />
                    </div>
                    <p className="text-sm font-semibold text-gray-700">Drop MRI image here</p>
                    <p className="text-[11px] text-gray-400 mt-1">PNG, JPG up to 10MB</p>
                  </div>
                )}
              </label>
            </div>

            <button
              type="submit"
              disabled={uploading}
              className="w-full py-2.5 px-4 bg-gray-900 text-white rounded-lg text-sm font-bold uppercase tracking-widest hover:bg-black disabled:opacity-50 flex items-center justify-center gap-2 transition-all shadow-sm"
            >
              {uploading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Brain size={15} />
                  Run A.I. Classification
                </>
              )}
            </button>
          </form>
        </div>

        {/* Result */}
        {showResult && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm animate-scale-in">
            <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-4">A.I. Prediction</h3>

            {/* Human Review Alert */}
            {result.requires_human_review && (
              <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
                <Shield size={16} className="text-red-600 shrink-0 mt-0.5" />
                <p className="text-[12px] text-red-700 leading-tight">
                  <span className="font-bold">Human Review Required:</span> This scan triggered a low confidence or high uncertainty flag.
                </p>
              </div>
            )}

            <div className="flex items-center gap-3 mb-6">
              <TumorBadge label={result.prediction_class} />
              <span className="text-3xl font-bold text-gray-900">
                {confidencePct}%
              </span>
            </div>

            {/* Uncertainty */}
            {uncertaintyPct && (
              <div className="flex items-center gap-2 mb-6 px-3 py-2 bg-gray-50/50 rounded-lg border border-gray-100">
                <Info size={14} className="text-gray-400" />
                <span className="text-[12px] text-gray-500">
                  Uncertainty Score: <span className="font-bold text-gray-900">{uncertaintyPct}%</span>
                </span>
                <span className="text-[9px] text-gray-300 font-bold ml-auto uppercase tracking-tighter">MC Dropout</span>
              </div>
            )}

            {probabilities && (
              <div className="space-y-4 mb-6">
                {Object.entries(probabilities).map(([label, prob]) => (
                  <div key={label}>
                    <div className="flex justify-between text-[11px] mb-1.5 uppercase font-bold tracking-tight">
                      <span className="text-gray-400">{label}</span>
                      <span className="text-gray-900">{((prob as number) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-1000"
                        style={{ width: `${(prob as number) * 100}%`, backgroundColor: PROB_COLORS[label] || '#737373' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => navigate(`/predictions/${result.id}`)}
              className="w-full py-2.5 bg-gray-50 text-gray-900 rounded-lg text-[13px] font-bold border border-gray-200 hover:bg-white hover:border-gray-900 transition-all flex items-center justify-center gap-2"
            >
              Detailed Report <ArrowRight size={14} />
            </button>
          </div>
        )}

        {/* Grad-CAM */}
        {showResult && result.gradcam_image && (
          <div className="bg-[#0A0A0A] rounded-xl border border-gray-800 p-2 shadow-inner animate-scale-in" style={{ animationDelay: '0.1s' }}>
            <p className="text-[9px] text-gray-500 mb-1.5 uppercase tracking-widest font-bold ml-1">Visualization: A.I. Attention</p>
            <img src={result.gradcam_image} alt="Grad-CAM" className="w-full rounded-lg aspect-square object-cover" />
            <p className="text-[10px] text-gray-500 mt-2 px-2 pb-1 text-center italic">
              Heatmap indicates image regions most significant to A.I. classification.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
