import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPaperDetails } from '../../services/arxivService';
import LoadingSpinner from '../../layout/LoadingSpinner';
import ErrorMessage from '../../components/errors/ErrorMessage';
import CitationGenerator from './CitationGenerator';
import './PaperDetail.css';

const PaperDetail = () => {
  const { paperId } = useParams();
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPaper = async () => {
      try {
        setLoading(true);
        const paperData = await fetchPaperDetails(paperId);
        
        if (paperData) {
          // Format the paper data to match our component's expectations
          const formattedPaper = {
            id: paperData.id,
            title: paperData.title,
            authors: paperData.authors,
            abstract: paperData.summary,
            published: paperData.published,
            updated: paperData.updated,
            category: paperData.primaryCategory,
            // Extract DOI if available from links
            doi: paperData.links?.find(link => link.title === 'doi')?.href?.split('/').pop() || null,
          };
          
          setPaper(formattedPaper);
        } else {
          setError('Paper not found.');
        }
      } catch (err) {
        console.error('Error fetching paper details:', err);
        setError('Failed to fetch paper details. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    if (paperId) {
      fetchPaper();
    }
  }, [paperId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!paper) return <ErrorMessage message="Paper not found." />;

  return (
    <div className="paper-detail">
      <h1>{paper.title}</h1>

      <div className="paper-detail-meta">
        <p><strong>Authors:</strong> {paper.authors.join(', ')}</p>
        <p><strong>Published:</strong> {new Date(paper.published).toLocaleDateString()}</p>
        <p><strong>Updated:</strong> {new Date(paper.updated).toLocaleDateString()}</p>
        <p><strong>Category:</strong> {paper.category}</p>
        {paper.doi && <p><strong>DOI:</strong> {paper.doi}</p>}
      </div>

      <div className="paper-detail-abstract">
        <h2>Abstract</h2>
        <p>{paper.abstract}</p>
      </div>

      <CitationGenerator paper={paper} />
    </div>
  );
};

export default PaperDetail;