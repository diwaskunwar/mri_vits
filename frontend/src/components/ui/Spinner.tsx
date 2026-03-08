// ============================================
// Spinner — monochrome loading indicator
// ============================================

interface SpinnerProps {
  size?: number;
  className?: string;
}

export function Spinner({ size = 24, className = '' }: SpinnerProps) {
  return (
    <div
      className={`rounded-full border-2 border-gray-200 border-t-gray-900 animate-spin ${className}`}
      style={{ width: size, height: size, flexShrink: 0 }}
    />
  );
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <Spinner size={28} />
    </div>
  );
}
