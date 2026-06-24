import React, { useState, useEffect } from 'react';
import { Search, FileText, AlertTriangle, Trash2, CheckCircle } from 'lucide-react';
import { useUiStore } from '../../stores/uiStore';
import { useDocumentStore } from '../../stores/documentStore';
import { useReviewStore } from '../../stores/reviewStore';

const Sidebar = ({ documentId }) => {
    const { sidebarTab, setSidebarTab } = useUiStore();
    const { 
        sections, 
        activeSection, 
        fetchSection, 
        searchResults, 
        search, 
        clearSearch,
        loading 
    } = useDocumentStore();
    const { annotations, deleteAnnotation, setCurrentPage } = useReviewStore();
    
    const [localQuery, setLocalQuery] = useState('');

    // Trigger debounced search
    useEffect(() => {
        const delay = setTimeout(() => {
            if (localQuery.trim()) {
                search(documentId, localQuery);
            } else {
                clearSearch();
            }
        }, 300);

        return () => clearTimeout(delay);
    }, [localQuery, documentId, search, clearSearch]);

    const handleSectionClick = async (secId, startPage) => {
        const sec = await fetchSection(documentId, secId);
        const targetPage = startPage || sec?.start_page;
        if (sec && targetPage) {
            setCurrentPage(targetPage);
        }
    };

    // Construct TOC tree with headers
    const renderTocTree = () => {
        if (sections.length === 0) {
            return <div className="p-4" style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>No sections found.</div>;
        }

        let lastChapter = null;
        let lastPart = null;
        let lastDivision = null;
        
        const nodes = [];
        sections.forEach((sec) => {
            if (sec.chapter_code !== lastChapter) {
                lastChapter = sec.chapter_code;
                lastPart = null;
                lastDivision = null;
                nodes.push(
                    <div key={`ch-${sec.id}`} className="toc-node level-chapter">
                        {sec.chapter_code}: {sec.chapter_heading}
                    </div>
                );
            }
            if (sec.part_code && sec.part_code !== lastPart) {
                lastPart = sec.part_code;
                lastDivision = null;
                nodes.push(
                    <div key={`pt-${sec.id}`} className="toc-node level-part">
                        {sec.part_code}: {sec.part_heading}
                    </div>
                );
            }
            if (sec.division_code && sec.division_code !== lastDivision) {
                lastDivision = sec.division_code;
                nodes.push(
                    <div key={`div-${sec.id}`} className="toc-node level-division">
                        {sec.division_code}: {sec.division_heading}
                    </div>
                );
            }

            const isActive = activeSection?.id === sec.id;
            nodes.push(
                <div 
                    key={`sec-${sec.id}`} 
                    className={`toc-node level-section ${isActive ? 'active' : ''}`}
                    onClick={() => handleSectionClick(sec.id, sec.start_page)}
                >
                    <span className={`toc-node-status ${sec.review_status}`} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        Section {sec.section_code}: {sec.section_heading}
                    </span>
                    {sec.annotation_count > 0 && (
                        <span style={{ fontSize: '0.7rem', padding: '1px 5px', borderRadius: 4, backgroundColor: 'var(--color-error-light)', color: 'var(--color-error)', fontWeight: 700, marginLeft: 'auto' }}>
                            {sec.annotation_count}
                        </span>
                    )}
                </div>
            );
        });

        return <div className="toc-tree">{nodes}</div>;
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Tabs */}
            <div className="toc-tabs">
                <button 
                    className={`toc-tab ${sidebarTab === 'toc' ? 'active' : ''}`}
                    onClick={() => setSidebarTab('toc')}
                >
                    TOC
                </button>
                <button 
                    className={`toc-tab ${sidebarTab === 'search' ? 'active' : ''}`}
                    onClick={() => setSidebarTab('search')}
                >
                    Search
                </button>
                <button 
                    className={`toc-tab ${sidebarTab === 'annotations' ? 'active' : ''}`}
                    onClick={() => setSidebarTab('annotations')}
                >
                    Issues ({annotations.length})
                </button>
            </div>

            {/* Content */}
            <div className="toc-content">
                {sidebarTab === 'toc' && (
                    renderTocTree()
                )}

                {sidebarTab === 'search' && (
                    <div className="search-container flex flex-col gap-3">
                        <div className="flex align-center gap-2 p-2" style={{ backgroundColor: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}>
                            <Search size={16} style={{ color: 'var(--color-text-muted)' }} />
                            <input 
                                type="text"
                                placeholder="Search section text..."
                                value={localQuery}
                                onChange={(e) => setLocalQuery(e.target.value)}
                                style={{ background: 'transparent', border: 'none', width: '100%', fontSize: '0.85rem', color: 'var(--color-text-primary)' }}
                            />
                        </div>

                        {loading.search && <div className="p-4" style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Searching...</div>}
                        
                        <div className="search-results-list">
                            {!loading.search && searchResults.map(res => (
                                <div 
                                    key={res.section_id} 
                                    className="search-result-card"
                                    onClick={() => handleSectionClick(res.section_id)}
                                >
                                    <div className="search-result-title">
                                        Section {res.section_code}: {res.section_heading}
                                    </div>
                                    <div className="search-result-chapter">
                                        {res.chapter_code || 'Schedules'}
                                    </div>
                                    <div 
                                        className="search-result-snippet"
                                        dangerouslySetInnerHTML={{ __html: res.snippet }}
                                    />
                                </div>
                            ))}
                            {localQuery && !loading.search && searchResults.length === 0 && (
                                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: 12 }}>
                                    No matches found.
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {sidebarTab === 'annotations' && (
                    <div className="annotation-list">
                        <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>
                            Section Mismatches
                        </h4>
                        
                        {annotations.length === 0 ? (
                            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', padding: 12, textAlign: 'center' }}>
                                No issues reported for this section.
                            </div>
                        ) : (
                            annotations.map(a => (
                                <div key={a.id} className="annotation-card" data-severity={a.severity}>
                                    <button 
                                        className="annotation-delete-btn" 
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            deleteAnnotation(a.id);
                                        }}
                                        title="Delete annotation"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                    <div className="annotation-card-text">
                                        "{a.highlighted_text}"
                                    </div>
                                    <div className="annotation-card-description">
                                        {a.issue_description || 'No description'}
                                    </div>
                                    <div className="annotation-card-meta">
                                        <span style={{ fontWeight: 700 }}>{a.reviewer_name || 'QA'}</span>
                                        <span>{new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Sidebar;
