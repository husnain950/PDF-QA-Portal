import React, { useRef } from 'react';
import { ZoomIn, ZoomOut, Maximize2, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { usePdfDocument, usePdfPageRenderer } from '../../hooks/usePdfRenderer';
import { useUiStore } from '../../stores/uiStore';
import { useReviewStore } from '../../stores/reviewStore';
import { useDocumentStore } from '../../stores/documentStore';

// Helper component to render a single PDF page
const PdfPage = ({ pdfDoc, pageNumber, zoom }) => {
    const canvasRef = useRef(null);
    const { loading, error } = usePdfPageRenderer(pdfDoc, pageNumber, zoom, canvasRef);

    return (
        <div className="pdf-canvas-wrapper" style={{ position: 'relative', marginBottom: '24px' }}>
            {loading && (
                <div className="flex justify-center align-center" style={{ position: 'absolute', inset: 0, background: 'rgba(255, 255, 255, 0.4)', zIndex: 1 }}>
                    <Loader2 className="animate-spin" style={{ color: 'var(--color-accent)' }} size={24} />
                </div>
            )}
            {error && (
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-error)', fontSize: '0.8rem' }}>
                    Error rendering page {pageNumber}
                </div>
            )}
            <canvas ref={canvasRef} className="pdf-canvas" />
            <div style={{ 
                position: 'absolute', 
                bottom: 8, 
                right: 8, 
                backgroundColor: 'rgba(0, 0, 0, 0.6)', 
                color: '#ffffff', 
                padding: '2px 8px', 
                borderRadius: '4px', 
                fontSize: '0.75rem',
                pointerEvents: 'none',
                zIndex: 2
            }}>
                Page {pageNumber}
            </div>
        </div>
    );
};

const PdfPanel = ({ pdfUrl }) => {
    const { pdfZoom, zoomIn, zoomOut, resetZoom } = useUiStore();
    const { currentPage, setCurrentPage, viewMode } = useReviewStore();
    const { activeSection } = useDocumentStore();
    
    const { pdfDoc, loading: docLoading, error: docError, numPages } = usePdfDocument(pdfUrl);

    const isSectionView = viewMode === 'section' && activeSection;
    const startPage = isSectionView ? (activeSection.start_page || 1) : currentPage;
    const endPage = isSectionView ? (activeSection.end_page || startPage) : currentPage;

    const pagesToRender = [];
    if (pdfDoc) {
        for (let i = startPage; i <= endPage; i++) {
            if (i >= 1 && i <= numPages) {
                pagesToRender.push(i);
            }
        }
    }

    const handlePrevPage = () => {
        if (!isSectionView && currentPage > 1) {
            setCurrentPage(currentPage - 1);
        }
    };

    const handleNextPage = () => {
        if (!isSectionView && currentPage < numPages) {
            setCurrentPage(currentPage + 1);
        }
    };

    const pageDisplayText = isSectionView
        ? (startPage === endPage ? `Page ${startPage} of ${numPages || '...'}` : `Pages ${startPage}–${endPage} of ${numPages || '...'}`)
        : `Page ${currentPage} of ${numPages || '...'}`;

    return (
        <div className="flex flex-col height-100" style={{ height: '100%' }}>
            {/* Header / Controls */}
            <div className="panel-header glass-panel">
                <span className="panel-title">PDF Original</span>
                
                {/* Page Navigation */}
                <div className="flex align-center gap-2">
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={handlePrevPage}
                        disabled={isSectionView || currentPage <= 1 || docLoading}
                        title={isSectionView ? "Disabled in Section View" : "Previous PDF Page"}
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, minWidth: 100, textAlign: 'center' }}>
                        {pageDisplayText}
                    </span>
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={handleNextPage}
                        disabled={isSectionView || currentPage >= numPages || docLoading}
                        title={isSectionView ? "Disabled in Section View" : "Next PDF Page"}
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>

                {/* Zoom Controls */}
                <div className="flex align-center gap-1">
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={zoomOut}
                        disabled={pdfZoom <= 0.5 || docLoading}
                        title="Zoom Out"
                    >
                        <ZoomOut size={16} />
                    </button>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, minWidth: 48, textAlign: 'center' }}>
                        {Math.round(pdfZoom * 100)}%
                    </span>
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={zoomIn}
                        disabled={pdfZoom >= 3.0 || docLoading}
                        title="Zoom In"
                    >
                        <ZoomIn size={16} />
                    </button>
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={resetZoom}
                        disabled={pdfZoom === 1.0 || docLoading}
                        title="Reset Zoom"
                    >
                        <Maximize2 size={16} />
                    </button>
                </div>
            </div>

            {/* Canvas Body */}
            <div className="panel-body">
                {docLoading && (
                    <div className="flex justify-center align-center" style={{ position: 'absolute', inset: 0, background: 'rgba(var(--color-bg-primary), 0.5)', zIndex: 3 }}>
                        <Loader2 className="animate-spin" style={{ color: 'var(--color-accent)' }} size={32} />
                    </div>
                )}
                
                {docError && (
                    <div className="p-6 flex flex-col justify-center align-center" style={{ color: 'var(--color-error)', height: '100%' }}>
                        <p style={{ fontWeight: 600 }}>Failed to load PDF</p>
                        <p style={{ fontSize: '0.8rem' }}>{docError.message || 'Check browser console'}</p>
                    </div>
                )}

                <div className="pdf-scroll-container">
                    {pdfDoc && pagesToRender.map((pageNumber) => (
                        <PdfPage 
                            key={pageNumber} 
                            pdfDoc={pdfDoc} 
                            pageNumber={pageNumber} 
                            zoom={pdfZoom} 
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default PdfPanel;

