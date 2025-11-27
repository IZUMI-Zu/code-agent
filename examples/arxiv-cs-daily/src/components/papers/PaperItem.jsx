
import { Link } from 'react-router-dom';
import './PaperItem.css';

const PaperItem = ({ paper }) => {
  return (
    <div className="paper-item">
      <h3 className="paper-title">
        <Link to={`/paper/${paper.id.split('/').pop()}`}>{paper.title}</Link>
      </h3>
      <p className="paper-authors">
        {paper.authors.join(', ')}
      </p>
      <p className="paper-abstract">
        {paper.summary.substring(0, 200)}...
      </p>
      <p className="paper-date">
        Published: {new Date(paper.published).toLocaleDateString()}
      </p>
    </div>
  );
};

export default PaperItem;
