import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sun, Moon, ArrowLeft, PanelLeftClose, PanelLeftOpen, BookOpen } from 'lucide-react';
import { useUiStore } from '../../stores/uiStore';

const AppShell = ({ 
    children, 
    title, 
    showBackButton = false, 
    sidebarContent = null, 
    actions = null,
    scrollable = false
}) => {
    const navigate = useNavigate();
    const { theme, toggleTheme, sidebarOpen, toggleSidebar } = useUiStore();

    return (
        <div className="app-shell">
            {/* Top Bar */}
            <header className="top-bar glass-panel">
                <div className="flex align-center gap-4">
                    {showBackButton && (
                        <button 
                            className="btn btn-secondary btn-icon" 
                            onClick={() => navigate('/')}
                            title="Back to Dashboard"
                        >
                            <ArrowLeft size={18} />
                        </button>
                    )}
                    {sidebarContent && (
                        <button 
                            className="btn btn-secondary btn-icon" 
                            onClick={toggleSidebar}
                            title={sidebarOpen ? "Hide Navigation Sidebar" : "Show Navigation Sidebar"}
                        >
                            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
                        </button>
                    )}
                    <div className="brand" onClick={() => navigate('/')}>
                        <BookOpen size={22} strokeWidth={2.5} />
                        <span>PDF-QA Portal</span>
                    </div>
                    {title && (
                        <div style={{ marginLeft: 24, fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                            {title}
                        </div>
                    )}
                </div>

                <div className="flex align-center gap-3">
                    {actions}
                    <button 
                        className="btn btn-secondary btn-icon" 
                        onClick={toggleTheme}
                        title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
                    >
                        {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
                    </button>
                </div>
            </header>

            {/* Main Area */}
            <div className="workspace-container">
                {sidebarContent && (
                    <aside className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
                        {sidebarContent}
                    </aside>
                )}
                <main className={`main-content ${scrollable ? 'scrollable' : ''}`}>
                    {children}
                </main>
            </div>
        </div>
    );
};

export default AppShell;
