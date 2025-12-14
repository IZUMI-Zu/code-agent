
import { Link } from 'react-router-dom';
import './CategoriesPage.css';

const CategoriesPage = () => {
  // List of computer science categories
  const categories = [
    { id: 'cs.AI', name: 'Artificial Intelligence' },
    { id: 'cs.LG', name: 'Machine Learning' },
    { id: 'cs.CV', name: 'Computer Vision' },
    { id: 'cs.CL', name: 'Computation and Language' },
    { id: 'cs.CR', name: 'Cryptography and Security' },
    { id: 'cs.DB', name: 'Databases' },
    { id: 'cs.DS', name: 'Data Structures and Algorithms' },
    { id: 'cs.HC', name: 'Human-Computer Interaction' },
  ];

  return (
    <div className="categories-page">
      <h1>Computer Science Categories</h1>
      <p>Browse research papers by category</p>
      
      <div className="categories-grid">
        {categories.map((category) => (
          <div key={category.id} className="category-card">
            <h3>
              <Link to={`/category/${category.id}`}>
                {category.name}
              </Link>
            </h3>
            <p className="category-id">{category.id}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CategoriesPage;
