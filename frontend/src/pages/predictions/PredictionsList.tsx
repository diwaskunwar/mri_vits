import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { predictionService } from '../../services/api';
import { PageLoader } from '../../components/ui/Spinner';
import { TumorBadge, ConfidenceBadge, ProcessStatusBadge } from '../../components/ui/Badge';
import { useAuth } from '../../hooks/useAuth';
import { Search, Trash2 } from 'lucide-react';
import { ConfirmDeleteModal } from '../../components/ui/ConfirmDeleteModal';

export default function PredictionsList() {
  const { isAdmin, isPatient } = useAuth();
  const [scans, setScans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; id: number; scanId: string }>({
    isOpen: false,
    id: 0,
    scanId: '',
  });

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 12;

  useEffect(() => { loadScans(); }, []);

  const loadScans = async () => {
    try {
      const data = await predictionService.getAll();
      setScans(data);
    } catch (err) {
      console.error('Failed to load scans:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteScan = async (id: number) => {
    try {
      await predictionService.deleteScan(id);
      loadScans();
    } catch (err) {
      console.error('Failed to delete scan:', err);
      alert('Failed to delete scan.');
    }
  };

  if (loading) return <PageLoader />;

  const filteredScans = scans.filter(scan => !searchTerm || scan.prediction_class?.toLowerCase().includes(searchTerm.toLowerCase()));
  const totalPages = Math.max(1, Math.ceil(filteredScans.length / itemsPerPage));
  const currentScans = filteredScans.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">

      {/* TOP: Header & Filter */}
      <div className="flex-none p-6 space-y-4 border-b border-gray-100 bg-white z-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 tracking-tight">
              {isPatient ? 'My Scans' : 'All Scans'}
            </h1>
            <p className="text-[13px] text-gray-500 mt-0.5">
              {isPatient ? 'View your brain scan predictions' : 'Manage and review patient scans'}
            </p>
          </div>
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <input
            type="text"
            placeholder="Search scans by prediction..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900 transition-shadow"
          />
        </div>
      </div>

      {/* MIDDLE: Scrollable Grid Content */}
      <div className="flex-1 overflow-y-auto p-6 bg-gray-50/30">
        {currentScans.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {currentScans.map((scan, index) => (
              <div key={scan.id} className="relative group">
                <Link
                  to={`/predictions/${scan.id}`}
                  className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-gray-900 hover:shadow-md transition-all duration-300 animate-slide-up"
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex flex-col gap-1">
                      {scan.status === 'COMPLETED' ? (
                        <TumorBadge label={scan.prediction_class || 'N/A'} />
                      ) : (
                        <ProcessStatusBadge status={scan.status} />
                      )}
                      <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mt-1">
                        Status: {scan.status}
                      </span>
                    </div>
                    {scan.status === 'COMPLETED' && scan.confidence !== undefined && (
                      <ConfidenceBadge confidence={scan.confidence} />
                    )}
                  </div>

                  <div className="space-y-3 text-[13px]">
                    <div className="flex justify-between items-center py-1.5 border-b border-gray-50">
                      <span className="text-gray-500">Scan ID</span>
                      <span className="text-gray-900 font-bold">#{scan.id}</span>
                    </div>
                    <div className="flex justify-between items-center py-1.5 border-b border-gray-50">
                      <span className="text-gray-500">Date</span>
                      <span className="text-gray-900 font-medium">
                        {new Date(scan.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {!isPatient && scan.user && (
                      <div className="flex justify-between items-center py-1.5 border-b border-gray-50 truncate gap-2">
                        <span className="text-gray-500">Patient</span>
                        <span className="text-gray-900 font-semibold truncate text-right">{scan.user.full_name || scan.user.username}</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center py-1.5 border-b border-gray-50">
                      <span className="text-gray-500">Latency (Q/P)</span>
                      <span className="text-gray-900 font-medium">
                        {scan.queue_time_ms ? `${scan.queue_time_ms.toFixed(0)}ms` : '---'} / {scan.process_time_ms ? `${scan.process_time_ms.toFixed(0)}ms` : '---'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-1.5">
                      <span className="text-gray-500">Review</span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-tighter ${scan.is_reviewed ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}>
                        {scan.is_reviewed ? 'Reviewed' : 'Pending'}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 flex items-center justify-end border-t border-gray-50">
                    <span className="text-[11px] font-bold text-gray-400 group-hover:text-gray-900 transition-colors uppercase tracking-widest flex items-center gap-1">
                      View Details
                      <span className="transition-transform group-hover:translate-x-1">→</span>
                    </span>
                  </div>
                </Link>

                {isAdmin && (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setDeleteModal({ isOpen: true, id: scan.id, scanId: scan.id.toString() });
                    }}
                    className="absolute bottom-3 left-4 p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100 z-20"
                    title="Delete Scan"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="h-full flex flex-col justify-center items-center text-center py-12">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <Search className="text-gray-400" size={20} />
            </div>
            <p className="text-[14px] font-medium text-gray-900">No scans found</p>
            <p className="text-[13px] text-gray-500 mt-1">Try adjusting your search query.</p>
          </div>
        )}
      </div>

      {/* BOTTOM: Fixed Pagination */}
      <div className="flex-none flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-white">
        <span className="text-[13px] text-gray-500">
          Showing <span className="font-medium text-gray-900">{filteredScans.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1}</span> to <span className="font-medium text-gray-900">{Math.min(currentPage * itemsPerPage, filteredScans.length)}</span> of <span className="font-medium text-gray-900">{filteredScans.length}</span> results
        </span>
        <div className="flex gap-2">
          <button
            disabled={currentPage === 1}
            onClick={(e) => { e.preventDefault(); setCurrentPage(c => c - 1); }}
            className="px-3 py-1.5 text-[13px] font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <button
            disabled={currentPage === totalPages}
            onClick={(e) => { e.preventDefault(); setCurrentPage(c => c + 1); }}
            className="px-3 py-1.5 text-[13px] font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>

      <ConfirmDeleteModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ ...deleteModal, isOpen: false })}
        onConfirm={() => handleDeleteScan(deleteModal.id)}
        title="Permanently Delete Scan"
        message="Are you sure you want to delete scan record"
        itemName={`#${deleteModal.scanId}`}
      />
    </div>
  );
}
