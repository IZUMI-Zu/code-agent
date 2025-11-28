import { useState, useEffect } from 'react';
import { format, isToday, parseISO } from 'date-fns';
import Navigation from '../components/Navigation';
import PaperCard from '../components/PaperCard';
import { fetchPapersByCategory } from '../services/arxivApi';
import './PaperList.css';

const PaperList = () => {
  const [papers, setPapers] = useState([]);
  const [filteredPapers, setFilteredPapers] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showTodayOnly, setShowTodayOnly] = useState(false);

  useEffect(() => {
    loadPapers();
  }, [selectedCategory]);

  useEffect(() => {
    filterPapers();
  }, [papers, showTodayOnly]);

  const loadPapers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchPapersByCategory(selectedCategory, 100);
      setPapers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filterPapers = () => {
    if (showTodayOnly) {
      const todayPapers = papers.filter(paper => {
        try {
          return isToday(parseISO(paper.published));
        } catch {
          return false;
        }
      });
      setFilteredPapers(todayPapers);
    } else {
      setFilteredPapers(papers);
    }
  };

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
  };

  if (loading) {
    return (
      <div className="paper-list-container">
        <Navigation 
          selectedCategory={selectedCategory}
          onCategoryChange={handleCategoryChange}
        />
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading papers...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="paper-list-container">
        <Navigation 
          selectedCategory={selectedCategory}
          onCategoryChange={handleCategoryChange}
        />
        <div className="error-container">
          <h2>Error Loading Papers</h2>
          <p>{error}</p>
          <button onClick={loadPapers} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="paper-list-container">
      <Navigation 
        selectedCategory={selectedCategory}
        onCategoryChange={handleCategoryChange}
      />
      
      <div className="content-container">
        <div className="list-header">
          <div className="header-info">
            <h2>
              {selectedCategory === 'all' ? 'All Computer Science Papers' : selectedCategory}
            </h2>
            <p className="paper-count">
              {filteredPapers.length} paper{filteredPapers.length !== 1 ? 's' : ''} found
            </p>
          </div>
          
          <div className="filter-controls">
            <label className="today-filter">
              <input
                type="checkbox"
                checked={showTodayOnly}
                onChange={(e) => setShowTodayOnly(e.target.checked)}
              />
              <span>Today's papers only</span>
            </label>
          </div>
        </div>

        {filteredPapers.length === 0 ? (
          <div className="empty-state">
            <p>No papers found for the selected filters.</p>
            {showTodayOnly && (
              <p className="empty-hint">Try unchecking "Today's papers only" to see more results.</p>
            )}
          </div>
        ) : (
          <div className="papers-grid">
            {filteredPapers.map(paper => (
              <PaperCard key={paper.id} paper={paper} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PaperList;
