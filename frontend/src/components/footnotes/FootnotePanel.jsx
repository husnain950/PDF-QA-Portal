import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Check, AlertCircle } from 'lucide-react';
import { useReviewStore } from '../../stores/reviewStore';

const FootnotePanel = ({ footnotes }) => {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const { updateFootnoteStatus, setCurrentPage } = useReviewStore();

    if (!footnotes || footnotes.length === 0) return null;

    const handlePageClick = (page, e) => {
        e.preventDefault();
        if (page) {
            setCurrentPage(page);
        }
    };

    return (
        <div className="footnotes-panel glass-panel" style={{ background: 'var(--color-bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}>
            <div 
                className="footnotes-header" 
                onClick={() => setIsCollapsed(!isCollapsed)}
            >
                <h3 className="flex align-center gap-2" style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                    Footnotes ({footnotes.length})
                </h3>
                <button className="btn btn-secondary btn-icon" style={{ border: 'none', height: 24, width: 24 }}>
                    {isCollapsed ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
            </div>

            {!isCollapsed && (
                <div className="footnotes-list">
                    {footnotes.map((fn) => (
                        <div 
                            key={fn.id} 
                            className={`footnote-card ${fn.review_status === 'approved' ? 'approved' : fn.review_status === 'has_issues' ? 'flagged' : ''}`}
                        >
                            <div className="footnote-meta">
                                <span className="footnote-marker">Marker: {fn.marker}</span>
                                {fn.page && (
                                    <button 
                                        className="btn" 
                                        onClick={(e) => handlePageClick(fn.page, e)}
                                        style={{ 
                                            background: 'var(--color-accent-light)', 
                                            color: 'var(--color-accent)', 
                                            fontSize: '0.75rem', 
                                            padding: '2px 8px',
                                            fontWeight: 700,
                                            border: 'none',
                                            cursor: 'pointer',
                                            borderRadius: 'var(--radius-sm)'
                                        }}
                                        title={`Jump PDF to page ${fn.page}`}
                                    >
                                        PDF Page {fn.page}
                                    </button>
                                )}
                            </div>

                            <div className="footnote-text">
                                {fn.text}
                            </div>

                            <div className="flex gap-2" style={{ marginTop: 8, justifyContent: 'flex-end' }}>
                                <button
                                    className={`btn ${fn.review_status === 'approved' ? 'btn-primary' : 'btn-secondary'}`}
                                    style={{ 
                                        padding: '4px 10px', 
                                        fontSize: '0.75rem',
                                        backgroundColor: fn.review_status === 'approved' ? 'var(--color-success)' : 'transparent',
                                        color: fn.review_status === 'approved' ? '#ffffff' : 'var(--color-text-secondary)',
                                        borderColor: fn.review_status === 'approved' ? 'var(--color-success)' : 'var(--color-border)',
                                    }}
                                    onClick={() => updateFootnoteStatus(fn.id, fn.review_status === 'approved' ? 'pending' : 'approved')}
                                >
                                    <Check size={12} />
                                    <span>{fn.review_status === 'approved' ? 'Approved' : 'Approve'}</span>
                                </button>
                                <button
                                    className={`btn ${fn.review_status === 'has_issues' ? 'btn-primary' : 'btn-secondary'}`}
                                    style={{ 
                                        padding: '4px 10px', 
                                        fontSize: '0.75rem',
                                        backgroundColor: fn.review_status === 'has_issues' ? 'var(--color-error)' : 'transparent',
                                        color: fn.review_status === 'has_issues' ? '#ffffff' : 'var(--color-text-secondary)',
                                        borderColor: fn.review_status === 'has_issues' ? 'var(--color-error)' : 'var(--color-border)',
                                    }}
                                    onClick={() => updateFootnoteStatus(fn.id, fn.review_status === 'has_issues' ? 'pending' : 'has_issues')}
                                >
                                    <AlertCircle size={12} />
                                    <span>{fn.review_status === 'has_issues' ? 'Flagged' : 'Flag Issue'}</span>
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default FootnotePanel;
