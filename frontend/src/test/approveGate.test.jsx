import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import ReviewToolbar from '../components/review/ReviewToolbar';
import HtmlPanel from '../components/review/HtmlPanel';
import { useDocumentStore } from '../stores/documentStore';
import { useReviewStore } from '../stores/reviewStore';

describe('approve gate + quality banner', () => {
    beforeEach(() => {
        useReviewStore.setState({
            annotations: [],
            currentPage: 1,
            viewMode: 'section',
            fetchAnnotations: vi.fn().mockResolvedValue([]),
        });
        useDocumentStore.setState({
            activeDocument: { id: 'doc-1' },
            sections: [
                { id: 'sec-1', review_status: 'has_issues' },
                { id: 'sec-2', review_status: 'pending' },
            ],
            activeSection: {
                id: 'sec-1',
                review_status: 'has_issues',
                quality_flags: [
                    { code: 'missing_table', reason: 'Mentions a table but HTML has no <table>' },
                    'footnote_glue',
                ],
                html_content: '<p>body</p>',
                plain_text: 'body',
            },
            loading: { activeSection: false },
            updateSectionStatus: vi.fn().mockResolvedValue(undefined),
        });
        vi.restoreAllMocks();
    });

    it('shows a banner listing quality flag reasons', () => {
        const section = useDocumentStore.getState().activeSection;
        render(
            <HtmlPanel
                section={section}
                sectionId={section.id}
                htmlContent={section.html_content}
                footnotes={[]}
            />,
        );

        const banner = screen.getByTestId('quality-flags-banner');
        expect(banner).toHaveTextContent(/Mentions a table/i);
        expect(banner).toHaveTextContent(/Footnote digits appear glued/i);
    });

    it('requires confirm before approving a quality-flagged section', async () => {
        const updateSectionStatus = vi.fn().mockResolvedValue(undefined);
        useDocumentStore.setState({ updateSectionStatus });

        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

        render(
            <MemoryRouter>
                <ReviewToolbar />
            </MemoryRouter>,
        );

        expect(screen.getByText('flagged')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: /Approve/i }));

        expect(confirmSpy).toHaveBeenCalledOnce();
        expect(confirmSpy.mock.calls[0][0]).toMatch(/Override parse-quality flags/i);
        expect(updateSectionStatus).not.toHaveBeenCalled();
    });

    it('approves after confirm override', async () => {
        const updateSectionStatus = vi.fn().mockResolvedValue(undefined);
        useDocumentStore.setState({ updateSectionStatus });
        vi.spyOn(window, 'confirm').mockReturnValue(true);

        render(
            <MemoryRouter>
                <ReviewToolbar />
            </MemoryRouter>,
        );

        fireEvent.click(screen.getByRole('button', { name: /Approve/i }));

        expect(updateSectionStatus).toHaveBeenCalledWith('doc-1', 'sec-1', 'approved');
    });

    it('approves silently when there are no quality flags', async () => {
        const updateSectionStatus = vi.fn().mockResolvedValue(undefined);
        useDocumentStore.setState({
            updateSectionStatus,
            activeSection: {
                id: 'sec-1',
                review_status: 'pending',
                quality_flags: [],
            },
        });
        const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

        render(
            <MemoryRouter>
                <ReviewToolbar />
            </MemoryRouter>,
        );

        fireEvent.click(screen.getByRole('button', { name: /Approve/i }));

        expect(confirmSpy).not.toHaveBeenCalled();
        expect(updateSectionStatus).toHaveBeenCalledWith('doc-1', 'sec-1', 'approved');
    });
});
