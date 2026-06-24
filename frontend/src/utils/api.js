const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = {
    async get(path) {
        const res = await fetch(`${API_BASE}${path}`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Network error' }));
            throw new Error(err.detail || 'API request failed');
        }
        return res.json();
    },

    async post(path, body, isMultipart = false) {
        const headers = {};
        if (!isMultipart) {
            headers['Content-Type'] = 'application/json';
        }
        const res = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers,
            body: isMultipart ? body : JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Network error' }));
            throw new Error(err.detail || 'API request failed');
        }
        return res.json();
    },

    async patch(path, body) {
        const res = await fetch(`${API_BASE}${path}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Network error' }));
            throw new Error(err.detail || 'API request failed');
        }
        return res.json();
    },

    async delete(path) {
        const res = await fetch(`${API_BASE}${path}`, {
            method: 'DELETE'
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Network error' }));
            throw new Error(err.detail || 'API request failed');
        }
        return res.status === 204 ? null : res.json();
    },
    
    getDownloadUrl(path) {
        return `${API_BASE}${path}`;
    },

    getFileUrl(filename) {
        return `${import.meta.env.VITE_STATIC_URL || 'http://localhost:8000'}/uploads/${filename}`;
    }
};
