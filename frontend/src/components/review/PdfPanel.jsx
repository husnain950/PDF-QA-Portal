import React, { useRef } from 'react';
import { ZoomIn, ZoomOut, Maximize2, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { usePdfRenderer } from '../../hooks/usePdfRenderer';
import { useUiStore } from '../../stores/uiStore';
import { useReviewStore } from '../../stores/reviewStore';

const PdfPanel = ({ pdfUrl }) => {
    const canvasRef = useRef(null);
    const { pdfZoom, zoomIn, zoomOut, resetZoom } = useUiStore();
    const { currentPage, setCurrentPage } = useReviewStore();
    
    const { loading, error, numPages } = usePdfRenderer(
        pdfUrl,
        currentPage,
        pdfZoom,
        canvasRef
    );

    const handlePrevPage = () => {
        if (currentPage > 1) {
            setCurrentPage(currentPage - 1);
        }
    };

    const handleNextPage = () => {
        if (currentPage < numPages) {
            setCurrentPage(currentPage + 1);
        }
    };

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
                        disabled={currentPage <= 1 || loading}
                        title="Previous PDF Page"
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, minWidth: 80, textAlign: 'center' }}>
                        Page {currentPage} of {numPages || '...'}
                    </span>
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={handleNextPage}
                        disabled={currentPage >= numPages || loading}
                        title="Next PDF Page"
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>

                {/* Zoom Controls */}
                <div className="flex align-center gap-1">
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={zoomOut}
                        disabled={pdfZoom <= 0.5 || loading}
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
                        disabled={pdfZoom >= 3.0 || loading}
                        title="Zoom In"
                    >
                        <ZoomIn size={16} />
                    </button>
                    <button 
                        className="btn btn-secondary btn-icon"
                        onClick={resetZoom}
                        disabled={pdfZoom === 1.0 || loading}
                        title="Reset Zoom"
                    >
                        <Maximize2 size={16} />
                    </button>
                </div>
            </div>

            {/* Canvas Body */}
            <div className="panel-body">
                {loading && (
                    <div className="flex justify-center align-center" style={{ position: 'absolute', inset: 0, background: 'rgba(var(--color-bg-primary), 0.5)', zIndex: 3 }}>
                        <Loader2 className="animate-spin" style={{ color: 'var(--color-accent)' }} size={32} />
                    </div>
                )}
                
                {error && (
                    <div className="p-6 flex flex-col justify-center align-center" style={{ color: 'var(--color-error)', height: '100%' }}>
                        <p style={{ fontWeight: 600 }}>Failed to load PDF</p>
                        <p style={{ fontSize: '0.8rem' }}>{error.message || 'Check browser console'}</p>
                    </div>
                )}

                <div className="pdf-scroll-container">
                    <div className="pdf-canvas-wrapper">
                        <canvas ref={canvasRef} className="pdf-canvas" />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PdfPanel;
