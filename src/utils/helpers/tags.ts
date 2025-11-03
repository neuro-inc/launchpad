/**
 * Utility functions for handling tags
 */

/**
 * Helper function to convert comma-separated tags string to array
 */
export const parseTags = (tags: string | null | undefined): string[] | null => {
  if (!tags || tags.trim() === '') return null;
  return tags
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
};

/**
 * Helper function to convert tags array to comma-separated string
 */
export const tagsToString = (tags: string[] | null | undefined): string => {
  if (!tags || tags.length === 0) return '';
  return tags.join(', ');
};
