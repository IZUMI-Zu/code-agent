
import { Link } from 'react-router-dom';
import { categories } from '../../utils/categories';
import './DomainNavigation.css';

const DomainNavigation = () => {
  // We'll show a subset of the most popular categories
  const popularCategories = categories.filter(category => 
    ['cs.AI', 'cs.LG', 'cs.CV', 'cs.CL', 'cs.CR', 'cs.SE'].includes(category.id)
  );

  return (
    <div className="domain-navigation">
      <h3>Popular Categories</h3>
      <ul>
        {popularCategories.map((category) => (
          <li key={category.id}>
            <Link to={`/category/${category.id}`}>{category.name}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default DomainNavigation;
