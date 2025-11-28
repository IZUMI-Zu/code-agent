import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import PaperList from './pages/PaperList';
import PaperDetail from './pages/PaperDetail';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<PaperList />} />
        <Route path="/paper/:id" element={<PaperDetail />} />
      </Routes>
    </Router>
  );
}

export default App;
