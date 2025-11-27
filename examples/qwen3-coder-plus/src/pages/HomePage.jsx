import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import PaperItem from '../components/papers/PaperItem';
import LoadingSpinner from '../layout/LoadingSpinner';
import ErrorMessage from '../components/errors/ErrorMessage';
import { fetchPapers } from '../services/arxivService';
import './HomePage.css';

const HomePage = () => {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPapersData = async () => {
      try {
        setLoading(true);
        // Fetch real data from arXiv API
        const papersData = await fetchPapers({
          max_results: 10 // Limit to 10 most recent papers for the homepage
        });
        
        setPapers(papersData);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch papers:', err);
        setError('Failed to fetch papers. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchPapersData();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="home-page">
      <header className="hero-section">
        <h1>Latest Computer Science Research</h1>
        <p>Stay up-to-date with the newest papers from arXiv</p>
      </header>

      <section className="featured-papers">
        <h2>Today&apos;s Featured Papers</h2>
        <div className="papers-list">
          {papers.map((paper) => (
            <PaperItem key={paper.id} paper={paper} />
          ))}
        </div>
        <div className="view-all-container">
          <Link to="/categories" className="view-all-link">
            View All Categories
          </Link>
        </div>
      </section>
    </div>
  );
};

export default HomePage;