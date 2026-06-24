import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, CheckCircle, AlertCircle, Clock, Trash2, Download } from 'lucide-react';
import AppShell from '../components/layout/AppShell';
import { useDocumentStore } from '../stores/documentStore';
import { api } from '../utils/api';

const DashboardPage = () => {
    const navigate = useNavigate();
    const { documents, fetchDocuments, deleteDocument, loading } = useDocumentStore();

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

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
            actions={
                <button className="btn btn-primary" onClick={() => navigate('/upload')}>
                    <UploadCloud size={16} />
                    <span>Upload Document</span>
                </button>
            }
        >
            <div className="dashboard-container">
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

                <h2 style={{ marginBottom: 24, fontSize: '1.25rem' }}>Your Documents</h2>

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
                ) : (
                    <div className="document-grid">
                        {documents.map((doc) => {
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
                                            <h3 className="document-name">{doc.name}</h3>
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

                                            <button 
                                                className="btn btn-danger"
                                                style={{ padding: '8px 12px', marginLeft: 'auto' }}
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
