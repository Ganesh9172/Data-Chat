import React, { useState, useEffect } from 'react';
import { X, UploadCloud, FileText, HelpCircle, Database, Trash2, CheckCircle2, RefreshCw } from 'lucide-react';
import { getKnowledgeBase, uploadKnowledgeDocument, addQAPair, deleteKnowledgeItem, revertKnowledgeUpdate } from '../services/api';

export default function KnowledgeModal({ isOpen, onClose, onKnowledgeUpdated, isAdmin = true }) {
  const canUpload = !!isAdmin;
  const canDeleteDoc = !!isAdmin;
  const canUpdateKnowledge = !!isAdmin;

  const [activeTab, setActiveTab] = useState(canUpload ? 'upload' : 'browser');
  const [knowledgeData, setKnowledgeData] = useState({ documents: [], qa_pairs: [], knowledge_updates: [], stats: {} });
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  // Q&A form state
  const [qaQuestion, setQaQuestion] = useState('');
  const [qaAnswer, setQaAnswer] = useState('');
  const [qaSource, setQaSource] = useState('Approved Technical Q&A');

  const loadData = async () => {
    try {
      const data = await getKnowledgeBase();
      setKnowledgeData(data);
    } catch (e) {
      console.error('Failed to load knowledge:', e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
      setStatusMessage(null);
      if (!canUpload && activeTab === 'upload') {
        setActiveTab('browser');
      } else if (!canUpdateKnowledge && activeTab === 'qa') {
        setActiveTab('browser');
      }
    }
  }, [isOpen, canUpload, canUpdateKnowledge]);

  if (!isOpen) return null;

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setStatusMessage(null);
    try {
      const res = await uploadKnowledgeDocument(file);
      setStatusMessage({
        type: 'success',
        text: `Indexed "${file.name}" with ${res.result?.chunk_count || 0} chunks! Immediately available to Firebird AI.`
      });
      await loadData();
      onKnowledgeUpdated?.();
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to upload document.' });
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleAddQA = async (e) => {
    e.preventDefault();
    if (!qaQuestion.trim() || !qaAnswer.trim()) return;

    setIsUploading(true);
    setStatusMessage(null);
    try {
      await addQAPair(qaQuestion.trim(), qaAnswer.trim(), qaSource.trim() || 'Approved Q&A');
      setStatusMessage({
        type: 'success',
        text: 'New approved Q&A embedded and added to Firebird AI knowledge base!'
      });
      setQaQuestion('');
      setQaAnswer('');
      await loadData();
      onKnowledgeUpdated?.();
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to add Q&A.' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete "${name}" from Firebird AI knowledge base?`)) return;
    try {
      await deleteKnowledgeItem(id);
      setStatusMessage({ type: 'success', text: `Removed "${name}" from knowledge base.` });
      await loadData();
      onKnowledgeUpdated?.();
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to delete item.' });
    }
  };

  const handleRevertUpdate = async (id, updateNum) => {
    if (!window.confirm(`Revert Knowledge Base Update #${updateNum}? Future answers will revert back to original PDF source text.`)) return;
    try {
      await revertKnowledgeUpdate(id);
      setStatusMessage({ type: 'success', text: `Reverted Knowledge Update #${updateNum}.` });
      await loadData();
      onKnowledgeUpdated?.();
    } catch (err) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to revert update.' });
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h3>
            <Database size={20} color="#f97316" />
            Firebird Knowledge Manager
          </h3>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div className="modal-tabs">
          {canUpload && (
            <button
              className={`modal-tab ${activeTab === 'upload' ? 'active' : ''}`}
              onClick={() => setActiveTab('upload')}
            >
              Upload Documents
            </button>
          )}
          {canUpdateKnowledge && (
            <button
              className={`modal-tab ${activeTab === 'qa' ? 'active' : ''}`}
              onClick={() => setActiveTab('qa')}
            >
              Add Approved Q&A
            </button>
          )}
          <button
            className={`modal-tab ${activeTab === 'browser' ? 'active' : ''}`}
            onClick={() => setActiveTab('browser')}
          >
            Indexed Knowledge ({knowledgeData.documents.length + knowledgeData.qa_pairs.length})
          </button>
        </div>

        {/* Status Notification */}
        {statusMessage && (
          <div
            style={{
              padding: '10px 24px',
              backgroundColor: statusMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              borderBottom: `1px solid ${statusMessage.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              color: statusMessage.type === 'success' ? '#34d399' : '#f87171',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}
          >
            <CheckCircle2 size={16} />
            {statusMessage.text}
          </div>
        )}

        {/* Modal Body */}
        <div className="modal-body">
          {activeTab === 'upload' && canUpload && (
            <div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: 16 }}>
                Upload PDF files, technical manuals, Standard Operating Procedures (SOP), or business documents.
                Firebird AI automatically extracts, chunks, generates vector embeddings, and stores them in JSON storage.
              </p>

              <label className="dropzone">
                <input
                  type="file"
                  accept=".pdf,.txt,.md,.csv,.json"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  style={{ display: 'none' }}
                />
                <div className="dropzone-icon">
                  <UploadCloud size={24} />
                </div>
                <div>
                  <h4 style={{ color: '#fff', fontSize: '1rem', marginBottom: 4 }}>
                    {isUploading ? 'Processing & Embedding Chunks...' : 'Click or Drop Document to Upload'}
                  </h4>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    Supported: PDF (page preserved), TXT, Markdown, CSV, JSON
                  </p>
                </div>
              </label>

              <div style={{ marginTop: 24, padding: 14, backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                <h5 style={{ fontSize: '0.82rem', color: 'var(--accent-fire-mid)', textTransform: 'uppercase', marginBottom: 6 }}>
                  ⚡ Zero-Restart Automatic Indexing
                </h5>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  As soon as processing completes, the centralized knowledge base is updated in real time. All authorized users can immediately ask questions about newly indexed documents.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'qa' && canUpdateKnowledge && (
            <form onSubmit={handleAddQA} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
                Add verified Q&A pairs directly into Firebird AI's knowledge base.
              </p>

              <div className="form-group">
                <label>Question</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g., What is the minimum static cold pressure for a two-storey dwelling?"
                  value={qaQuestion}
                  onChange={(e) => setQaQuestion(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Approved Answer</label>
                <textarea
                  className="form-textarea"
                  placeholder="e.g., Minimum 1.1 to 1.2 bar to provide 0.55 bar static head for 5.5m building height plus 0.5 bar positive overpressure margin."
                  value={qaAnswer}
                  onChange={(e) => setQaAnswer(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Source Reference</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g., 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1"
                  value={qaSource}
                  onChange={(e) => setQaSource(e.target.value)}
                />
              </div>

              <button type="submit" className="primary-btn" disabled={isUploading || !qaQuestion || !qaAnswer}>
                {isUploading ? 'Generating Embeddings...' : 'Add to Knowledge Base'}
              </button>
            </form>
          )}

          {activeTab === 'browser' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <h4 style={{ fontSize: '0.9rem', color: '#fff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FileText size={16} color="#f97316" />
                  Indexed Documents ({knowledgeData.documents.length})
                </h4>
                {knowledgeData.documents.length === 0 ? (
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>No documents indexed yet.</p>
                ) : (
                  <div className="knowledge-table-container">
                    <table className="knowledge-table">
                      <thead>
                        <tr>
                          <th>Document Name</th>
                          <th>Type</th>
                          <th>Chunks</th>
                          <th>Date</th>
                          {canDeleteDoc && <th>Action</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {knowledgeData.documents.map((doc) => (
                          <tr key={doc.id}>
                            <td style={{ color: '#fff', fontWeight: 500 }}>{doc.name}</td>
                            <td><span className="badge">{doc.file_type.toUpperCase()}</span></td>
                            <td>{doc.chunk_count}</td>
                            <td>{new Date(doc.created_at).toLocaleDateString()}</td>
                            {canDeleteDoc && (
                              <td>
                                <button
                                  className="delete-action-btn"
                                  onClick={() => handleDelete(doc.id, doc.name)}
                                  title="Delete document"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Field Knowledge Updates */}
              <div>
                <h4 style={{ fontSize: '0.9rem', color: '#fff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <RefreshCw size={16} color="#10b981" />
                  Field Knowledge Updates ({(knowledgeData.knowledge_updates || []).length})
                </h4>
                {(!knowledgeData.knowledge_updates || knowledgeData.knowledge_updates.length === 0) ? (
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>No field corrections submitted yet.</p>
                ) : (
                  <div className="knowledge-table-container">
                    <table className="knowledge-table">
                      <thead>
                        <tr>
                          <th>Update</th>
                          <th>Corrected Information</th>
                          <th>Status</th>
                          <th>Original Source</th>
                          {canUpdateKnowledge && <th>Action</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {knowledgeData.knowledge_updates.map((ku) => (
                          <tr key={ku.id}>
                            <td style={{ color: '#fff', fontWeight: 500 }}>
                              Update #{ku.update_number || 1}
                            </td>
                            <td style={{ maxWidth: 220, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {ku.corrected_information}
                            </td>
                            <td>
                              <span
                                className="badge"
                                style={{
                                  borderColor: ku.status === 'approved' ? '#10b981' : ku.status === 'reverted' ? '#64748b' : '#f59e0b',
                                  color: ku.status === 'approved' ? '#34d399' : ku.status === 'reverted' ? '#94a3b8' : '#fbbf24'
                                }}
                              >
                                {ku.status.toUpperCase()}
                              </span>
                            </td>
                            <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                              {ku.source_document ? `${ku.source_document}, P${ku.source_page || 1}` : 'Field note'}
                            </td>
                            {canUpdateKnowledge && (
                              <td>
                                {ku.status === 'approved' ? (
                                  <button
                                    className="delete-action-btn"
                                    onClick={() => handleRevertUpdate(ku.id, ku.update_number || 1)}
                                    title="Revert update"
                                    style={{ color: '#f59e0b' }}
                                  >
                                    <RefreshCw size={14} />
                                  </button>
                                ) : (
                                  <button
                                    className="delete-action-btn"
                                    onClick={() => handleDelete(ku.id, `Update #${ku.update_number || 1}`)}
                                    title="Delete update"
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                )}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div>
                <h4 style={{ fontSize: '0.9rem', color: '#fff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <HelpCircle size={16} color="#fbbf24" />
                  Approved Q&A Pairs ({knowledgeData.qa_pairs.length})
                </h4>
                {knowledgeData.qa_pairs.length === 0 ? (
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>No Q&A pairs added yet.</p>
                ) : (
                  <div className="knowledge-table-container">
                    <table className="knowledge-table">
                      <thead>
                        <tr>
                          <th>Question</th>
                          <th>Answer Preview</th>
                          <th>Source</th>
                          {(canUpdateKnowledge || canDeleteDoc) && <th>Action</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {knowledgeData.qa_pairs.map((qa) => (
                          <tr key={qa.id}>
                            <td style={{ color: '#fff', maxWidth: 200, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {qa.question}
                            </td>
                            <td style={{ maxWidth: 220, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {qa.answer}
                            </td>
                            <td><span className="badge" style={{ borderColor: '#facc15', color: '#facc15' }}>{qa.source}</span></td>
                            {(canUpdateKnowledge || canDeleteDoc) && (
                              <td>
                                <button
                                  className="delete-action-btn"
                                  onClick={() => handleDelete(qa.id, qa.question)}
                                  title="Delete Q&A"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
