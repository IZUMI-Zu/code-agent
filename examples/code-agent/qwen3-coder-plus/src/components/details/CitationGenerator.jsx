import { useState } from 'react';
import { CopyToClipboard } from 'react-copy-to-clipboard';
import { generateBibtex, generateAPA, generateMLA } from '../../utils/citationUtils';

const CitationGenerator = ({ paper }) => {
  const [activeTab, setActiveTab] = useState('bibtex');
  const [copied, setCopied] = useState(false);

  const citations = {
    bibtex: generateBibtex(paper),
    apa: generateAPA(paper),
    mla: generateMLA(paper)
  };

  const handleCopy = () => {
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="citation-generator">
      <h3>Cite this paper</h3>
      <div className="citation-tabs">
        <button
          className={activeTab === 'bibtex' ? 'active' : ''}
          onClick={() => setActiveTab('bibtex')}
        >
          BibTeX
        </button>
        <button
          className={activeTab === 'apa' ? 'active' : ''}
          onClick={() => setActiveTab('apa')}
        >
          APA
        </button>
        <button
          className={activeTab === 'mla' ? 'active' : ''}
          onClick={() => setActiveTab('mla')}
        >
          MLA
        </button>
      </div>

      <div className="citation-content">
        <pre>{citations[activeTab]}</pre>
        <CopyToClipboard
          text={citations[activeTab]}
          onCopy={handleCopy}
        >
          <button className="copy-button">
            {copied ? 'Copied!' : 'Copy to Clipboard'}
          </button>
        </CopyToClipboard>
      </div>
    </div>
  );
};

export default CitationGenerator;