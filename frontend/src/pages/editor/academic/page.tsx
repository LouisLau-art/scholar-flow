import React, { useEffect, useState } from 'react';
import { editorService } from '../../../services/editorService';
import { AcademicCheckModal } from '../../../components/AcademicCheckModal';

interface Manuscript {
  id: string;
  title: string;
  pre_check_status: string;
}

export default function EICAcademicQueuePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedManuscriptId, setSelectedManuscriptId] = useState<string | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const data = await editorService.getAcademicQueue();
      setManuscripts(data as unknown as Manuscript[]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const openDecisionModal = (id: string) => {
    setSelectedManuscriptId(id);
    setModalOpen(true);
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">EIC Academic Pre-check Queue</h1>
      
      {loading ? (
        <div>Loading...</div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {manuscripts.length === 0 ? (
                 <tr><td colSpan={3} className="px-6 py-4 text-center text-gray-500">No manuscripts awaiting academic check.</td></tr>
              ) : (
                manuscripts.map(m => (
                  <tr key={m.id}>
                    <td className="px-6 py-4 whitespace-nowrap">{m.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{m.pre_check_status}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button 
                        onClick={() => openDecisionModal(m.id)}
                        className="text-purple-600 hover:text-purple-900"
                      >
                        Make Decision
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {selectedManuscriptId && (
        <AcademicCheckModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          manuscriptId={selectedManuscriptId}
          onSuccess={fetchQueue}
        />
      )}
    </div>
  );
}
