import { useState } from 'react';
import { generateBibTeX, generateStandardCitation, copyToClipboard } from '../utils/citations';
import './CitationTools.css';

const CitationTools = ({ paper }) => {
  const [copiedFormat, setCopiedFormat] = useState(null);

  const handleCopy = async (format) => {
    let text = '';
    if (format === 'bibtex') {
      text = generateBibTeX(paper);
    } else if (format === 'standard') {
      text = generateStandardCitation(paper);
    }

    const success = await copyToClipboard(text);
    if (success) {
      setCopiedFormat(format);
      setTimeout(() => setCopiedFormat(null), 2000);
    }
  };

  const bibtex = generateBibTeX(paper);
  const standard = generateStandardCitation(paper);

  return (
    <div className="citation-tools">
      <h3 className="citation-title">Citation</h3>
      
      <div className="citation-section">
        <div className="citation-header">
          <h4>BibTeX</h4>
          <button 
            className={`copy-btn ${copiedFormat === 'bibtex' ? 'copied' : ''}`}
            onClick={() => handleCopy('bibtex')}
          >
            {copiedFormat === 'bibtex' ? '✓ Copied!' : 'Copy'}
          </button>
        </div>
        <pre className="citation-text">{bibtex}</pre>
      </div>

      <div className="citation-section">
        <div className="citation-header">
          <h4>Standard Citation</h4>
          <button 
            className={`copy-btn ${copiedFormat === 'standard' ? 'copied' : ''}`}
            onClick={() => handleCopy('standard')}
          >
            {copiedFormat === 'standard' ? '✓ Copied!' : 'Copy'}
          </button>
        </div>
        <p className="citation-text">{standard}</p>
      </div>
    </div>
  );
};

export default CitationTools;
