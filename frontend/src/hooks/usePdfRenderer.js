import { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

// Set up worker
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

export const usePdfRenderer = (pdfUrl, pageNumber, zoom, canvasRef) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [numPages, setNumPages] = useState(0);
    const pdfDocRef = useRef(null);
    const renderTaskRef = useRef(null);

    // Load PDF Document
    useEffect(() => {
        if (!pdfUrl) {
            setNumPages(0);
            pdfDocRef.current = null;
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
                    pdfDocRef.current = pdf;
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
            if (pdfDocRef.current) {
                if (typeof pdfDocRef.current.destroy === 'function') {
                    pdfDocRef.current.destroy();
                } else if (typeof pdfDocRef.current.cleanup === 'function') {
                    pdfDocRef.current.cleanup();
                }
                pdfDocRef.current = null;
            }
        };

    }, [pdfUrl]);

    // Render Page
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !pdfDocRef.current) return;

        let isCancelled = false;

        const renderPage = async () => {
            try {
                if (renderTaskRef.current) {
                    renderTaskRef.current.cancel();
                }

                const page = await pdfDocRef.current.getPage(pageNumber);
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
    }, [pageNumber, zoom, pdfDocRef.current, canvasRef]);

    return { loading, error, numPages };
};
