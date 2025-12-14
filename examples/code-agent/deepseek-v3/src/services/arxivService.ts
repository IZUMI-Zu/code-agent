import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001/api';

export interface ArxivPaper {
  id: string;
  title: string;
  summary: string;
  authors: string[];
  categories: string[];
  published: string;
  updated: string;
  pdfUrl: string;
  doi?: string;
  comment?: string;
  journalRef?: string;
}

export interface ArxivResponse {
  papers: ArxivPaper[];
  totalResults: number;
  startIndex: number;
  itemsPerPage: number;
}

export class ArxivService {
  private static instance: ArxivService;
  private cache: Map<string, { data: ArxivResponse; timestamp: number }> = new Map();
  private CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

  private constructor() {}

  public static getInstance(): ArxivService {
    if (!ArxivService.instance) {
      ArxivService.instance = new ArxivService();
    }
    return ArxivService.instance;
  }

  private getCacheKey(params: Record<string, any>): string {
    return JSON.stringify(params);
  }

  private isCacheValid(cacheKey: string): boolean {
    const cached = this.cache.get(cacheKey);
    if (!cached) return false;
    
    const now = Date.now();
    return now - cached.timestamp < this.CACHE_DURATION;
  }

  async fetchPapers(params: {
    searchQuery?: string;
    category?: string;
    start?: number;
    maxResults?: number;
    sortBy?: 'relevance' | 'lastUpdatedDate' | 'submittedDate';
    sortOrder?: 'ascending' | 'descending';
  } = {}): Promise<ArxivResponse> {
    const {
      searchQuery = 'cat:cs.*',
      category,
      start = 0,
      maxResults = 50,
      sortBy = 'submittedDate',
      sortOrder = 'descending'
    } = params;

    // Build search query
    let query = searchQuery;
    if (category && !searchQuery.includes(category)) {
      query = `cat:${category}`;
    }

    const cacheKey = this.getCacheKey({ query, start, maxResults, sortBy, sortOrder });
    
    // Check cache
    if (this.isCacheValid(cacheKey)) {
      console.log('Returning cached data');
      return this.cache.get(cacheKey)!.data;
    }

    try {
      const response = await axios.get(`${API_BASE_URL}/arxiv`, {
        params: {
          search_query: query,
          start,
          max_results: maxResults,
          sortBy,
          sortOrder
        }
      });

      // Parse XML response using DOMParser (browser-compatible)
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(response.data as string, 'text/xml');
      
      // Get entries
      const entries = xmlDoc.getElementsByTagName('entry');
      const papers: ArxivPaper[] = [];
      
      for (let i = 0; i < entries.length; i++) {
        const entry = entries[i];
        
        // Extract data from XML nodes
        const idElement = entry.getElementsByTagName('id')[0];
        const titleElement = entry.getElementsByTagName('title')[0];
        const summaryElement = entry.getElementsByTagName('summary')[0];
        const publishedElement = entry.getElementsByTagName('published')[0];
        const updatedElement = entry.getElementsByTagName('updated')[0];
        
        // Extract authors
        const authorElements = entry.getElementsByTagName('author');
        const authors: string[] = [];
        for (let j = 0; j < authorElements.length; j++) {
          const nameElement = authorElements[j].getElementsByTagName('name')[0];
          if (nameElement) {
            authors.push(nameElement.textContent || '');
          }
        }
        
        // Extract categories
        const categoryElements = entry.getElementsByTagName('category');
        const categories: string[] = [];
        for (let j = 0; j < categoryElements.length; j++) {
          const term = categoryElements[j].getAttribute('term');
          if (term) {
            categories.push(term);
          }
        }
        
        // Extract arXiv-specific fields
        const doiElement = entry.getElementsByTagName('arxiv:doi')[0];
        const commentElement = entry.getElementsByTagName('arxiv:comment')[0];
        const journalRefElement = entry.getElementsByTagName('arxiv:journal_ref')[0];
        
        const id = idElement?.textContent?.split('/').pop()?.split('v')[0] || '';
        
        papers.push({
          id,
          title: titleElement?.textContent?.replace(/\n/g, ' ').trim() || '',
          summary: summaryElement?.textContent?.replace(/\n/g, ' ').trim() || '',
          authors,
          categories,
          published: publishedElement?.textContent || '',
          updated: updatedElement?.textContent || '',
          pdfUrl: `https://arxiv.org/pdf/${id}.pdf`,
          doi: doiElement?.textContent || undefined,
          comment: commentElement?.textContent || undefined,
          journalRef: journalRefElement?.textContent || undefined
        });
      }

      // Extract pagination info
      const totalResultsElement = xmlDoc.getElementsByTagName('opensearch:totalResults')[0];
      const startIndexElement = xmlDoc.getElementsByTagName('opensearch:startIndex')[0];
      const itemsPerPageElement = xmlDoc.getElementsByTagName('opensearch:itemsPerPage')[0];
      
      const totalResults = parseInt(totalResultsElement?.textContent || '0', 10);
      const startIndex = parseInt(startIndexElement?.textContent || '0', 10);
      const itemsPerPage = parseInt(itemsPerPageElement?.textContent || '50', 10);

      const result: ArxivResponse = {
        papers,
        totalResults,
        startIndex,
        itemsPerPage
      };

      // Cache the result
      this.cache.set(cacheKey, {
        data: result,
        timestamp: Date.now()
      });

      return result;
    } catch (error) {
      console.error('Error fetching papers from arXiv:', error);
      throw new Error('Failed to fetch papers from arXiv API');
    }
  }

  async fetchPaperById(paperId: string): Promise<ArxivPaper | null> {
    try {
      const response = await this.fetchPapers({
        searchQuery: `id:${paperId}`,
        maxResults: 1
      });

      return response.papers[0] || null;
    } catch (error) {
      console.error(`Error fetching paper ${paperId}:`, error);
      return null;
    }
  }

  async fetchPapersByCategory(category: string, maxResults: number = 50): Promise<ArxivResponse> {
    return this.fetchPapers({
      category,
      maxResults
    });
  }

  async fetchLatestPapers(maxResults: number = 50): Promise<ArxivResponse> {
    return this.fetchPapers({
      searchQuery: 'cat:cs.*',
      maxResults,
      sortBy: 'submittedDate',
      sortOrder: 'descending'
    });
  }

  clearCache(): void {
    this.cache.clear();
  }
}

export default ArxivService.getInstance();