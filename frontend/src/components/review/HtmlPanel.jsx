import React, { useRef, useEffect, useState } from 'react';
import { useTextSelection } from '../../hooks/useTextSelection';
import { useReviewStore } from '../../stores/reviewStore';
import AnnotationPopover from '../annotations/AnnotationPopover';
import FootnotePanel from '../footnotes/FootnotePanel';

const HtmlPanel = ({ sectionId, htmlContent, footnotes }) => {
    const containerRef = useRef(null);
    const { annotations, createAnnotation, fetchAnnotations } = useReviewStore();
    const [popoverCoords, setPopoverCoords] = useState(null);
    const [selectionData, setSelectionData] = useState(null);

    // Fetch annotations whenever section changes
    useEffect(() => {
        if (sectionId) {
            fetchAnnotations(sectionId);
        }
    }, [sectionId, fetchAnnotations]);

    // Listen to text selections
    const { clearSelection } = useTextSelection(containerRef, (data) => {
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

    return (
        <div className="flex flex-col height-100" style={{ height: '100%' }} onClick={handleCancelAnnotation}>
            <div className="panel-header glass-panel">
                <span className="panel-title">Parsed HTML Content</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                    Highlight text in this pane to report discrepancies
                </span>
            </div>

            <div className="panel-body" style={{ position: 'relative' }}>
                <div 
                    ref={containerRef} 
                    className="html-renderer-container"
                    onClick={(e) => e.stopPropagation()} // Stop bubble up to prevent clearing selection
                />

                {popoverCoords && selectionData && (
                    <AnnotationPopover 
                        selectionText={selectionData.text}
                        coords={popoverCoords}
                        onSave={handleSaveAnnotation}
                        onCancel={handleCancelAnnotation}
                    />
                )}

                <div onClick={(e) => e.stopPropagation()}>
                    <FootnotePanel 
                        footnotes={footnotes} 
                        annotations={annotations}
                        onFootnoteSelect={handleFootnoteSelect}
                    />
                </div>
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
