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
  const [activeId, setActiveId] = useState<string | null>(null);
  const [decision, setDecision] = useState<'pass' | 'revision'>('pass');
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');

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
    setError('');
    try {
      if (decision === 'revision' && !comment.trim()) {
        setError('Comment is required for revision.');
        return;
      }
      await editorService.submitTechnicalCheck(id, { decision, comment: comment.trim() || undefined });
      setActiveId(null);
      setDecision('pass');
      setComment('');
      fetchWorkspace();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit check');
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
                      {activeId === m.id ? (
                        <div className="space-y-2 min-w-[280px]">
                          <select
                            className="w-full border rounded p-1 text-sm"
                            value={decision}
                            onChange={(e) => setDecision(e.target.value as 'pass' | 'revision')}
                          >
                            <option value="pass">Pass to Academic</option>
                            <option value="revision">Request Revision</option>
                          </select>
                          <textarea
                            className="w-full border rounded p-1 text-sm min-h-[70px]"
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            placeholder={decision === 'revision' ? 'Comment is required for revision...' : 'Optional comment...'}
                          />
                          {error ? <div className="text-xs text-red-600">{error}</div> : null}
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleSubmitCheck(m.id)}
                              className="text-green-600 hover:text-green-900 text-sm"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => {
                                setActiveId(null);
                                setDecision('pass');
                                setComment('');
                                setError('');
                              }}
                              className="text-gray-500 hover:text-gray-700 text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button 
                          onClick={() => {
                            setActiveId(m.id);
                            setDecision('pass');
                            setComment('');
                            setError('');
                          }}
                          className="text-green-600 hover:text-green-900"
                        >
                          Submit Check
                        </button>
                      )}
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
