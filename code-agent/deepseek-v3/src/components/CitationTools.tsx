import React, { useState, useEffect } from 'react';
import type { ArxivPaper } from '../services/arxivService';

interface CitationToolsProps {
  paper: ArxivPaper;
}

type CitationFormat = 'bibtex' | 'apa' | 'mla' | 'chicago' | 'harvard' | 'vancouver';

interface CitationOption {
  id: CitationFormat;
  name: string;
  description: string;
}

const CITATION_OPTIONS: CitationOption[] = [
  {
    id: 'bibtex',
    name: 'BibTeX',
    description: 'Standard BibTeX format for LaTeX documents'
  },
  {
    id: 'apa',
    name: 'APA',
    description: 'American Psychological Association (7th edition)'
  },
  {
    id: 'mla',
    name: 'MLA',
    description: 'Modern Language Association (9th edition)'
  },
  {
    id: 'chicago',
    name: 'Chicago',
    description: 'Chicago Manual of Style (17th edition)'
  },
  {
    id: 'harvard',
    name: 'Harvard',
    description: 'Harvard referencing style'
  },
  {
    id: 'vancouver',
    name: 'Vancouver',
    description: 'Vancouver/Numeric style'
  }
];

const CitationTools: React.FC<CitationToolsProps> = ({ paper }) => {
  const [selectedFormat, setSelectedFormat] = useState<CitationFormat>('bibtex');
  const [citationText, setCitationText] = useState<string>('');
  const [isCopied, setIsCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Generate citation based on selected format
  const generateCitation = (format: CitationFormat): string => {
    const authors = paper.authors.join(' and ');
    const year = new Date(paper.published).getFullYear();
    const title = paper.title.replace(/\.$/, '');
    const journal = 'arXiv preprint';
    const arxivId = paper.id;
    const url = `https://arxiv.org/abs/${arxivId}`;
    const doi = paper.doi ? `https://doi.org/${paper.doi}` : undefined;

    switch (format) {
      case 'bibtex':
        return `@article{${arxivId.replace('.', '')},
  author = {${authors}},
  title = {{${title}}},
  journal = {arXiv preprint},
  year = {${year}},
  eprint = {${arxivId}},
  url = {${url}}${doi ? `,\n  doi = {${paper.doi}}` : ''}
}`;

      case 'apa':
        return `${authors} (${year}). ${title}. ${journal} ${arxivId}. ${doi || url}`;

      case 'mla':
        return `${authors}. "${title}." ${journal} ${arxivId} (${year}). ${doi ? `DOI: ${paper.doi}` : `Web. ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} <${url}>.`}`;

      case 'chicago':
        return `${authors}. "${title}." ${journal} ${arxivId} (${year}). ${doi || url}`;

      case 'harvard':
        return `${authors} (${year}) '${title}', ${journal}, ${arxivId}. Available at: ${doi || url} (Accessed: ${new Date().toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })})`;

      case 'vancouver':
        return `${authors}. ${title}. ${journal}. ${year};${arxivId}. ${doi ? `DOI: ${paper.doi}` : `Available from: ${url}`}`;

      default:
        return `Citation format not supported.`;
    }
  };

  // Update citation when format changes
  useEffect(() => {
    setIsLoading(true);
    // Simulate async generation (could be real async with citation.js)
    setTimeout(() => {
      setCitationText(generateCitation(selectedFormat));
      setIsLoading(false);
    }, 100);
  }, [selectedFormat, paper]);

  const handleCopyCitation = async () => {
    try {
      await navigator.clipboard.writeText(citationText);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = citationText;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  const handleDownloadCitation = () => {
    const blob = new Blob([citationText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${paper.id}-${selectedFormat}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Citation Tools
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Generate citations for this paper in various academic formats
        </p>
      </div>

      <div className="p-6">
        {/* Format selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Select Citation Format
          </label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {CITATION_OPTIONS.map((option) => (
              <button
                key={option.id}
                onClick={() => setSelectedFormat(option.id)}
                className={`p-3 text-left rounded-lg border transition-colors ${
                  selectedFormat === option.id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-900/50 text-gray-700 dark:text-gray-300'
                }`}
              >
                <div className="font-medium">{option.name}</div>
                <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  {option.description}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Citation preview */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Citation Preview
            </label>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {isLoading ? 'Generating...' : 'Ready to copy'}
            </div>
          </div>
          <div className="relative">
            <pre className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4 text-sm font-mono text-gray-800 dark:text-gray-300 whitespace-pre-wrap overflow-x-auto max-h-64 overflow-y-auto">
              {isLoading ? 'Generating citation...' : citationText}
            </pre>
            {!isLoading && citationText && (
              <button
                onClick={handleCopyCitation}
                className="absolute top-2 right-2 p-2 bg-gray-800 dark:bg-gray-700 text-white rounded-md hover:bg-gray-900 dark:hover:bg-gray-600 transition-colors"
                title="Copy to clipboard"
              >
                {isCopied ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleCopyCitation}
            disabled={isLoading || !citationText}
            className={`inline-flex items-center px-4 py-2 rounded-lg transition-colors ${
              isCopied
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
          >
            {isCopied ? (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied!
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy Citation
              </>
            )}
          </button>
          <button
            onClick={handleDownloadCitation}
            disabled={isLoading || !citationText}
            className="inline-flex items-center px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download as .txt
          </button>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-white rounded-lg transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Print
          </button>
        </div>

        {/* Tips */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Citation Tips
          </h4>
          <ul className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
            <li className="flex items-start">
              <svg className="w-3 h-3 mr-1.5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Always verify citations with your institution's style guide</span>
            </li>
            <li className="flex items-start">
              <svg className="w-3 h-3 mr-1.5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>BibTeX is recommended for LaTeX documents and reference managers</span>
            </li>
            <li className="flex items-start">
              <svg className="w-3 h-3 mr-1.5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Include the arXiv ID and URL for proper attribution</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default CitationTools;