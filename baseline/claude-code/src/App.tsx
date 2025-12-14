// ============================================================
// 应用根组件 - 路由配置
// 设计原则：扁平路由结构，无嵌套复杂性
// ============================================================

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { PaperPage } from './pages/PaperPage';

export function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/paper/:id" element={<PaperPage />} />
      </Routes>
    </BrowserRouter>
  );
}
