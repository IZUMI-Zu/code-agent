import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import NavigationBar from '../components/NavigationBar';
import PaperList from '../components/PaperList';
import arxivService from '../services/arxivService';
import type { ArxivPaper } from '../services/arxivService';

const HomePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [papers, setPapers] = useState<ArxivPaper[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(
    searchParams.get('category')
  );
  const [searchQuery, setSearchQuery] = useState<string>(
    searchParams.get('search') || ''
  );
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchPapers = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      let response;
      
      if (searchQuery) {
        // Search by query
        response = await arxivService.fetchPapers({
          searchQuery: `all:${searchQuery}`,
          maxResults: 50,
          sortBy: 'relevance',
          sortOrder: 'descending'
        });
      } else if (selectedCategory) {
        // Filter by category
        response = await arxivService.fetchPapersByCategory(selectedCategory, 50);
      } else {
        // Get latest papers
        response = await arxivService.fetchLatestPapers(50);
      }

      setPapers(response.papers);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error fetching papers:', err);
      setError(err instanceof Error ? err.message : 'Failed to load papers. Please try again.');
      setPapers([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, searchQuery]);

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedCategory) {
      params.set('category', selectedCategory);
    }
    if (searchQuery) {
      params.set('search', searchQuery);
    }
    setSearchParams(params);
  }, [selectedCategory, searchQuery, setSearchParams]);

  // Fetch papers when filters change
  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  const handleCategoryChange = (category: string | null) => {
    setSelectedCategory(category);
    setSearchQuery(''); // Clear search when changing category
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setSelectedCategory(null); // Clear category when searching
  };

  const handlePaperClick = (paper: ArxivPaper) => {
    // Track paper views or other analytics could go here
    console.log('Paper clicked:', paper.id);
  };

  const handleRefresh = () => {
    arxivService.clearCache();
    fetchPapers();
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <NavigationBar
        selectedCategory={selectedCategory || undefined}
        onCategoryChange={handleCategoryChange}
        onSearch={handleSearch}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {searchQuery ? (
                  <>Search Results for "{searchQuery}"</>
                ) : selectedCategory ? (
                  <>Latest in {selectedCategory.replace('cs.', '').toUpperCase()}</>
                ) : (
                  <>Latest Computer Science Papers</>
                )}
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                {searchQuery
                  ? 'Papers matching your search query'
                  : selectedCategory
                  ? 'Latest preprints in this category'
                  : 'Daily updated preprints from arXiv Computer Science'}
              </p>
            </div>

            <div className="flex items-center space-x-4">
              {lastUpdated && (
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              )}
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg
                  className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Refresh
              </button>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {isLoading ? '...' : papers.length}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Papers Found</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {isLoading ? '...' : new Set(papers.flatMap(p => p.categories)).size}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Categories</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {isLoading ? '...' : new Set(papers.flatMap(p => p.authors)).size}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">Authors</div>
            </div>
          </div>
        </div>

        {/* Paper List */}
        <PaperList
          papers={papers}
          isLoading={isLoading}
          error={error}
          onPaperClick={handlePaperClick}
        />

        {/* Footer note */}
        {!isLoading && !error && papers.length > 0 && (
          <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
            <p>
              Showing {papers.length} papers • Data sourced from{' '}
              <a
                href="https://arxiv.org"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                arXiv.org
              </a>
              {' • '}
              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                Back to top
              </button>
            </p>
            <p className="mt-1 text-xs">
              Papers are updated daily. Click on any paper title to view detailed information.
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

export default HomePage;