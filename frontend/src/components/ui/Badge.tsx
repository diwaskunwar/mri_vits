// ============================================
// Badge — tumor type & status labels (B&W)
// ============================================

const TUMOR_STYLES: Record<string, string> = {
  glioma: 'bg-[#0A0A0A] text-white',
  meningioma: 'bg-[#404040] text-white',
  notumor: 'bg-gray-100 text-gray-800 border border-gray-300',
  pituitary: 'bg-gray-200 text-gray-800',
};

export function TumorBadge({ label }: { label: string }) {
  const style = TUMOR_STYLES[label?.toLowerCase()] ?? 'bg-gray-100 text-gray-700';
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide ${style}`}
    >
      {label || 'N/A'}
    </span>
  );
}

export function StatusBadge({ reviewed }: { reviewed: boolean }) {
  return reviewed ? (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-gray-900 text-white">
      <span className="w-1.5 h-1.5 rounded-full bg-white" />
      Reviewed
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-gray-100 text-gray-600 border border-gray-200">
      <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
      Pending
    </span>
  );
}

export function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const style =
    pct >= 80 ? 'bg-gray-900 text-white'
      : pct >= 50 ? 'bg-gray-400 text-white'
        : 'bg-gray-100 text-gray-600 border border-gray-200';
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold tabular-nums ${style}`}>
      {pct}%
    </span>
  );
}

export function ProcessStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    PENDING: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    PROCESSING: 'bg-blue-100 text-blue-800 border-blue-200',
    COMPLETED: 'bg-green-100 text-green-800 border-green-200',
    FAILED: 'bg-red-100 text-red-800 border-red-200',
  };
  const style = styles[status] || 'bg-gray-100 text-gray-800';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest border ${style}`}>
      {status}
    </span>
  );
}
