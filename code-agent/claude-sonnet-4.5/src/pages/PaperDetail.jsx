import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { format } from 'date-fns';
import { fetchPaperById } from '../services/arxivApi';
import CitationTools from '../components/CitationTools';
import { getCategoryName } from '../constants/categories';
import './PaperDetail.css';

const PaperDetail = () => {
  const { id } = useParams();
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPaper();
  }, [id]);

  const loadPaper = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchPaperById(id);
      setPaper(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMMM dd, yyyy');
    } catch (error) {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="paper-detail-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading paper details...</p>
        </div>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="paper-detail-container">
        <div className="error-container">
          <h2>Error Loading Paper</h2>
          <p>{error || 'Paper not found'}</p>
          <Link to="/" className="back-link">← Back to Papers</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="paper-detail-container">
      <div className="detail-header">
        <Link to="/" className="back-link">← Back to Papers</Link>
      </div>

      <article className="paper-detail">
        <header className="detail-title-section">
          <h1 className="detail-title">{paper.title}</h1>
          
          <div className="detail-meta">
            <div className="meta-item">
              <span className="meta-label">arXiv ID:</span>
              <span className="meta-value">{paper.id}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Submitted:</span>
              <span className="meta-value">{formatDate(paper.published)}</span>
            </div>
            {paper.updated !== paper.published && (
              <div className="meta-item">
                <span className="meta-label">Updated:</span>
                <span className="meta-value">{formatDate(paper.updated)}</span>
              </div>
            )}
          </div>

          <div className="detail-categories">
            {paper.primaryCategory && (
              <span className="category-tag primary" title={getCategoryName(paper.primaryCategory)}>
                {paper.primaryCategory}
              </span>
            )}
            {paper.categories
              .filter(cat => cat !== paper.primaryCategory)
              .map((cat, index) => (
                <span key={index} className="category-tag" title={getCategoryName(cat)}>
                  {cat}
                </span>
              ))}
          </div>
        </header>

        <section className="detail-section">
          <h2>Authors</h2>
          <div className="authors-list">
            {paper.authors.map((author, index) => (
              <div key={index} className="author-item">
                <span className="author-name">{author.name}</span>
                {author.affiliation && (
                  <span className="author-affiliation">({author.affiliation})</span>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="detail-section">
          <h2>Abstract</h2>
          <p className="abstract-text">{paper.summary}</p>
        </section>

        <section className="detail-section">
          <h2>Resources</h2>
          <div className="resources-links">
            {paper.pdfLink && (
              <a 
                href={paper.pdfLink} 
                target="_blank" 
                rel="noopener noreferrer"
                className="resource-btn pdf-btn"
              >
                📄 View PDF
              </a>
            )}
            <a 
              href={paper.abstractLink} 
              target="_blank" 
              rel="noopener noreferrer"
              className="resource-btn abstract-btn"
            >
              🔗 arXiv Page
            </a>
          </div>
        </section>

        <section className="detail-section">
          <CitationTools paper={paper} />
        </section>
      </article>
    </div>
  );
};

export default PaperDetail;
