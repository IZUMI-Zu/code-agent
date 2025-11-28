import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import './PaperCard.css';

const PaperCard = ({ paper }) => {
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
    } catch (error) {
      return dateString;
    }
  };

  return (
    <div className="paper-card">
      <div className="paper-header">
        <div className="paper-categories">
          {paper.primaryCategory && (
            <span className="category-tag primary">
              {paper.primaryCategory}
            </span>
          )}
        </div>
        <span className="paper-date">{formatDate(paper.published)}</span>
      </div>
      
      <Link to={`/paper/${paper.id}`} className="paper-title-link">
        <h3 className="paper-title">{paper.title}</h3>
      </Link>
      
      <div className="paper-authors">
        {paper.authors.slice(0, 3).map((author, index) => (
          <span key={index} className="author-name">
            {author.name}
            {index < Math.min(2, paper.authors.length - 1) && ', '}
          </span>
        ))}
        {paper.authors.length > 3 && (
          <span className="author-name"> et al.</span>
        )}
      </div>

      <p className="paper-summary">
        {paper.summary.length > 300 
          ? `${paper.summary.substring(0, 300)}...` 
          : paper.summary}
      </p>

      <div className="paper-footer">
        <span className="paper-id">arXiv:{paper.id}</span>
        <Link to={`/paper/${paper.id}`} className="read-more">
          Read More →
        </Link>
      </div>
    </div>
  );
};

export default PaperCard;
