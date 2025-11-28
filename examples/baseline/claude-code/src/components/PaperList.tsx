// ============================================================
// 论文列表组件
// 设计原则：纯展示，无业务逻辑
// ============================================================

import { Link } from 'react-router-dom';
import type { Paper } from '../types';

interface PaperListProps {
  papers: Paper[];
  loading?: boolean;
}

export function PaperList({ papers, loading }: PaperListProps) {
  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  if (papers.length === 0) {
    return <div className="empty">暂无论文数据</div>;
  }

  return (
    <div className="paper-list">
      {papers.map(paper => (
        <PaperItem key={paper.id} paper={paper} />
      ))}
    </div>
  );
}

// ============================================================
// 单个论文条目
// ============================================================

interface PaperItemProps {
  paper: Paper;
}

function PaperItem({ paper }: PaperItemProps) {
  return (
    <article className="paper-item">
      <div className="paper-header">
        <Link to={`/paper/${paper.id}`} className="paper-title">
          {paper.title}
        </Link>
        <span className="paper-category">[{paper.primaryCategory}]</span>
      </div>

      <div className="paper-authors">
        {formatAuthorsList(paper.authors.map(a => a.name))}
      </div>

      <div className="paper-meta">
        <time dateTime={paper.published.toISOString()}>
          {formatDate(paper.published)}
        </time>
        <a href={paper.pdfUrl} target="_blank" rel="noopener noreferrer">
          PDF
        </a>
      </div>
    </article>
  );
}

// ============================================================
// 辅助函数
// ============================================================

/**
 * 格式化作者列表（最多显示 3 个，超过则显示 et al.）
 */
function formatAuthorsList(authors: string[]): string {
  if (authors.length <= 3) {
    return authors.join(', ');
  }
  return `${authors.slice(0, 3).join(', ')} et al.`;
}

/**
 * 格式化日期为本地化字符串
 */
function formatDate(date: Date): string {
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}
