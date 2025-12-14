// ============================================================
// 领域导航组件
// 设计原则：数据驱动，无特殊分支
// ============================================================

import { CS_CATEGORIES, type CategoryKey } from '../types';

interface CategoryNavProps {
  activeCategory: CategoryKey;
  onCategoryChange: (category: CategoryKey) => void;
}

export function CategoryNav({ activeCategory, onCategoryChange }: CategoryNavProps) {
  return (
    <nav className="category-nav">
      <h2>计算机科学领域</h2>
      <ul>
        {/* 通过 Object.entries 统一处理所有分类 - 无特殊情况 */}
        {Object.entries(CS_CATEGORIES).map(([key, label]) => (
          <li key={key}>
            <button
              className={key === activeCategory ? 'active' : ''}
              onClick={() => onCategoryChange(key as CategoryKey)}
            >
              <span className="category-code">{key}</span>
              <span className="category-label">{label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
