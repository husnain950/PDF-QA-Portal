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
        // Stored names are relative to the uploads root ("pdf/<sha256>.pdf"), which the
        // static mount serves as a subpath. Each segment is encoded separately so the
        // slash survives while spaces in any legacy flat name do not.
        const encoded = String(filename || '')
            .split('/')
            .map(encodeURIComponent)
            .join('/');
        return `${import.meta.env.VITE_STATIC_URL || 'http://localhost:8000'}/uploads/${encoded}`;
    }
};

/** JSON versions of a document. The PDF is static; only the parse is versioned. */
export const versionsApi = {
    list(documentId) {
        return api.get(`/documents/${documentId}/versions`);
    },

    create(documentId, file, { note, reviewerName } = {}) {
        const form = new FormData();
        form.append('json_file', file);
        if (note) form.append('note', note);
        if (reviewerName) form.append('reviewer_name', reviewerName);
        return api.post(`/documents/${documentId}/versions`, form, true);
    },

    activate(documentId, versionId) {
        return api.post(
            `/documents/${documentId}/versions/${versionId}/activate`,
            {},
        );
    },

    diff(documentId, versionId, againstId) {
        const query = againstId ? `?against=${encodeURIComponent(againstId)}` : '';
        return api.get(`/documents/${documentId}/versions/${versionId}/diff${query}`);
    },
};
