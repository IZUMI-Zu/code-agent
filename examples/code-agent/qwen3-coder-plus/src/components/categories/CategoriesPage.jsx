
import { Link } from 'react-router-dom';
import { categories } from '../../utils/categories';
import './CategoriesPage.css';

const CategoriesPage = () => {
  return (
    <div className="categories-page">
      <h2>Computer Science Categories</h2>
      <div className="categories-grid">
        {categories.map((category) => (
          <div key={category.id} className="category-card">
            <Link to={`/category/${category.id}`}>
              <h3>{category.name}</h3>
              <p className="category-id">{category.id}</p>
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CategoriesPage;
