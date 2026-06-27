import { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

// Set up worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

// Hook to load the PDF document once
export const usePdfDocument = (pdfUrl) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [numPages, setNumPages] = useState(0);
    const [pdfDoc, setPdfDoc] = useState(null);

    useEffect(() => {
        if (!pdfUrl) {
            setNumPages(0);
            setPdfDoc(null);
            return;
        }

        let isCancelled = false;

        const loadPdf = async () => {
            setLoading(true);
            setError(null);
            try {
                const loadingTask = pdfjsLib.getDocument({ url: pdfUrl });
                const pdf = await loadingTask.promise;
                if (!isCancelled) {
                    setPdfDoc(pdf);
                    setNumPages(pdf.numPages);
                }
            } catch (err) {
                if (!isCancelled) {
                    console.error('Error loading PDF:', err);
                    setError(err);
                }
            } finally {
                if (!isCancelled) {
                    setLoading(false);
                }
            }
        };

        loadPdf();

        return () => {
            isCancelled = true;
            if (pdfDoc) {
                if (typeof pdfDoc.destroy === 'function') {
                    pdfDoc.destroy();
                } else if (typeof pdfDoc.cleanup === 'function') {
                    pdfDoc.cleanup();
                }
            }
            setPdfDoc(null);
        };
    }, [pdfUrl]);

    return { pdfDoc, loading, error, numPages };
};

// Hook to render a single PDF page given a loaded pdfDoc object
export const usePdfPageRenderer = (pdfDoc, pageNumber, zoom, canvasRef) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const renderTaskRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !pdfDoc) return;

        let isCancelled = false;

        const renderPage = async () => {
            setLoading(true);
            setError(null);
            try {
                if (renderTaskRef.current) {
                    renderTaskRef.current.cancel();
                }

                const page = await pdfDoc.getPage(pageNumber);
                if (isCancelled) return;

                const viewport = page.getViewport({ scale: zoom });
                const context = canvas.getContext('2d');
                
                canvas.height = viewport.height;
                canvas.width = viewport.width;

                const renderContext = {
                    canvasContext: context,
                    viewport: viewport
                };

                const renderTask = page.render(renderContext);
                renderTaskRef.current = renderTask;
                
                await renderTask.promise;
            } catch (err) {
                if (err.name !== 'RenderingCancelledException' && !isCancelled) {
                    console.error('Error rendering page:', err);
                    setError(err);
                }
            } finally {
                if (!isCancelled) {
                    setLoading(false);
                }
            }
        };

        renderPage();

        return () => {
            isCancelled = true;
            if (renderTaskRef.current) {
                renderTaskRef.current.cancel();
            }
        };
    }, [pageNumber, zoom, pdfDoc, canvasRef]);

    return { loading, error };
};

// Backward-compatible original hook
export const usePdfRenderer = (pdfUrl, pageNumber, zoom, canvasRef) => {
    const { pdfDoc, loading: docLoading, error: docError, numPages } = usePdfDocument(pdfUrl);
    const { loading: pageLoading, error: pageError } = usePdfPageRenderer(pdfDoc, pageNumber, zoom, canvasRef);

    return {
        loading: docLoading || pageLoading,
        error: docError || pageError,
        numPages
    };
};

