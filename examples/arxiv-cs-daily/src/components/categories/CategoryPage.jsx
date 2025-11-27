import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import PaperItem from '../../components/papers/PaperItem';
import LoadingSpinner from '../../layout/LoadingSpinner';
import ErrorMessage from '../../components/errors/ErrorMessage';
import { fetchPapersByCategory } from '../../services/arxivService';
import './CategoryPage.css';

const CategoryPage = () => {
  const { categoryId } = useParams();
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Map category IDs to display names
  const categoryNames = {
    'cs.AI': 'Artificial Intelligence',
    'cs.LG': 'Machine Learning',
    'cs.CV': 'Computer Vision',
    'cs.CL': 'Computation and Language',
    'cs.CR': 'Cryptography and Security',
    'cs.DB': 'Databases',
    'cs.DS': 'Data Structures and Algorithms',
    'cs.HC': 'Human-Computer Interaction',
  };

  useEffect(() => {
    const fetchPapers = async () => {
      try {
        setLoading(true);
        // Fetch real data from arXiv API
        const papersData = await fetchPapersByCategory(categoryId, 20);
        
        setPapers(papersData);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch papers:', err);
        setError('Failed to fetch papers. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchPapers();
  }, [categoryId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="category-page">
      <h1>{categoryNames[categoryId] || categoryId}</h1>
      <p>Browse the latest research papers in this category</p>

      <div className="papers-list">
        {papers.length > 0 ? (
          papers.map((paper) => (
            <PaperItem key={paper.id} paper={paper} />
          ))
        ) : (
          <p>No papers found in this category.</p>
        )}
      </div>
    </div>
  );
};

export default CategoryPage;