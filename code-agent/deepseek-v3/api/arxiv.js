const axios = require('axios');

const ARXIV_API_BASE = 'http://export.arxiv.org/api/query';

module.exports = async (req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  // Handle OPTIONS request for CORS preflight
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // Only allow GET requests
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    const { search_query, start, max_results, sortBy, sortOrder } = req.query;
    
    // Default parameters for CS papers
    const defaultParams = {
      search_query: search_query || 'cat:cs.*',
      start: start || 0,
      max_results: max_results || 50,
      sortBy: sortBy || 'submittedDate',
      sortOrder: sortOrder || 'descending'
    };

    // Build arXiv API URL
    const params = new URLSearchParams(defaultParams);
    const arxivUrl = `${ARXIV_API_BASE}?${params.toString()}`;

    // Fetch from arXiv API
    const response = await axios.get(arxivUrl, {
      headers: {
        'Accept': 'application/xml'
      }
    });

    // Return the XML response
    res.setHeader('Content-Type', 'application/xml');
    res.status(200).send(response.data);
  } catch (error) {
    console.error('Error fetching from arXiv API:', error.message);
    res.status(500).json({ 
      error: 'Failed to fetch data from arXiv API',
      details: error.message 
    });
  }
};