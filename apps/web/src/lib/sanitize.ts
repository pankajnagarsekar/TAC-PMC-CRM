import DOMPurify from 'dompurify';

/**
 * Strips all HTML tags from a string.
 * Use this for fields like names, descriptions, etc. where NO HTML is expected.
 */
export function sanitizeText(input: string): string {
    if (!input) return '';
    // Force string and trim
    let str = String(input).trim();
    // Aggressive JS stripping: remove common execution patterns
    str = str.replace(/(alert|eval|prompt|confirm|javascript:)\s*\(.*\)/gi, '[REDACTED]');
    str = str.replace(/on\w+\s*=.*(?=\s|>|$)/gi, ''); // event handlers
    // Strip all tags
    const clean = DOMPurify.sanitize(str, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] });
    // Decode entities to get pure text
    return clean.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

/**
 * Sanitizes HTML for safe display while allowing basic formatting.
 * Use this for fields that intentionally support some Markdown/HTML if any.
 */
export function sanitizeHTML(input: string): string {
    if (!input) return '';
    return DOMPurify.sanitize(input, {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
        ALLOWED_ATTR: ['href', 'target', 'rel']
    });
}
