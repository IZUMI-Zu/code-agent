// ============================================================
// 论文详情页组件
// 设计原则：集中展示所有元数据和引用工具
// ============================================================

import { useState } from 'react';
import type { Paper } from '../types';
import { generateBibtex, generateCitation } from '../services/arxiv';

interface PaperDetailProps {
  paper: Paper;
}

export function PaperDetail({ paper }: PaperDetailProps) {
  const [copiedType, setCopiedType] = useState<string | null>(null);

  const handleCopy = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopiedType(type);
    setTimeout(() => setCopiedType(null), 2000);
  };

  const bibtex = generateBibtex(paper);
  const citation = generateCitation(paper);

  return (
    <div className="paper-detail">
      {/* ==================== 核心元数据 ==================== */}
      <header className="paper-detail-header">
        <h1>{paper.title}</h1>

        <div className="paper-categories">
          {paper.categories.map(cat => (
            <span key={cat} className="category-tag">{cat}</span>
          ))}
        </div>

        <div className="paper-authors-detail">
          <h3>作者</h3>
          <ul>
            {paper.authors.map((author, idx) => (
              <li key={idx}>
                {author.name}
                {author.affiliation && (
                  <span className="affiliation"> - {author.affiliation}</span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="paper-dates">
          <div>
            <strong>提交日期：</strong>
            {formatDateTime(paper.published)}
          </div>
          <div>
            <strong>更新日期：</strong>
            {formatDateTime(paper.updated)}
          </div>
        </div>
      </header>

      {/* ==================== 摘要 ==================== */}
      <section className="paper-abstract">
        <h3>摘要</h3>
        <p>{paper.abstract}</p>
      </section>

      {/* ==================== 链接 ==================== */}
      <section className="paper-links">
        <h3>资源链接</h3>
        <div className="links-grid">
          <a href={paper.pdfUrl} target="_blank" rel="noopener noreferrer" className="link-button">
            PDF 下载
          </a>
          <a href={paper.arxivUrl} target="_blank" rel="noopener noreferrer" className="link-button">
            arXiv 页面
          </a>
        </div>
      </section>

      {/* ==================== 引用工具 ==================== */}
      <section className="paper-citations">
        <h3>引用格式</h3>

        {/* BibTeX */}
        <div className="citation-block">
          <div className="citation-header">
            <h4>BibTeX</h4>
            <button
              onClick={() => handleCopy(bibtex, 'bibtex')}
              className="copy-button"
            >
              {copiedType === 'bibtex' ? '已复制 ✓' : '复制'}
            </button>
          </div>
          <pre className="citation-content">{bibtex}</pre>
        </div>

        {/* 标准引用 */}
        <div className="citation-block">
          <div className="citation-header">
            <h4>标准引用（APA 风格）</h4>
            <button
              onClick={() => handleCopy(citation, 'citation')}
              className="copy-button"
            >
              {copiedType === 'citation' ? '已复制 ✓' : '复制'}
            </button>
          </div>
          <p className="citation-content">{citation}</p>
        </div>
      </section>
    </div>
  );
}

// ============================================================
// 辅助函数
// ============================================================

/**
 * 格式化日期时间（包含时分秒）
 */
function formatDateTime(date: Date): string {
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
