import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../hooks/usePdfRenderer', () => ({
    usePdfDocument: () => ({
        pdfDoc: { id: 'pdf' },
        loading: false,
        error: null,
        numPages: 400,
    }),
    usePdfPageRenderer: () => ({ loading: false, error: null }),
}));

import PdfPanel from '../components/review/PdfPanel';
import { useDocumentStore } from '../stores/documentStore';
import { useReviewStore } from '../stores/reviewStore';
import { useUiStore } from '../stores/uiStore';

describe('section PDF rendering', () => {
    beforeEach(() => {
        useDocumentStore.setState({
            activeSection: { id: 'section-1', start_page: 1, end_page: 291 },
        });
        useReviewStore.setState({
            currentPage: 1,
            viewMode: 'section',
        });
        useUiStore.setState({ pdfZoom: 1 });
    });

    it('renders one canvas for a 291-page section and pages through the range', () => {
        const { container } = render(<PdfPanel pdfUrl="/uploads/large.pdf" />);

        expect(container.querySelectorAll('canvas')).toHaveLength(1);
        const selector = screen.getByRole('combobox', {
            name: 'PDF page within section',
        });
        expect(selector.querySelectorAll('option')).toHaveLength(291);

        fireEvent.change(selector, { target: { value: '291' } });

        expect(useReviewStore.getState().currentPage).toBe(291);
        expect(container.querySelectorAll('canvas')).toHaveLength(1);
    });
});
