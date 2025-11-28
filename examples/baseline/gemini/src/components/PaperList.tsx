import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchPapers } from '../services/arxivApi';
import { CS_CATEGORIES } from '../types';
import type { Paper } from '../types';
import './PaperList.css';

const PaperList: React.FC = () => {
  const { category } = useParams<{ category: string }>();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeCategory = category 
    ? CS_CATEGORIES.find(c => c.id === category)
    : { id: 'cs', name: 'Computer Science (All)', description: 'Recent CS Preprints' };

  // Use 'cs' as default search query if no category is selected
  const queryCategory = category || 'cs';

  useEffect(() => {
    const loadPapers = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchPapers(queryCategory);
        setPapers(data);
      } catch (err) {
        setError('Failed to load papers. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadPapers();
  }, [queryCategory]);

  if (loading) return <div className="loading">Loading papers...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="paper-list-container">
      <header className="list-header">
        <h2>{activeCategory?.name}</h2>
        <p className="subtitle">{activeCategory?.description}</p>
      </header>

      <div className="paper-list">
        {papers.length === 0 ? (
          <p>No papers found.</p>
        ) : (
          papers.map((paper) => (
            <div key={paper.id} className="paper-item">
              <div className="paper-meta-top">
                <span className="paper-date">{new Date(paper.published).toLocaleDateString()}</span>
                <span className="paper-tags">
                  {paper.categories.map(cat => (
                    <span key={cat} className="tag">{cat}</span>
                  ))}
                </span>
              </div>
              
              <h3 className="paper-title">
                <Link to={`/paper/${encodeURIComponent(paper.id)}`}>
                  {paper.title}
                </Link>
              </h3>

              <div className="paper-authors">
                {paper.authors.slice(0, 3).map(a => a.name).join(', ')}
                {paper.authors.length > 3 && ', et al.'}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default PaperList;
