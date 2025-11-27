
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './layout/Header';
import Footer from './layout/Footer';
import HomePage from './pages/HomePage';
import CategoriesPage from './pages/CategoriesPage';
import CategoryPage from './components/categories/CategoryPage';
import PaperDetail from './components/details/PaperDetail';
import AboutPage from './components/about/AboutPage';
import NotFoundPage from './components/errors/NotFoundPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Header />

        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/categories" element={<CategoriesPage />} />
            <Route path="/category/:categoryId" element={<CategoryPage />} />
            <Route path="/paper/:paperId" element={<PaperDetail />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>

        <Footer />
      </div>
    </Router>
  );
}

export default App;
