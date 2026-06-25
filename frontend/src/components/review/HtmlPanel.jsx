import React, { useRef, useEffect, useState } from 'react';
import { useTextSelection } from '../../hooks/useTextSelection';
import { useReviewStore } from '../../stores/reviewStore';
import AnnotationPopover from '../annotations/AnnotationPopover';
import FootnotePanel from '../footnotes/FootnotePanel';
import { Copy, Check, Code, Eye } from 'lucide-react';

const HtmlPanel = ({ sectionId, htmlContent, footnotes }) => {
    const containerRef = useRef(null);
    const { annotations, createAnnotation, fetchAnnotations } = useReviewStore();
    const [popoverCoords, setPopoverCoords] = useState(null);
    const [selectionData, setSelectionData] = useState(null);
    const [showRaw, setShowRaw] = useState(false);
    const [copied, setCopied] = useState(false);

    // Fetch annotations whenever section changes
    useEffect(() => {
        if (sectionId) {
            fetchAnnotations(sectionId);
        }
    }, [sectionId, fetchAnnotations]);

    // Listen to text selections
    const { clearSelection } = useTextSelection(containerRef, (data) => {
        if (showRaw) return; // Disable annotations/selection logic in raw mode
        setSelectionData(data);
        setPopoverCoords(data.coords);
    });

    // Inject highlighting marks into rendered DOM
    useEffect(() => {
        const container = containerRef.current;
        if (!container || !htmlContent) return;

        // Reset DOM to clean state
        container.innerHTML = htmlContent;

        if (!annotations || annotations.length === 0) return;

        // Inject <mark> tags for all annotations
        annotations.forEach((annot) => {
            if (annot.footnote_id) return; // Skip footnote annotations in main text container
            if (annot.status === 'resolved') return; // Skip resolved annotations
            const range = createRangeFromOffsets(container, annot.start_offset, annot.end_offset);
            if (range) {
                const mark = document.createElement('mark');
                mark.className = 'qa-highlight';
                mark.setAttribute('data-annotation-id', annot.id);
                mark.setAttribute('data-severity', annot.severity);
                mark.setAttribute('title', `Issue: ${annot.issue_description || 'No description'}`);
                
                try {
                    range.surroundContents(mark);
                } catch (e) {
                    // Fallback if cross-element selection
                    try {
                        const content = range.extractContents();
                        mark.appendChild(content);
                        range.insertNode(mark);
                    } catch (err) {
                        console.error('Failed to apply fallback highlight:', err);
                    }
                }
            }
        });
    }, [htmlContent, annotations]);

    const handleSaveAnnotation = async (data) => {
        if (!sectionId || !selectionData) return;
        try {
            await createAnnotation(sectionId, {
                highlightedText: selectionData.text,
                startOffset: selectionData.start,
                endOffset: selectionData.end,
                issueDescription: data.issueDescription,
                severity: data.severity,
                reviewerName: data.reviewerName,
                footnoteId: selectionData.footnoteId
            });
            handleCancelAnnotation();
        } catch (e) {
            alert('Failed to save annotation: ' + e.message);
        }
    };

    const handleCancelAnnotation = () => {
        clearSelection();
        setPopoverCoords(null);
        setSelectionData(null);
    };

    const handleFootnoteSelect = (footnoteId, text, start, end, coords) => {
        setSelectionData({
            text,
            start,
            end,
            footnoteId
        });
        setPopoverCoords(coords);
    };

    const handleCopyHtml = () => {
        if (!htmlContent) return;
        
        const copyToClipboard = async (text) => {
            // 1. Try modern Clipboard API first
            if (navigator.clipboard && navigator.clipboard.writeText) {
                try {
                    await navigator.clipboard.writeText(text);
                    return; // Successfully copied
                } catch (err) {
                    console.warn('Modern clipboard API failed, trying fallback method...', err);
                }
            }
            
            // 2. Fallback using a temporary textarea
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            textarea.style.top = '0';
            textarea.setAttribute('readonly', ''); // Prevent visual keyboard on mobile
            document.body.appendChild(textarea);
            
            const activeEl = document.activeElement;
            textarea.select();
            textarea.setSelectionRange(0, 99999); // Safe selection range for iOS
            
            try {
                const successful = document.execCommand('copy');
                if (!successful) {
                    throw new Error('execCommand returned false');
                }
            } catch (err) {
                console.error('Fallback copy method failed:', err);
                // 3. Last resort fallback: ask user to copy manually via prompt
                window.prompt("Copy HTML (Ctrl+C / Cmd+C):", text);
            } finally {
                document.body.removeChild(textarea);
                if (activeEl && typeof activeEl.focus === 'function') {
                    activeEl.focus();
                }
            }
        };

        copyToClipboard(htmlContent)
            .then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            })
            .catch((err) => {
                console.error('All copy methods failed: ', err);
            });
    };

    return (
        <div className="flex flex-col height-100" style={{ height: '100%' }} onClick={handleCancelAnnotation}>
            <div className="panel-header glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', boxSizing: 'border-box' }}>
                <div className="flex flex-col">
                    <span className="panel-title">Parsed HTML Content</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                        {showRaw ? 'Viewing raw HTML markup code' : 'Highlight text in this pane to report discrepancies'}
                    </span>
                </div>
                <div className="flex align-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <button 
                        className={`btn ${showRaw ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ padding: '6px 12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}
                        onClick={() => setShowRaw(!showRaw)}
                        title={showRaw ? "Switch to Rendered HTML View" : "Switch to Raw HTML Code View"}
                    >
                        {showRaw ? <Eye size={14} /> : <Code size={14} />}
                        <span>{showRaw ? 'Rendered' : 'Raw HTML'}</span>
                    </button>
                    <button 
                        className="btn btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}
                        onClick={handleCopyHtml}
                        title="Copy raw HTML to clipboard"
                    >
                        {copied ? <Check size={14} style={{ color: 'var(--color-success)' }} /> : <Copy size={14} />}
                        <span>{copied ? 'Copied!' : 'Copy HTML'}</span>
                    </button>
                </div>
            </div>

            <div className="panel-body" style={{ position: 'relative' }}>
                <div 
                    ref={containerRef} 
                    className="html-renderer-container"
                    style={{ display: showRaw ? 'none' : 'block' }}
                    onClick={(e) => e.stopPropagation()} // Stop bubble up to prevent clearing selection
                />

                {showRaw && (
                    <div className="html-renderer-container raw-mode" style={{ padding: 24 }}>
                        <pre style={{ 
                            margin: 0, 
                            padding: 16, 
                            backgroundColor: 'var(--color-bg-primary)', 
                            border: '1px solid var(--color-border)', 
                            borderRadius: 'var(--radius-md)', 
                            whiteSpace: 'pre-wrap', 
                            wordBreak: 'break-all', 
                            fontFamily: 'monospace', 
                            fontSize: '0.8rem', 
                            color: 'var(--color-text-primary)',
                            overflowX: 'auto',
                            lineHeight: 1.5,
                            userSelect: 'text'
                        }}>
                            {htmlContent}
                        </pre>
                    </div>
                )}

                {popoverCoords && selectionData && !showRaw && (
                    <AnnotationPopover 
                        selectionText={selectionData.text}
                        coords={popoverCoords}
                        onSave={handleSaveAnnotation}
                        onCancel={handleCancelAnnotation}
                    />
                )}

                {!showRaw && (
                    <div onClick={(e) => e.stopPropagation()}>
                        <FootnotePanel 
                            footnotes={footnotes} 
                            annotations={annotations}
                            onFootnoteSelect={handleFootnoteSelect}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};

// Helper: Maps plain text character offsets back to HTML DOM nodes
const createRangeFromOffsets = (container, startOffset, endOffset) => {
    const range = document.createRange();
    let currentOffset = 0;
    let startNode = null;
    let startCharOffset = 0;
    let endNode = null;
    let endCharOffset = 0;

    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
        const length = node.textContent.length;
        
        if (!startNode && currentOffset + length >= startOffset) {
            startNode = node;
            startCharOffset = startOffset - currentOffset;
        }
        if (!endNode && currentOffset + length >= endOffset) {
            endNode = node;
            endCharOffset = endOffset - currentOffset;
            break;
        }
        currentOffset += length;
    }

    if (startNode && endNode) {
        try {
            range.setStart(startNode, startCharOffset);
            range.setEnd(endNode, endCharOffset);
            return range;
        } catch (e) {
            console.error('Error setting range offsets:', e);
        }
    }
    return null;
};

export default HtmlPanel;
