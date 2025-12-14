import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchPaperById } from '../services/arxivApi';
import type { Paper } from '../types';
import './PaperDetail.css';

const PaperDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [paper, setPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showBibtex, setShowBibtex] = useState(false);

  useEffect(() => {
    if (!id) return;
    const loadPaper = async () => {
      setLoading(true);
      try {
        const data = await fetchPaperById(decodeURIComponent(id));
        setPaper(data);
      } catch (err) {
        setError('Failed to load paper details.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadPaper();
  }, [id]);

  if (loading) return <div className="loading">Loading paper details...</div>;
  if (error || !paper) return <div className="error">{error || 'Paper not found'}</div>;

  const generateBibtex = (p: Paper) => {
    const year = new Date(p.published).getFullYear();
    const authorText = p.authors.map(a => a.name).join(' and ');
    const arxivId = p.id.split('/').pop(); // simple extraction
    
    return `@article{arxiv.${arxivId},
  title={${p.title}},
  author={${authorText}},
  journal={arXiv preprint arXiv:${arxivId}},
  year={${year}},
  url={${p.links.abs}}
}`;
  };

  return (
    <div className="paper-detail-container">
      <Link to=".." className="back-link">&larr; Back to list</Link>
      
      <article className="paper-detail">
        <header className="detail-header">
          <h1 className="detail-title">{paper.title}</h1>
          <div className="detail-meta">
            <div className="meta-row">
              <span className="label">Authors:</span>
              <span className="value">{paper.authors.map(a => a.name).join(', ')}</span>
            </div>
            <div className="meta-row">
              <span className="label">Submitted:</span>
              <span className="value">{new Date(paper.published).toLocaleDateString()}</span>
            </div>
             <div className="meta-row">
              <span className="label">Categories:</span>
              <span className="value tag-list">
                {paper.categories.map(c => <span key={c} className="tag">{c}</span>)}
              </span>
            </div>
          </div>
        </header>

        <div className="action-bar">
          <a href={paper.links.pdf} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
            View PDF
          </a>
          <a href={paper.links.abs} target="_blank" rel="noopener noreferrer" className="btn btn-outline">
            arXiv Page
          </a>
          <button onClick={() => setShowBibtex(!showBibtex)} className="btn btn-outline">
            {showBibtex ? 'Hide Citation' : 'Cite (BibTeX)'}
          </button>
        </div>

        {showBibtex && (
          <div className="bibtex-box">
            <pre>{generateBibtex(paper)}</pre>
            <button 
              onClick={() => navigator.clipboard.writeText(generateBibtex(paper))}
              className="btn-copy"
            >
              Copy
            </button>
          </div>
        )}

        <section className="detail-abstract">
          <h3>Abstract</h3>
          <p>{paper.summary}</p>
        </section>
      </article>
    </div>
  );
};

export default PaperDetail;
