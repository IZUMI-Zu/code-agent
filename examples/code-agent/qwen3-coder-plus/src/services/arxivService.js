import { parseArxivPapers, formatPaper } from '../utils/arxivParser';

// Base URL for the arXiv API (using proxy to avoid CORS issues)
const ARXIV_API_BASE = `${import.meta.env.VITE_API_BASE_URL || '/api'}/query`;

// Default search parameters
const DEFAULT_PARAMS = {
  search_query: 'cat:cs.AI OR cat:cs.LG OR cat:cs.CV OR cat:cs.CL',
  sortBy: 'submittedDate',
  sortOrder: 'descending',
  max_results: 50
};

/**
 * Builds a query string from parameters
 * @param {Object} params - Query parameters
 * @returns {string} - Encoded query string
 */
const buildQueryString = (params) => {
  return Object.keys(params)
    .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
};

/**
 * Fetches papers from the arXiv API
 * @param {Object} options - Search options
 * @returns {Promise<Array>} - Promise resolving to array of formatted papers
 */
export const fetchPapers = async (options = {}) => {
  const params = { ...DEFAULT_PARAMS, ...options };
  const queryString = buildQueryString(params);
  const url = `${ARXIV_API_BASE}?${queryString}`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch papers: ${response.status}`);
    }

    const xmlText = await response.text();
    const papers = parseArxivPapers(xmlText);

    // Format papers for display
    return papers.map(formatPaper);
  } catch (error) {
    console.error('Error fetching papers:', error);
    throw error;
  }
};

/**
 * Fetches papers for a specific computer science domain
 * @param {string} domain - The cs domain (e.g., 'AI', 'LG', 'CV', 'CL')
 * @param {number} maxResults - Maximum number of results to return
 * @returns {Promise<Array>} - Promise resolving to array of formatted papers
 */
export const fetchPapersByDomain = async (domain, maxResults = 50) => {
  const options = {
    search_query: `cat:cs.${domain}`,
    max_results: maxResults
  };

  return await fetchPapers(options);
};

/**
 * Fetches papers for a specific computer science category
 * @param {string} categoryId - The cs category ID (e.g., 'cs.AI', 'cs.LG', 'cs.CV', 'cs.CL')
 * @param {number} maxResults - Maximum number of results to return
 * @returns {Promise<Array>} - Promise resolving to array of formatted papers
 */
export const fetchPapersByCategory = async (categoryId, maxResults = 50) => {
  const options = {
    search_query: `cat:${categoryId}`,
    max_results: maxResults
  };

  return await fetchPapers(options);
};

/**
 * Searches papers by keyword
 * @param {string} keyword - Search keyword
 * @param {number} maxResults - Maximum number of results to return
 * @returns {Promise<Array>} - Promise resolving to array of formatted papers
 */
export const searchPapers = async (keyword, maxResults = 50) => {
  const options = {
    search_query: `all:${keyword}`,
    max_results: maxResults
  };

  return await fetchPapers(options);
};

/**
 * Fetches details for a specific paper
 * @param {string} paperId - The arXiv paper ID
 * @returns {Promise<Object>} - Promise resolving to formatted paper object
 */
export const fetchPaperDetails = async (paperId) => {
  const params = {
    id_list: paperId,
    max_results: 1
  };
  const queryString = buildQueryString(params);
  const url = `${ARXIV_API_BASE}?${queryString}`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch paper details: ${response.status}`);
    }

    const xmlText = await response.text();
    const papers = parseArxivPapers(xmlText);

    // Format papers for display
    return papers.length > 0 ? formatPaper(papers[0]) : null;
  } catch (error) {
    console.error('Error fetching paper details:', error);
    throw error;
  }
};