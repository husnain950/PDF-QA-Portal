import { useState, useEffect } from 'react';

export const getSelectionCharacterOffsetsWithin = (element) => {
    let start = 0;
    let end = 0;
    const sel = window.getSelection();
    if (sel.rangeCount > 0) {
        const range = sel.getRangeAt(0);
        const preCaretRange = range.cloneRange();
        preCaretRange.selectNodeContents(element);
        preCaretRange.setEnd(range.startContainer, range.startOffset);
        start = preCaretRange.toString().length;
        end = start + range.toString().length;
    }
    return { start, end };
};

export const useTextSelection = (containerRef, onSelectionComplete) => {
    const [selectedText, setSelectedText] = useState('');
    const [selectionCoords, setSelectionCoords] = useState(null);
    const [offsets, setOffsets] = useState({ start: 0, end: 0 });

    useEffect(() => {
        const handleMouseUp = (e) => {
            const container = containerRef.current;
            if (!container) return;

            const selection = window.getSelection();
            if (!selection.rangeCount || selection.isCollapsed) {
                // Clear selection
                setSelectedText('');
                setSelectionCoords(null);
                return;
            }

            const range = selection.getRangeAt(0);
            
            // Check if selection is within the container
            if (!container.contains(range.commonAncestorContainer)) {
                return;
            }

            const text = selection.toString().trim();
            if (!text) return;

            // Calculate offsets
            const { start, end } = getSelectionCharacterOffsetsWithin(container);
            
            // Get position of selection to place the popover
            const rect = range.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            
            // Calculate coords relative to container
            const coords = {
                top: rect.bottom - containerRect.top + container.scrollTop + 8,
                left: rect.left - containerRect.left + container.scrollLeft + (rect.width / 2) - 160 // Center popover
            };

            setSelectedText(text);
            setOffsets({ start, end });
            setSelectionCoords(coords);

            if (onSelectionComplete) {
                onSelectionComplete({ text, start, end, coords });
            }
        };

        const handleMouseDown = () => {
            // Keep existing selection intact until mouseup
        };

        const container = containerRef.current;
        if (container) {
            container.addEventListener('mouseup', handleMouseUp);
            container.addEventListener('mousedown', handleMouseDown);
        }

        return () => {
            if (container) {
                container.removeEventListener('mouseup', handleMouseUp);
                container.removeEventListener('mousedown', handleMouseDown);
            }
        };
    }, [containerRef, onSelectionComplete]);

    const clearSelection = () => {
        window.getSelection().removeAllRanges();
        setSelectedText('');
        setSelectionCoords(null);
    };

    return { selectedText, selectionCoords, offsets, clearSelection };
};
