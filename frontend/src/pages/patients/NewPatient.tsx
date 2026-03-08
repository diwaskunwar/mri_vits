import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function NewPatient() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/patients')}
        className="flex items-center gap-1.5 text-[13px] text-gray-500 hover:text-gray-900"
      >
        <ArrowLeft size={15} />
        Back to Patients
      </button>

      <h1 className="text-xl font-semibold">Add Patient</h1>
      <p className="text-gray-500">
        Patients are added through invitations. Go to Invitations to create an invitation link.
      </p>
    </div>
  );
}
