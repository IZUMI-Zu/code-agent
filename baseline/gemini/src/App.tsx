import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import PaperList from './components/PaperList';
import PaperDetail from './components/PaperDetail';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<PaperList />} />
          <Route path="category/:category" element={<PaperList />} />
          <Route path="paper/:id" element={<PaperDetail />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;