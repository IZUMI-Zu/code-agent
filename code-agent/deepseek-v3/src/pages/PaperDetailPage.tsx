import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import NavigationBar from '../components/NavigationBar';
import CitationTools from '../components/CitationTools';
import arxivService from '../services/arxivService';
import type { ArxivPaper } from '../services/arxivService';
import { getCategoryName, getMainCategory } from '../utils/categories';

const PaperDetailPage: React.FC = () => {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const [paper, setPaper] = useState<ArxivPaper | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [relatedPapers, setRelatedPapers] = useState<ArxivPaper[]>([]);
  const [isLoadingRelated, setIsLoadingRelated] = useState(false);

  useEffect(() => {
    const fetchPaperDetails = async () => {
      if (!paperId) {
        setError('No paper ID provided');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // Fetch the specific paper
        const paperData = await arxivService.fetchPaperById(paperId);
        
        if (!paperData) {
          setError(`Paper with ID "${paperId}" not found`);
          setPaper(null);
        } else {
          setPaper(paperData);
          
          // Fetch related papers from the same primary category
          if (paperData.categories.length > 0) {
            const primaryCategory = paperData.categories.find(cat => cat.startsWith('cs.')) || paperData.categories[0];
            if (primaryCategory) {
              setIsLoadingRelated(true);
              try {
                const relatedResponse = await arxivService.fetchPapersByCategory(primaryCategory, 5);
                // Filter out the current paper
                setRelatedPapers(relatedResponse.papers.filter(p => p.id !== paperId).slice(0, 4));
              } catch (err) {
                console.error('Error fetching related papers:', err);
              } finally {
                setIsLoadingRelated(false);
              }
            }
          }
        }
      } catch (err) {
        console.error('Error fetching paper details:', err);
        setError(err instanceof Error ? err.message : 'Failed to load paper details');
        setPaper(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPaperDetails();
  }, [paperId]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleBack = () => {
    navigate(-1);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <NavigationBar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 animate-pulse">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-6"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6 mb-2"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/6 mb-8"></div>
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-4"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-48"></div>
          </div>
        </main>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <NavigationBar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-800 p-8 text-center">
            <div className="text-red-600 dark:text-red-400 mb-4">
              <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Paper Not Found</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">{error || 'The requested paper could not be found.'}</p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={handleBack}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Go Back
              </button>
              <Link
                to="/"
                className="px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg transition-colors text-center"
              >
                Browse Latest Papers
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const primaryCategory = paper.categories.find(cat => cat.startsWith('cs.')) || paper.categories[0];
  const mainCategory = primaryCategory ? getMainCategory(primaryCategory) : undefined;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <NavigationBar selectedCategory={primaryCategory} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back button */}
        <button
          onClick={handleBack}
          className="inline-flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to papers
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main content */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Paper header */}
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                  <div className="flex flex-wrap items-center gap-2">
                    {paper.categories.map((category) => (
                      <span
                        key={category}
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                          category === primaryCategory
                            ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300'
                        }`}
                      >
                        {getCategoryName(category)}
                      </span>
                    ))}
                  </div>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {formatDate(paper.published)}
                  </span>
                </div>

                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                  {paper.title}
                </h1>

                {/* Authors */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Authors
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {paper.authors.map((author, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-3 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-300 text-sm"
                      >
                        <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        {author}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Paper content */}
              <div className="p-6">
                {/* Abstract */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                    Abstract
                  </h3>
                  <div className="prose prose-lg dark:prose-invert max-w-none">
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-line">
                      {paper.summary}
                    </p>
                  </div>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  {/* Dates */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Submission Timeline
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Submitted</span>
                        <span className="text-gray-900 dark:text-white">
                          {formatDate(paper.published)}
                        </span>
                      </div>
                      {paper.updated !== paper.published && (
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Last Updated</span>
                          <span className="text-gray-900 dark:text-white">
                            {formatDate(paper.updated)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Identifiers */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Identifiers
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">arXiv ID</span>
                        <span className="text-gray-900 dark:text-white font-mono">
                          {paper.id}
                        </span>
                      </div>
                      {paper.doi && (
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">DOI</span>
                          <a
                            href={`https://doi.org/${paper.doi}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            {paper.doi}
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Additional information */}
                {(paper.comment || paper.journalRef) && (
                  <div className="mb-8">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                      Additional Information
                    </h3>
                    <div className="space-y-3">
                      {paper.comment && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                            Comments
                          </h4>
                          <p className="text-gray-700 dark:text-gray-300">{paper.comment}</p>
                        </div>
                      )}
                      {paper.journalRef && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                            Journal Reference
                          </h4>
                          <p className="text-gray-700 dark:text-gray-300">{paper.journalRef}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
                <div className="flex flex-wrap gap-3">
                  <a
                    href={paper.pdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download PDF
                  </a>
                  <a
                    href={`https://arxiv.org/abs/${paper.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg transition-colors"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    View on arXiv
                  </a>
                  <Link
                    to={`/?category=${primaryCategory}`}
                    className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    Browse {getCategoryName(primaryCategory)} Papers
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Citation tools */}
            {paper && <CitationTools paper={paper} />}

            {/* Related papers */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Related Papers
              </h3>
              {isLoadingRelated ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
                  ))}
                </div>
              ) : relatedPapers.length > 0 ? (
                <div className="space-y-4">
                  {relatedPapers.map((relatedPaper) => (
                    <Link
                      key={relatedPaper.id}
                      to={`/paper/${relatedPaper.id}`}
                      className="block p-3 hover:bg-gray-50 dark:hover:bg-gray-900 rounded-lg transition-colors"
                    >
                      <h4 className="font-medium text-gray-900 dark:text-white text-sm line-clamp-2 mb-1">
                        {relatedPaper.title}
                      </h4>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(relatedPaper.published).toLocaleDateString()}
                        </span>
                        <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded">
                          {getCategoryName(relatedPaper.categories[0] || '')}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 text-sm">
                  No related papers found.
                </p>
              )}
              {mainCategory && (
                <Link
                  to={`/?category=${mainCategory.id}`}
                  className="mt-4 inline-flex items-center text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                >
                  Browse all {mainCategory.name} papers
                  <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              )}
            </div>

            {/* Paper info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Paper Information
              </h3>
              <div className="space-y-3">
                <div>
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    arXiv ID
                  </div>
                  <div className="font-mono text-sm text-gray-900 dark:text-white">
                    {paper.id}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Primary Category
                  </div>
                  <div className="text-sm text-gray-900 dark:text-white">
                    {getCategoryName(primaryCategory)}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    All Categories
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {paper.categories.map((category) => (
                      <span
                        key={category}
                        className="inline-block px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded"
                      >
                        {category}
                      </span>
                    ))}
                  </div>
                </div>
                {paper.doi && (
                  <div>
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      DOI
                    </div>
                    <a
                      href={`https://doi.org/${paper.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {paper.doi}
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default PaperDetailPage;