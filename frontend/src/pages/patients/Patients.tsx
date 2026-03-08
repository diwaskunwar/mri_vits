import { useState, useEffect } from 'react';
import { predictionService } from '../../services/api';
import type { User } from '../../types';
import { PageLoader } from '../../components/ui/Spinner';
import { Plus, Search, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ConfirmDeleteModal } from '../../components/ui/ConfirmDeleteModal';

export default function Patients() {
  const [patients, setPatients] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; id: number; name: string }>({
    isOpen: false,
    id: 0,
    name: '',
  });

  const { isAdmin } = useAuth();

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 12;

  useEffect(() => { loadPatients(); }, []);

  const loadPatients = async () => {
    try {
      const data = await predictionService.getPatients();
      setPatients(data);
    } catch (err) {
      console.error('Failed to load patients:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePatient = async (id: number) => {
    try {
      await predictionService.deleteUser(id);
      loadPatients();
    } catch (err) {
      console.error('Failed to delete patient:', err);
      alert('Failed to delete patient.');
    }
  };

  if (loading) return <PageLoader />;

  const filteredPatients = patients.filter(p => !searchTerm || p.username?.toLowerCase().includes(searchTerm.toLowerCase()));
  const totalPages = Math.max(1, Math.ceil(filteredPatients.length / itemsPerPage));
  const currentPatients = filteredPatients.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">

      {/* TOP: Header & Filter */}
      <div className="flex-none p-6 space-y-4 border-b border-gray-100 bg-white z-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 tracking-tight">Patients</h1>
            <p className="text-[13px] text-gray-500 mt-0.5">Manage patient accounts</p>
          </div>
          <Link
            to="/invitations/new"
            className="flex items-center gap-2 px-4 py-2 bg-[#0A0A0A] text-white rounded-lg text-[13px] font-medium hover:bg-black transition-colors"
          >
            <Plus size={16} />
            Invite Patient
          </Link>
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <input
            type="text"
            placeholder="Search patients by username..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1); // Reset page on search
            }}
            className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900 transition-shadow"
          />
        </div>
      </div>

      {/* MIDDLE: Scrollable Grid Content */}
      <div className="flex-1 overflow-y-auto p-6 bg-gray-50/30">
        {currentPatients.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {currentPatients.map((patient, index) => (
              <div key={patient.id} className="relative group">
                <Link
                  to={`/patients/${patient.id}`}
                  className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-gray-900 hover:shadow-md transition-all duration-300 animate-slide-up"
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center border border-gray-200 group-hover:bg-gray-900 group-hover:text-white transition-colors duration-300">
                      <span className="text-base font-bold">
                        {patient.full_name?.[0]?.toUpperCase() || patient.username?.[0]?.toUpperCase() || 'P'}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h3 className="font-bold text-[14px] text-gray-900 truncate pr-6">
                          {patient.full_name || patient.username}
                        </h3>
                        <span className="text-gray-300 group-hover:text-gray-900 transition-colors">→</span>
                      </div>
                      <p className="text-[12px] text-gray-500 mt-0.5 truncate">{patient.email}</p>
                      <div className="mt-3 pt-3 border-t border-gray-50 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">#{patient.id}</span>
                          <span className="text-[10px] text-gray-300 group-hover:text-gray-900 transition-colors">•</span>
                          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest transition-colors group-hover:text-gray-900">
                            {patient.total_scans || 0} Scans
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>

                {isAdmin && (
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setDeleteModal({ isOpen: true, id: patient.id, name: patient.full_name || patient.username });
                    }}
                    className="absolute bottom-4 right-4 p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100 z-20"
                    title="Delete Patient"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="h-full flex flex-col justify-center items-center text-center py-12 animate-fade-in">
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <Search className="text-gray-400" size={20} />
            </div>
            <p className="text-[14px] font-medium text-gray-900">No patients found</p>
            <p className="text-[13px] text-gray-500 mt-1">Try adjusting your search or invite a new patient.</p>
          </div>
        )}
      </div>

      {/* BOTTOM: Fixed Pagination */}
      <div className="flex-none flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-white">
        <span className="text-[13px] text-gray-500">
          Showing <span className="font-medium text-gray-900">{filteredPatients.length === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1}</span> to <span className="font-medium text-gray-900">{Math.min(currentPage * itemsPerPage, filteredPatients.length)}</span> of <span className="font-medium text-gray-900">{filteredPatients.length}</span> results
        </span>
        <div className="flex gap-2">
          <button
            disabled={currentPage === 1}
            onClick={() => setCurrentPage(c => c - 1)}
            className="px-3 py-1.5 text-[13px] font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <button
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage(c => c + 1)}
            className="px-3 py-1.5 text-[13px] font-medium text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>

      <ConfirmDeleteModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ ...deleteModal, isOpen: false })}
        onConfirm={() => handleDeletePatient(deleteModal.id)}
        title="Delete Patient Account"
        message="Are you sure you want to delete the account for"
        itemName={deleteModal.name}
      />
    </div>
  );
}
