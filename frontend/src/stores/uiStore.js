import { create } from 'zustand';

const getInitialTheme = () => {
    if (typeof window !== 'undefined') {
        const storedTheme = localStorage.getItem('qa-portal-theme');
        if (storedTheme) return storedTheme;
        
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        return systemPrefersDark ? 'dark' : 'light';
    }
    return 'light';
};

export const useUiStore = create((set) => {
    // Set initial theme in DOM
    const initialTheme = getInitialTheme();
    if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', initialTheme);
    }

    return {
        theme: initialTheme,
        sidebarOpen: true,
        sidebarTab: 'toc', // 'toc' | 'search' | 'annotations'
        splitRatio: 0.5,
        pdfZoom: 1.0,

        toggleTheme: () => set((state) => {
            const newTheme = state.theme === 'light' ? 'dark' : 'light';
            localStorage.setItem('qa-portal-theme', newTheme);
            document.documentElement.setAttribute('data-theme', newTheme);
            return { theme: newTheme };
        }),

        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setSidebarTab: (tab) => set({ sidebarTab: tab }),
        setSplitRatio: (ratio) => set({ splitRatio: ratio }),
        setPdfZoom: (zoom) => set({ pdfZoom: zoom }),
        zoomIn: () => set((state) => ({ pdfZoom: Math.min(3.0, state.pdfZoom + 0.25) })),
        zoomOut: () => set((state) => ({ pdfZoom: Math.max(0.5, state.pdfZoom - 0.25) })),
        resetZoom: () => set({ pdfZoom: 1.0 })
    };
});
