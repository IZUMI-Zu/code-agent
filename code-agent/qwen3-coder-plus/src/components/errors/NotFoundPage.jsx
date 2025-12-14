import { Link } from 'react-router-dom';
import './NotFoundPage.css';

const NotFoundPage = () => {
  return (
    <div className="not-found-page">
      <h1>404 - Page Not Found</h1>
      <p>Sorry, the page you&apos;re looking for does not exist.</p>
      <Link to="/" className="home-link">Return to Home</Link>
    </div>
  );
};

export default NotFoundPage;