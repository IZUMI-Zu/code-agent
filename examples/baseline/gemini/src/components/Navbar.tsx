import React from 'react';
import { NavLink } from 'react-router-dom';
import { CS_CATEGORIES } from '../types';
import './Navbar.css';

const Navbar: React.FC = () => {
  return (
    <nav className="navbar">
      <div className="navbar-header">
        <h1>arXiv CS Daily</h1>
      </div>
      <ul className="navbar-list">
        <li>
          <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
            All Recent
          </NavLink>
        </li>
        {CS_CATEGORIES.map((cat) => (
          <li key={cat.id}>
            <NavLink to={`/category/${cat.id}`} className={({ isActive }) => isActive ? 'active' : ''}>
              <span className="cat-id">{cat.id}</span>
              <span className="cat-name">{cat.name}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default Navbar;
