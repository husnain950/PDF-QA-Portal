import { create } from 'zustand';
import { api } from '../utils/api';
import { useDocumentStore } from './documentStore';

export const useReviewStore = create((set, get) => ({
    annotations: [],
    viewMode: 'section', // 'section' | 'page'
    currentPage: 1,
    activeFootnoteId: null,

    fetchAnnotations: async (sectionId) => {
        try {
            const data = await api.get(`/sections/${sectionId}/annotations`);
            set({ annotations: data });
            return data;
        } catch (e) {
            console.error('Failed to fetch annotations', e);
            return [];
        }
    },

    createAnnotation: async (sectionId, annotationData) => {
        try {
            const res = await api.post(`/sections/${sectionId}/annotations`, {
                highlighted_text: annotationData.highlightedText,
                start_offset: annotationData.startOffset,
                end_offset: annotationData.endOffset,
                issue_description: annotationData.issueDescription,
                severity: annotationData.severity,
                reviewer_name: annotationData.reviewerName
            });

            // Update annotations in store
            set((state) => ({ annotations: [...state.annotations, res] }));

            // side effects: updates active section's review status
            const docStore = useDocumentStore.getState();
            if (docStore.activeSection && docStore.activeSection.id === sectionId) {
                // Set to has_issues
                docStore.fetchSection(docStore.activeDocument.id, sectionId);
                docStore.fetchSections(docStore.activeDocument.id);
            }
            return res;
        } catch (e) {
            console.error('Failed to create annotation', e);
            throw e;
        }
    },

    updateAnnotation: async (annotationId, updateData) => {
        try {
            const res = await api.patch(`/annotations/${annotationId}`, {
                issue_description: updateData.issueDescription,
                severity: updateData.severity
            });

            set((state) => ({
                annotations: state.annotations.map(a => a.id === annotationId ? res : a)
            }));
            return res;
        } catch (e) {
            console.error('Failed to update annotation', e);
            throw e;
        }
    },

    deleteAnnotation: async (annotationId) => {
        try {
            const annotations = get().annotations;
            const deleted = annotations.find(a => a.id === annotationId);
            
            await api.delete(`/annotations/${annotationId}`);
            
            set((state) => ({
                annotations: state.annotations.filter(a => a.id !== annotationId)
            }));

            // side effects: refresh section
            if (deleted) {
                const docStore = useDocumentStore.getState();
                docStore.fetchSection(docStore.activeDocument.id, deleted.section_id);
                docStore.fetchSections(docStore.activeDocument.id);
            }
        } catch (e) {
            console.error('Failed to delete annotation', e);
            throw e;
        }
    },

    updateFootnoteStatus: async (footnoteId, status) => {
        try {
            const res = await api.patch(`/footnotes/${footnoteId}/status`, {
                review_status: status
            });
            
            // Side effect: update active section footnotes directly in documentStore
            const docStore = useDocumentStore.getState();
            const activeSection = docStore.activeSection;
            if (activeSection && activeSection.footnotes) {
                const updatedFootnotes = activeSection.footnotes.map(fn => 
                    fn.id === footnoteId ? { ...fn, review_status: status } : fn
                );
                
                let newSectionStatus = activeSection.review_status;
                if (status === 'has_issues') {
                    newSectionStatus = 'has_issues';
                }

                docStore.setState({
                    activeSection: { 
                        ...activeSection, 
                        footnotes: updatedFootnotes,
                        review_status: newSectionStatus
                    }
                });
                
                // If it's a page section, update it as well
                const pageSections = docStore.pageSections;
                docStore.setState({
                    pageSections: pageSections.map(s => {
                        if (s.footnotes) {
                            return {
                                ...s,
                                review_status: status === 'has_issues' ? 'has_issues' : s.review_status,
                                footnotes: s.footnotes.map(fn => fn.id === footnoteId ? { ...fn, review_status: status } : fn)
                            };
                        }
                        return s;
                    })
                });

                // Also update the sidebar sections tree status
                if (status === 'has_issues') {
                    const sections = docStore.sections;
                    docStore.setState({
                        sections: sections.map(s => s.id === activeSection.id ? { ...s, review_status: 'has_issues' } : s)
                    });
                }
                
                docStore.fetchDocument(docStore.activeDocument.id);
            }
            return res;
        } catch (e) {
            console.error('Failed to update footnote status', e);
            throw e;
        }
    },

    setViewMode: (mode) => set({ viewMode: mode }),
    setCurrentPage: (page) => set({ currentPage: page })
}));
