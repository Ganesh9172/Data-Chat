import React, { useState } from 'react';
import { X, BarChart3, Check, Trash2 } from 'lucide-react';

export default function PowerBIModal({ isOpen, onClose, activeContext, onSaveContext }) {
  const [reportName, setReportName] = useState(activeContext?.report_name || 'Plant Operations Monitor');
  const [visualTitle, setVisualTitle] = useState(activeContext?.visual_title || 'Pressure vs Temperature Alert');
  const [filters, setFilters] = useState(
    activeContext?.selected_filters ? JSON.stringify(activeContext.selected_filters) : '{"Unit": "Boiler 4", "Status": "Alert"}'
  );
  const [dataSummary, setDataSummary] = useState(
    activeContext?.data_summary || 'Line A sensor reported temperature reached 92°C with rising pressure alert.'
  );

  if (!isOpen) return null;

  const handleApply = (e) => {
    e.preventDefault();
    let parsedFilters = null;
    try {
      if (filters.trim()) {
        parsedFilters = JSON.parse(filters);
      }
    } catch {
      parsedFilters = { raw: filters };
    }

    onSaveContext({
      report_name: reportName,
      visual_title: visualTitle,
      selected_filters: parsedFilters,
      data_summary: dataSummary
    });
    onClose();
  };

  const handleClear = () => {
    onSaveContext(null); https://127.0.0.1:57505/static/artifacts/00738c56-d75e-4c70-b6e9-fe7763afa556/.user_uploaded/media_1789200295104.png?csrf=c33aca91-10a0-4f51-ad18-a56d5326f3c2
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <BarChart3 size={20} color="#facc15" />
            Power BI Integration Context
          </h3>
          <button className="close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem' }}>
            This simulator demonstrates Firebird AI's future Power BI compatibility.
            When active, the selected report metadata, visuals, and active filters are sent to <code>POST /api/chat</code> to ground answers in both the knowledge base and report context.
          </p>

          <form onSubmit={handleApply} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label>Report Name</label>
              <input
                type="text"
                className="form-input"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Active Visual Title</label>
              <input
                type="text"
                className="form-input"
                value={visualTitle}
                onChange={(e) => setVisualTitle(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Selected Slicers / Filters (JSON)</label>
              <input
                type="text"
                className="form-input"
                style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}
                value={filters}
                onChange={(e) => setFilters(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Report Data Summary</label>
              <textarea
                className="form-textarea"
                rows={2}
                value={dataSummary}
                onChange={(e) => setDataSummary(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
              <button type="submit" className="primary-btn" style={{ flex: 1 }}>
                <Check size={16} />
                Attach to Chat
              </button>
              {activeContext && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="primary-btn"
                  style={{ backgroundColor: 'var(--bg-tertiary)', background: 'none', border: '1px solid var(--border-subtle)', color: '#ef4444' }}
                >
                  <Trash2 size={16} />
                  Detach
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
