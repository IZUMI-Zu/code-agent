// ============================================================
// 论文详情页
// 设计原则：按需加载，错误处理简洁
// ============================================================

import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PaperDetail } from '../components/PaperDetail';
import { fetchPaperById } from '../services/arxiv';
import type { Paper } from '../types';

export function PaperPage() {
  const { id } = useParams<{ id: string }>();
  const [paper, setPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    loadPaper(id);
  }, [id]);

  const loadPaper = async (arxivId: string) => {
    setLoading(true);
    try {
      const data = await fetchPaperById(arxivId);
      setPaper(data);
    } catch (error) {
      console.error('Failed to fetch paper:', error);
      setPaper(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">加载论文详情...</div>;
  }

  if (!paper) {
    return (
      <div className="error">
        <h2>论文未找到</h2>
        <Link to="/">返回首页</Link>
      </div>
    );
  }

  return (
    <div className="paper-page">
      <nav className="breadcrumb">
        <Link to="/">首页</Link>
        <span> / </span>
        <span>{paper.id}</span>
      </nav>

      <PaperDetail paper={paper} />
    </div>
  );
}
