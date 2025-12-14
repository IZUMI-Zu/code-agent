
import { useNavigate } from 'react-router-dom';
import './PaperList.css';

function PaperList({ papers, loading, error }) {
  const navigate = useNavigate();

  const handlePaperClick = (paperId) => {
    // Extract the ID part after the last slash
    const id = paperId.split('/').pop();
    navigate(`/paper/${id}`);
  };

  if (loading) {
    return (
      <div className="paper-list">
        <div className="loading">Loading papers...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="paper-list">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  if (!papers || papers.length === 0) {
    return (
      <div className="paper-list">
        <div className="not-found">No papers found.</div>
      </div>
    );
  }

  return (
    <div className="paper-list">
      <h2>Latest Computer Science Papers</h2>
      <ul className="paper-items">
        {papers.map((paper) => (
          <li 
            key={paper.id} 
            className="paper-item"
            onClick={() => handlePaperClick(paper.id)}
          >
            <h3>{paper.title}</h3>
            <div className="authors">
              {paper.authors.join(', ')}
            </div>
            <div className="date">
              Published: {paper.publishedFormatted}
            </div>
            <div className="categories">
              {paper.categories.map((category) => (
                <span key={category} className="category-tag">
                  {category}
                </span>
              ))}
            </div>
            <div className="abstract">
              <div className="abstract-preview">
                {paper.summary}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default PaperList;
