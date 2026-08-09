/** Known parse-quality codes → human-readable reasons. */
const FLAG_REASONS = {
    missing_table:
        'Mentions a table but HTML has no <table>',
    footnote_glue:
        'Footnote digits appear glued into words (no proper cite markers)',
    wall_of_text:
        'Long body with almost no block structure (heading-only / wall of text)',
    heading_body_bleed:
        'Heading looks like body text bled into the heading',
};

/**
 * Normalize section.quality_flags from API shapes:
 * - JSON string
 * - array of string codes
 * - array of { code, reason|message }
 */
export function normalizeQualityFlags(raw) {
    let value = raw;
    if (value == null || value === '') return [];

    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (!trimmed) return [];
        try {
            value = JSON.parse(trimmed);
        } catch {
            return [{ code: trimmed, reason: humanReason(trimmed) }];
        }
    }

    if (!Array.isArray(value)) {
        if (typeof value === 'object' && value !== null) {
            value = [value];
        } else {
            return [];
        }
    }

    return value
        .map((entry) => {
            if (entry == null) return null;
            if (typeof entry === 'string') {
                const code = entry.trim();
                if (!code) return null;
                return { code, reason: humanReason(code) };
            }
            if (typeof entry === 'object') {
                const code = String(entry.code || entry.flag || '').trim();
                const reason = String(
                    entry.reason || entry.message || '',
                ).trim();
                if (!code && !reason) return null;
                return {
                    code: code || 'quality',
                    reason: reason || humanReason(code || 'quality'),
                };
            }
            return null;
        })
        .filter(Boolean);
}

export function humanReason(code) {
    return FLAG_REASONS[code] || `Parse quality issue: ${code}`;
}

export function hasCriticalQualityFlags(raw) {
    return normalizeQualityFlags(raw).length > 0;
}

export function formatQualityFlagList(raw) {
    return normalizeQualityFlags(raw).map((f) => f.reason);
}
