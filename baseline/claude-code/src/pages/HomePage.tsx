// ============================================================
// 首页 - 论文列表视图
// 设计原则：状态管理简洁，数据流单向
// ============================================================

import { useState, useEffect } from 'react';
import { CategoryNav } from '../components/CategoryNav';
import { PaperList } from '../components/PaperList';
import { BackButton } from '../components/BackButton';
import { fetchPapers } from '../services/arxiv';
import type { CategoryKey, Paper } from '../types';

export function HomePage() {
  // ==================== 状态管理 ====================
  const [activeCategory, setActiveCategory] = useState<CategoryKey>('cs.AI');
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);

  // ==================== 数据获取 ====================
  useEffect(() => {
    loadPapers(activeCategory);
  }, [activeCategory]);

  const loadPapers = async (category: CategoryKey) => {
    setLoading(true);
    try {
      const data = await fetchPapers(category, 50);
      setPapers(data);
    } catch (error) {
      console.error('Failed to fetch papers:', error);
      setPapers([]);
    } finally {
      setLoading(false);
    }
  };

  // ==================== 渲染 ====================
  return (
    <div className="home-page">
      <aside className="sidebar">
        <CategoryNav
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />
      </aside>

      <main className="main-content">
        <BackButton />

        <header className="page-header">
          <h1>arXiv CS Daily</h1>
          <p className="subtitle">
            当前领域：<strong>{activeCategory}</strong>
          </p>
        </header>

        <PaperList papers={papers} loading={loading} />
      </main>
    </div>
  );
}
