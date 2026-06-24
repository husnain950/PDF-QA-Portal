import React from 'react';
import { Check, AlertTriangle, ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';
import { useDocumentStore } from '../../stores/documentStore';
import { useReviewStore } from '../../stores/reviewStore';

const ReviewToolbar = () => {
    const { 
        activeDocument, 
        sections, 
        activeSection, 
        fetchSection, 
        updateSectionStatus,
        loading 
    } = useDocumentStore();
    const { setCurrentPage } = useReviewStore();

    if (!activeSection) return null;

    // Find current section index in flat sections list
    const currentIndex = sections.findIndex(s => s.id === activeSection.id);
    const hasPrev = currentIndex > 0;
    const hasNext = currentIndex < sections.length - 1;

    const navigateToSection = async (index) => {
        if (index < 0 || index >= sections.length) return;
        const targetSec = sections[index];
        const sec = await fetchSection(activeDocument.id, targetSec.id);
        if (sec && sec.start_page) {
            setCurrentPage(sec.start_page);
        }
    };

    const handleApprove = async () => {
        try {
            await updateSectionStatus(activeDocument.id, activeSection.id, 'approved');
            // Auto advance
            if (hasNext) {
                setTimeout(() => navigateToSection(currentIndex + 1), 300);
            }
        } catch (e) {
            alert('Failed to update status: ' + e.message);
        }
    };

    const handleFlag = async () => {
        try {
            await updateSectionStatus(activeDocument.id, activeSection.id, 'has_issues');
        } catch (e) {
            alert('Failed to update status: ' + e.message);
        }
    };

    return (
        <div className="review-toolbar glass-panel" style={{ gap: 12, overflow: 'hidden', padding: '0 16px' }}>
            {/* Left side: Status Badge */}
            <div className="flex align-center gap-2" style={{ flexShrink: 0 }}>
                {loading.activeSection ? (
                    <Loader2 className="animate-spin" size={14} style={{ color: 'var(--color-accent)' }} />
                ) : (
                    <>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', whiteSpace: 'nowrap' }}>
                            Status:
                        </span>
                        <span 
                            className={`badge badge-${activeSection.review_status === 'has_issues' ? 'flagged' : activeSection.review_status}`} 
                            style={{ fontSize: '0.75rem', padding: '3px 8px', whiteSpace: 'nowrap' }}
                        >
                            {activeSection.review_status === 'has_issues' ? 'flagged' : activeSection.review_status}
                        </span>
                    </>
                )}
            </div>

            {/* Center: Actions */}
            <div className="flex align-center gap-2" style={{ justifyContent: 'center', flex: 1 }}>
                <button
                    className={`btn ${activeSection.review_status === 'approved' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ 
                        padding: '6px 12px', 
                        fontSize: '0.8rem',
                        backgroundColor: activeSection.review_status === 'approved' ? 'var(--color-success)' : 'transparent',
                        borderColor: activeSection.review_status === 'approved' ? 'var(--color-success)' : 'var(--color-border)',
                        color: activeSection.review_status === 'approved' ? '#ffffff' : 'var(--color-text-secondary)',
                        whiteSpace: 'nowrap'
                    }}
                    onClick={handleApprove}
                    disabled={loading.activeSection}
                    title="Approve Section & Move Next"
                >
                    <Check size={14} />
                    <span>Approve</span>
                </button>

                <button
                    className={`btn ${activeSection.review_status === 'has_issues' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ 
                        padding: '6px 12px', 
                        fontSize: '0.8rem',
                        backgroundColor: activeSection.review_status === 'has_issues' ? 'var(--color-error)' : 'transparent',
                        borderColor: activeSection.review_status === 'has_issues' ? 'var(--color-error)' : 'var(--color-border)',
                        color: activeSection.review_status === 'has_issues' ? '#ffffff' : 'var(--color-text-secondary)',
                        whiteSpace: 'nowrap'
                    }}
                    onClick={handleFlag}
                    disabled={loading.activeSection}
                    title="Flag Section"
                >
                    <AlertTriangle size={14} />
                    <span>Flag</span>
                </button>
            </div>

            {/* Right side: Navigation (icon buttons) */}
            <div className="flex align-center gap-1" style={{ flexShrink: 0 }}>
                <button
                    className="btn btn-secondary btn-icon"
                    style={{ width: 32, height: 32 }}
                    onClick={() => navigateToSection(currentIndex - 1)}
                    disabled={!hasPrev || loading.activeSection}
                    title="Previous Section"
                >
                    <ArrowLeft size={14} />
                </button>

                <button
                    className="btn btn-secondary btn-icon"
                    style={{ width: 32, height: 32 }}
                    onClick={() => navigateToSection(currentIndex + 1)}
                    disabled={!hasNext || loading.activeSection}
                    title="Next Section"
                >
                    <ArrowRight size={14} />
                </button>
            </div>
        </div>
    );
};

export default ReviewToolbar;
