const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// arXiv API base URL
const ARXIV_API_BASE = 'http://export.arxiv.org/api/query';

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'arXiv CS Daily API proxy is running' });
});

// arXiv API proxy endpoint
app.get('/api/arxiv', async (req, res) => {
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
    res.set('Content-Type', 'application/xml');
    res.send(response.data);
  } catch (error) {
    console.error('Error fetching from arXiv API:', error.message);
    res.status(500).json({ 
      error: 'Failed to fetch data from arXiv API',
      details: error.message 
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`arXiv CS Daily API proxy server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
  console.log(`arXiv proxy: http://localhost:${PORT}/api/arxiv`);
});