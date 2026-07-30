import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, CheckCircle, Clock, Trash2, Download, Upload, Loader2, Search } from 'lucide-react';
import AppShell from '../components/layout/AppShell';
import { useDocumentStore } from '../stores/documentStore';
import { api } from '../utils/api';
import { filterDocuments } from '../utils/documentFilters';

const DashboardPage = () => {
    const navigate = useNavigate();
    const { documents, fetchDocuments, deleteDocument, loading } = useDocumentStore();

    const [replacingDocId, setReplacingDocId] = useState(null);
    const [replacingDocName, setReplacingDocName] = useState('');
    const [replacingLoading, setReplacingLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');
    const [documentQuery, setDocumentQuery] = useState('');
    const [sourceFilter, setSourceFilter] = useState('all');
    const replaceJsonInputRef = useRef(null);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const handleReplaceJsonClick = (docId, name, e) => {
        e.stopPropagation();
        setReplacingDocId(docId);
        setReplacingDocName(name);
        if (replaceJsonInputRef.current) {
            replaceJsonInputRef.current.click();
        }
    };

    const handleReplaceJsonFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.name.endsWith('.json')) {
            alert('Please select a valid JSON file.');
            e.target.value = '';
            return;
        }

        const confirmMsg = `Replace the parsed JSON structure for "${replacingDocName}"?\n\nStable sections keep their QA state. The portal will stop the replacement if it would remove annotated or reviewed evidence.`;
        if (!window.confirm(confirmMsg)) {
            e.target.value = '';
            setReplacingDocId(null);
            setReplacingDocName('');
            return;
        }

        const formData = new FormData();
        formData.append('json_file', file);

        try {
            setReplacingLoading(true);
            await api.post(`/documents/${replacingDocId}/replace-json`, formData, true);
            setSuccessMessage('JSON structure replaced safely. Stable QA state was preserved.');
            setTimeout(() => setSuccessMessage(''), 6000);
            fetchDocuments();
        } catch (err) {
            alert('Failed to replace JSON: ' + (err.message || 'Unknown error'));
        } finally {
            setReplacingLoading(false);
            e.target.value = '';
            setReplacingDocId(null);
            setReplacingDocName('');
        }
    };

    const handleDelete = async (docId, name, e) => {
        e.stopPropagation();
        if (window.confirm(`Are you sure you want to delete "${name}"? This will delete all annotations, footnotes validation, and source files.`)) {
            try {
                await deleteDocument(docId);
            } catch (err) {
                alert('Failed to delete document: ' + err.message);
            }
        }
    };

    // Calculate aggregated metrics
    const totalDocs = documents.length;
    const totalSections = documents.reduce((sum, doc) => sum + doc.total_sections, 0);
    const totalIssues = documents.reduce((sum, doc) => sum + (doc.stats?.has_issues || 0), 0);
    const totalReviewed = documents.reduce((sum, doc) => sum + (doc.stats?.reviewed || 0), 0);
    const overallCompletion = totalSections > 0 ? Math.round((totalReviewed / totalSections) * 100) : 0;
    const filteredDocuments = filterDocuments(
        documents,
        documentQuery,
        sourceFilter,
    );

    const handleExport = (docId, format, e) => {
        e.stopPropagation();
        window.open(api.getDownloadUrl(`/documents/${docId}/export?format=${format}`));
    };

    const handleReviewClick = (docId) => {
        navigate(`/review/${docId}`);
    };

    return (
        <AppShell 
            title="Review Dashboard"
            scrollable={true}
            actions={
                <button className="btn btn-primary" onClick={() => navigate('/upload')}>
                    <UploadCloud size={16} />
                    <span>Upload Document</span>
                </button>
            }
        >
            <input 
                type="file" 
                ref={replaceJsonInputRef} 
                style={{ display: 'none' }} 
                accept=".json"
                onChange={handleReplaceJsonFileChange}
            />

            {replacingLoading && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    backgroundColor: 'rgba(15, 23, 42, 0.6)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    zIndex: 9999,
                    gap: 16,
                    backdropFilter: 'blur(6px)'
                }}>
                    <Loader2 className="animate-spin" size={32} style={{ color: 'var(--color-accent)' }} />
                    <span style={{ color: '#ffffff', fontWeight: 600, fontSize: '0.95rem', fontFamily: 'var(--font-heading)' }}>
                        Replacing JSON structure & re-parsing sections...
                    </span>
                </div>
            )}

            <div className="dashboard-container">
                {successMessage && (
                    <div className="flex align-center gap-2 p-3" style={{ 
                        backgroundColor: 'var(--color-success-light)', 
                        color: 'var(--color-success)', 
                        borderRadius: 'var(--radius-sm)', 
                        marginBottom: 24, 
                        fontSize: '0.85rem',
                        border: '1px solid var(--color-success)',
                        display: 'flex',
                        alignItems: 'center'
                    }}>
                        <CheckCircle size={16} />
                        <span>{successMessage}</span>
                    </div>
                )}

                {/* Stats Summary Grid */}
                <section className="stats-grid">
                    <div className="stat-card">
                        <div className="stat-value">{totalDocs}</div>
                        <div className="stat-label">Uploaded Documents</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{totalSections.toLocaleString()}</div>
                        <div className="stat-label">Total Sections</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value" style={{ color: totalIssues > 0 ? 'var(--color-warning)' : 'inherit' }}>
                            {totalIssues}
                        </div>
                        <div className="stat-label">Reported Issues</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value" style={{ color: 'var(--color-success)' }}>
                            {overallCompletion}%
                        </div>
                        <div className="stat-label">Overall Completion</div>
                    </div>
                </section>

                <section className="library-head">
                    <div>
                        <span className="library-kicker">Legal review library</span>
                        <h2>Acts and editions</h2>
                        <p>
                            Showing {filteredDocuments.length.toLocaleString()} of {documents.length.toLocaleString()} documents
                        </p>
                    </div>
                    <div className="library-controls">
                        <label className="document-search" htmlFor="document-filter">
                            <Search size={16} aria-hidden="true" />
                            <span className="sr-only">Filter documents</span>
                            <input
                                id="document-filter"
                                type="search"
                                value={documentQuery}
                                onChange={(event) => setDocumentQuery(event.target.value)}
                                placeholder="Find an Act or edition…"
                                autoComplete="off"
                            />
                        </label>
                        <div className="source-filters" role="group" aria-label="Document source">
                            {[
                                ['all', 'All'],
                                ['acts_corpus', 'ACT Corpus'],
                                ['upload', 'Manual Uploads'],
                            ].map(([value, label]) => (
                                <button
                                    key={value}
                                    type="button"
                                    className={`source-filter ${sourceFilter === value ? 'active' : ''}`}
                                    onClick={() => setSourceFilter(value)}
                                    aria-pressed={sourceFilter === value}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>
                </section>

                {loading.documents ? (
                    <div style={{ textAlign: 'center', padding: 48, color: 'var(--color-text-muted)' }}>
                        Loading documents...
                    </div>
                ) : documents.length === 0 ? (
                    <div className="glass-panel" style={{ padding: '60px 20px', textAlign: 'center', border: '1px dashed var(--color-border)' }}>
                        <FileText size={48} style={{ color: 'var(--color-text-muted)', marginBottom: 16 }} />
                        <h3 style={{ marginBottom: 8 }}>No documents uploaded yet</h3>
                        <p style={{ color: 'var(--color-text-secondary)', marginBottom: 24, fontSize: '0.9rem' }}>
                            Upload Pakistan Income Tax ordinances or laws to begin QA verification.
                        </p>
                        <button className="btn btn-primary" onClick={() => navigate('/upload')}>
                            <UploadCloud size={16} />
                            <span>Upload Your First PDF + JSON</span>
                        </button>
                    </div>
                ) : filteredDocuments.length === 0 ? (
                    <div className="glass-panel library-empty">
                        <Search size={32} aria-hidden="true" />
                        <h3>No matching documents</h3>
                        <p>Try another title or choose a different source filter.</p>
                    </div>
                ) : (
                    <div className="document-grid">
                        {filteredDocuments.map((doc) => {
                            const reviewedCount = doc.stats?.reviewed || 0;
                            const totalCount = doc.total_sections;
                            const compPercent = totalCount > 0 ? Math.round((reviewedCount / totalCount) * 100) : 0;
                            const isPending = compPercent === 0;

                            // SVG Progress Circle math
                            const strokeDashoffset = 251.2 - (251.2 * compPercent) / 100;

                            return (
                                <div 
                                    key={doc.id} 
                                    className="document-card"
                                    onClick={() => handleReviewClick(doc.id)}
                                >
                                    <div className="document-info">
                                        <div>
                                            <div className="document-title-row">
                                                <span className={`source-badge ${doc.source_type === 'acts_corpus' ? 'act' : 'upload'}`}>
                                                    {doc.source_type === 'acts_corpus' ? 'ACT Corpus' : 'Manual'}
                                                </span>
                                                <h3 className="document-name">{doc.name}</h3>
                                            </div>
                                            <div className="document-meta flex align-center gap-2">
                                                <Clock size={12} />
                                                <span>Uploaded on {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                                            </div>
                                            
                                            <div className="document-stats-summary">
                                                <span className="document-stat-item">
                                                    <strong>{doc.total_sections}</strong> sections
                                                </span>
                                                <span className="document-stat-item">
                                                    <strong>{doc.total_pages}</strong> pages
                                                </span>
                                            </div>
                                        </div>

                                        {/* Actions */}
                                        <div className="flex gap-2" style={{ marginTop: 12 }}>
                                            <button 
                                                className="btn btn-primary"
                                                style={{ padding: '8px 14px', fontSize: '0.85rem' }}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleReviewClick(doc.id);
                                                }}
                                            >
                                                {isPending ? 'Start Review' : 'Continue Review'}
                                            </button>
                                            
                                            <button 
                                                className="btn btn-secondary"
                                                style={{ padding: '8px 12px', fontSize: '0.85rem' }}
                                                onClick={(e) => handleExport(doc.id, 'json', e)}
                                                title="Export report as JSON"
                                            >
                                                <Download size={14} />
                                                <span>JSON</span>
                                            </button>

                                            <button 
                                                className="btn btn-secondary"
                                                style={{ padding: '8px 12px', fontSize: '0.85rem' }}
                                                onClick={(e) => handleExport(doc.id, 'csv', e)}
                                                title="Export report as CSV"
                                            >
                                                <Download size={14} />
                                                <span>CSV</span>
                                            </button>

                                            {doc.source_type !== 'acts_corpus' && (
                                                <button
                                                    className="btn btn-secondary"
                                                    style={{ padding: '8px 12px', fontSize: '0.85rem', marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}
                                                    onClick={(e) => handleReplaceJsonClick(doc.id, doc.name, e)}
                                                    title="Replace parsed JSON structure"
                                                >
                                                    <Upload size={14} />
                                                    <span>Replace JSON</span>
                                                </button>
                                            )}
                                            
                                            <button 
                                                className="btn btn-danger"
                                                style={{ padding: '8px 12px' }}
                                                onClick={(e) => handleDelete(doc.id, doc.name, e)}
                                                title="Delete Document"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>

                                    {/* SVG Progress Circle */}
                                    <div className="progress-ring-container">
                                        <svg className="progress-ring-svg" width="90" height="90">
                                            <circle 
                                                className="progress-ring-bg" 
                                                cx="45" 
                                                cy="45" 
                                                r="36" 
                                            />
                                            <circle 
                                                className="progress-ring-bar" 
                                                cx="45" 
                                                cy="45" 
                                                r="36" 
                                                style={{
                                                    strokeDashoffset,
                                                    stroke: compPercent === 100 ? 'var(--color-success)' : 'var(--color-accent)'
                                                }}
                                            />
                                        </svg>
                                        <div className="progress-ring-text">
                                            {compPercent}%
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </AppShell>
    );
};

export default DashboardPage;
