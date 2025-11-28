import axios from 'axios';

// Use Vite proxy in development, direct API in production
const ARXIV_API_BASE = import.meta.env.DEV 
  ? '/api/arxiv'  // Vite proxy endpoint
  : 'https://export.arxiv.org/api/query';  // Direct API for production

/**
 * Parse arXiv API XML response to JSON
 */
const parseArxivXML = (xmlText) => {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
  
  const entries = xmlDoc.querySelectorAll('entry');
  const papers = [];

  entries.forEach(entry => {
    const id = entry.querySelector('id')?.textContent || '';
    const arxivId = id.split('/abs/')[1] || '';
    
    const title = entry.querySelector('title')?.textContent?.trim().replace(/\s+/g, ' ') || '';
    const summary = entry.querySelector('summary')?.textContent?.trim().replace(/\s+/g, ' ') || '';
    const published = entry.querySelector('published')?.textContent || '';
    const updated = entry.querySelector('updated')?.textContent || '';
    
    // Extract authors
    const authorNodes = entry.querySelectorAll('author');
    const authors = Array.from(authorNodes).map(author => {
      const name = author.querySelector('name')?.textContent || '';
      const affiliation = author.querySelector('arxiv\\:affiliation, affiliation')?.textContent || '';
      return { name, affiliation };
    });

    // Extract categories
    const categoryNodes = entry.querySelectorAll('category');
    const categories = Array.from(categoryNodes).map(cat => cat.getAttribute('term'));

    // Extract primary category
    const primaryCategory = entry.querySelector('arxiv\\:primary_category, primary_category')?.getAttribute('term') || '';

    // Extract PDF link
    const links = entry.querySelectorAll('link');
    let pdfLink = '';
    links.forEach(link => {
      if (link.getAttribute('title') === 'pdf') {
        pdfLink = link.getAttribute('href');
      }
    });

    papers.push({
      id: arxivId,
      title,
      summary,
      published,
      updated,
      authors,
      categories,
      primaryCategory,
      pdfLink,
      abstractLink: id,
    });
  });

  return papers;
};

/**
 * Fetch papers by category
 * @param {string} category - arXiv category (e.g., 'cs.AI')
 * @param {number} maxResults - Maximum number of results to return
 * @param {number} start - Starting index for pagination
 */
export const fetchPapersByCategory = async (category, maxResults = 50, start = 0) => {
  try {
    const searchQuery = category === 'all' ? 'cat:cs.*' : `cat:${category}`;
    const params = new URLSearchParams({
      search_query: searchQuery,
      start: start.toString(),
      max_results: maxResults.toString(),
      sortBy: 'submittedDate',
      sortOrder: 'descending',
    });

    const url = `${ARXIV_API_BASE}?${params.toString()}`;

    const response = await axios.get(url, {
      timeout: 15000, // 15 second timeout
      headers: {
        'Accept': 'application/xml',
      },
    });
    
    const papers = parseArxivXML(response.data);
    return papers;
  } catch (error) {
    console.error('Error fetching papers:', error);
    
    // Provide more specific error messages
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - arXiv API is taking too long to respond');
    } else if (error.response) {
      throw new Error(`arXiv API error: ${error.response.status}`);
    } else if (error.request) {
      throw new Error('Network error - please check your internet connection');
    } else {
      throw new Error('Failed to fetch papers from arXiv API');
    }
  }
};

/**
 * Fetch a single paper by arXiv ID
 * @param {string} arxivId - arXiv paper ID (e.g., '2301.12345')
 */
export const fetchPaperById = async (arxivId) => {
  try {
    const params = new URLSearchParams({
      id_list: arxivId,
    });

    const url = `${ARXIV_API_BASE}?${params.toString()}`;

    const response = await axios.get(url, {
      timeout: 15000,
      headers: {
        'Accept': 'application/xml',
      },
    });
    
    const papers = parseArxivXML(response.data);
    
    if (papers.length === 0) {
      throw new Error('Paper not found');
    }

    return papers[0];
  } catch (error) {
    console.error('Error fetching paper:', error);
    
    if (error.message === 'Paper not found') {
      throw error;
    } else if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - arXiv API is taking too long to respond');
    } else if (error.response) {
      throw new Error(`arXiv API error: ${error.response.status}`);
    } else if (error.request) {
      throw new Error('Network error - please check your internet connection');
    } else {
      throw new Error('Failed to fetch paper from arXiv API');
    }
  }
};

/**
 * Search papers by query string
 * @param {string} query - Search query
 * @param {number} maxResults - Maximum number of results
 */
export const searchPapers = async (query, maxResults = 50) => {
  try {
    const params = new URLSearchParams({
      search_query: query,
      max_results: maxResults.toString(),
      sortBy: 'submittedDate',
      sortOrder: 'descending',
    });

    const url = `${ARXIV_API_BASE}?${params.toString()}`;

    const response = await axios.get(url, {
      timeout: 15000,
      headers: {
        'Accept': 'application/xml',
      },
    });
    
    const papers = parseArxivXML(response.data);
    return papers;
  } catch (error) {
    console.error('Error searching papers:', error);
    
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - arXiv API is taking too long to respond');
    } else if (error.response) {
      throw new Error(`arXiv API error: ${error.response.status}`);
    } else if (error.request) {
      throw new Error('Network error - please check your internet connection');
    } else {
      throw new Error('Failed to search papers from arXiv API');
    }
  }
};
