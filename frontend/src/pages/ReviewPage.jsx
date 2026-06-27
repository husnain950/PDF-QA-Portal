import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';

import AppShell from '../components/layout/AppShell';
import Sidebar from '../components/layout/Sidebar';
import SplitPane from '../components/review/SplitPane';
import PdfPanel from '../components/review/PdfPanel';
import HtmlPanel from '../components/review/HtmlPanel';
import ReviewToolbar from '../components/review/ReviewToolbar';

import { useDocumentStore } from '../stores/documentStore';
import { useReviewStore } from '../stores/reviewStore';
import { useKeyboardNav } from '../hooks/useKeyboardNav';
import { api } from '../utils/api';

const ReviewPage = () => {
    const { documentId } = useParams();
    const navigate = useNavigate();

    const { 
        activeDocument, 
        sections, 
        activeSection, 
        pageSections,
        fetchDocument, 
        fetchSections, 
        fetchSection,
        fetchSectionsByPage,
        loading 
    } = useDocumentStore();

    const { currentPage, viewMode, setViewMode, setCurrentPage } = useReviewStore();
    const [initialLoad, setInitialLoad] = useState(true);
    const [error, setError] = useState('');

    // Wire keyboard navigation for arrow keys
    useKeyboardNav({
        onArrowLeft: () => {
            if (currentPage > 1) setCurrentPage(currentPage - 1);
        },
        onArrowRight: () => {
            if (activeDocument && currentPage < activeDocument.total_pages) {
                setCurrentPage(currentPage + 1);
            }
        }
    });

    useEffect(() => {
        const loadDocAndSections = async () => {
            setInitialLoad(true);
            try {
                // Fetch document metadata
                const doc = await fetchDocument(documentId);
                if (!doc) {
                    setError('Document not found');
                    return;
                }

                // Fetch sections list for TOC
                await fetchSections(documentId);
            } catch (err) {
                setError('Failed to load review data');
                console.error(err);
            } finally {
                setInitialLoad(false);
            }
        };

        if (documentId) {
            loadDocAndSections();
        }
    }, [documentId, fetchDocument, fetchSections]);

    // Fetch page sections when in Page View
    useEffect(() => {
        if (viewMode === 'page' && currentPage) {
            fetchSectionsByPage(documentId, currentPage);
        }
    }, [viewMode, currentPage, documentId, fetchSectionsByPage]);

    // Resume Logic: Set first pending section as active once sections list loads
    useEffect(() => {
        if (!initialLoad && sections.length > 0 && !activeSection && viewMode === 'section') {
            // Find first pending section
            const firstPending = sections.find(s => s.review_status === 'pending') || sections[0];
            
            const loadInitialSection = async () => {
                const sec = await fetchSection(documentId, firstPending.id);
                if (sec && sec.start_page) {
                    setCurrentPage(sec.start_page);
                }
            };
            loadInitialSection();
        }
    }, [initialLoad, sections, activeSection, documentId, fetchSection, setCurrentPage, viewMode]);

    if (initialLoad) {
        return (
            <div className="flex flex-col justify-center align-center" style={{ height: '100vh', gap: 16 }}>
                <Loader2 className="animate-spin" size={32} style={{ color: 'var(--color-accent)' }} />
                <span style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>Loading Workspace...</span>
            </div>
        );
    }

    if (error || !activeDocument) {
        return (
            <div className="flex flex-col justify-center align-center" style={{ height: '100vh', gap: 16 }}>
                <AlertCircle size={48} style={{ color: 'var(--color-error)' }} />
                <h3>Workspace Error</h3>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>{error || 'Document metadata could not be fetched'}</p>
                <button className="btn btn-primary" onClick={() => navigate('/')}>
                    <ArrowLeft size={16} />
                    <span>Back to Dashboard</span>
                </button>
            </div>
        );
    }

    const pdfUrl = api.getFileUrl(activeDocument.pdf_filename);

    const leftPanel = (
        <PdfPanel pdfUrl={pdfUrl} />
    );

    const rightPanel = (
        <div className="flex flex-col height-100" style={{ height: '100%' }}>
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {viewMode === 'section' ? (
                    activeSection ? (
                        <HtmlPanel 
                            section={activeSection}
                            sectionId={activeSection.id}
                            htmlContent={activeSection.html_content}
                            footnotes={activeSection.footnotes}
                        />
                    ) : (
                        <div className="flex justify-center align-center" style={{ height: '100%', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                            Select a section from the Table of Contents to begin review
                        </div>
                    )
                ) : (
                    /* Page View: list of sections covering current page */
                    pageSections.length > 0 ? (
                        <div style={{ flex: 1, overflowY: 'auto' }}>
                            {pageSections.map(sec => (
                                <div key={sec.id} style={{ borderBottom: '4px solid var(--color-border)', paddingBottom: 24 }}>
                                    <div style={{ padding: '12px 24px', backgroundColor: 'var(--color-bg-tertiary)', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                                            Section {sec.section_code}: {sec.section_heading}
                                        </span>
                                        <span className={`badge badge-${sec.review_status}`}>
                                            {sec.review_status}
                                        </span>
                                    </div>
                                    <HtmlPanel 
                                        section={sec}
                                        sectionId={sec.id}
                                        htmlContent={sec.html_content}
                                        footnotes={sec.footnotes}
                                    />
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="flex justify-center align-center" style={{ height: '100%', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                            No parsed sections map to page {currentPage}
                        </div>
                    )
                )}
            </div>
            {viewMode === 'section' && <ReviewToolbar />}
        </div>
    );

    const statsText = activeDocument.stats
        ? `(${activeDocument.stats.approved}/${activeDocument.total_sections} approved · ${activeDocument.stats.has_issues} issues)`
        : '';

    const actions = (
        <div className="flex align-center gap-2">
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>View:</span>
            <div className="flex" style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                <button
                    className={`btn ${viewMode === 'section' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '6px 12px', fontSize: '0.75rem', borderRadius: 0, border: 'none' }}
                    onClick={() => setViewMode('section')}
                >
                    Section View
                </button>
                <button
                    className={`btn ${viewMode === 'page' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '6px 12px', fontSize: '0.75rem', borderRadius: 0, border: 'none' }}
                    onClick={() => setViewMode('page')}
                >
                    Page View
                </button>
            </div>
        </div>
    );

    return (
        <AppShell 
            title={`${activeDocument.name} ${statsText}`}
            showBackButton={true}
            sidebarContent={<Sidebar documentId={documentId} />}
            actions={actions}
        >
            <SplitPane left={leftPanel} right={rightPanel} />
        </AppShell>
    );
};

export default ReviewPage;
