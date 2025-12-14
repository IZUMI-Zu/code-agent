import { useState } from 'react';
import { CS_CATEGORIES } from '../constants/categories';
import './Navigation.css';

const Navigation = ({ selectedCategory, onCategoryChange }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const handleCategoryClick = (categoryId) => {
    onCategoryChange(categoryId);
    setIsMenuOpen(false);
  };

  return (
    <nav className="navigation">
      <div className="nav-container">
        <div className="nav-header">
          <h1 className="nav-title">arXiv CS Daily</h1>
          <button 
            className="nav-toggle"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
        </div>
        
        <div className={`nav-categories ${isMenuOpen ? 'open' : ''}`}>
          <button
            className={`category-btn ${selectedCategory === 'all' ? 'active' : ''}`}
            onClick={() => handleCategoryClick('all')}
          >
            All CS
          </button>
          
          {CS_CATEGORIES.map(category => (
            <button
              key={category.id}
              className={`category-btn ${selectedCategory === category.id ? 'active' : ''}`}
              onClick={() => handleCategoryClick(category.id)}
              title={category.name}
            >
              {category.id}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
