import React, { useState } from 'react';
import { Lock, Shield, AlertCircle, ArrowRight, X } from 'lucide-react';
import { adminLogin } from '../services/api';

export default function LoginModal({ isOpen, onClose, onLoginSuccess }) {
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('admin');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await adminLogin(password.trim(), username.trim());
      onLoginSuccess(data);
      setPassword('');
      onClose();
    } catch (err) {
      setError(err.message || 'Admin authentication failed. Please verify password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay login-modal-overlay" style={{ zIndex: 1000 }} onClick={onClose}>
      <div className="modal-content login-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          background: 'linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(15, 23, 42, 0.8) 100%)',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(249, 115, 22, 0.35)'
            }}>
              <Shield size={22} color="#fff" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#fff', fontWeight: 600 }}>
                Admin Authentication
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Unlock Knowledge Base management
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: 4,
              borderRadius: 4
            }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '24px' }}>
          {error && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-sm)',
              color: '#f87171',
              fontSize: '0.84rem',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 16
            }}>
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem' }}>
                <Lock size={14} color="#94a3b8" />
                Admin Password
              </label>
              <input
                type="password"
                className="form-input"
                placeholder="Enter administrator password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
                required
              />
            </div>

            <button
              type="submit"
              className="primary-btn"
              disabled={loading || !password}
              style={{
                marginTop: 6,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                padding: '10px 16px'
              }}
            >
              {loading ? 'Verifying...' : (
                <>
                  <span>Unlock Admin Access</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
