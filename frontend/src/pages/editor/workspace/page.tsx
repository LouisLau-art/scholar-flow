import React, { useEffect, useState } from 'react';
import { editorService } from '../../../services/editorService';

interface Manuscript {
  id: string;
  title: string;
  pre_check_status: string;
}

export default function AEWorkspacePage() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchWorkspace = async () => {
    setLoading(true);
    try {
      const data = await editorService.getAEWorkspace();
      setManuscripts(data as unknown as Manuscript[]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspace();
  }, []);

  const handleSubmitCheck = async (id: string) => {
    if (!confirm("Confirm technical check pass?")) return;
    try {
      await editorService.submitTechnicalCheck(id);
      fetchWorkspace();
    } catch (error) {
      alert("Failed to submit check");
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Assistant Editor Workspace</h1>
      
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
                 <tr><td colSpan={3} className="px-6 py-4 text-center text-gray-500">No manuscripts assigned.</td></tr>
              ) : (
                manuscripts.map(m => (
                  <tr key={m.id}>
                    <td className="px-6 py-4 whitespace-nowrap">{m.title}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{m.pre_check_status}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button 
                        onClick={() => handleSubmitCheck(m.id)}
                        className="text-green-600 hover:text-green-900"
                      >
                        Submit Check (Pass)
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
