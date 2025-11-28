# arXiv CS Daily

一个简洁、高效的 arXiv 计算机科学论文每日浏览系统。

## 核心功能

### 1. 领域导航系统
- 基于 arXiv 主要 CS 领域的分类导航（cs.AI, cs.CV, cs.LG 等）
- 快速切换和过滤不同子领域
- 侧边栏导航，直观易用

### 2. 每日论文列表
- 按提交日期排序的最新论文
- 显示关键信息：标题、作者、领域标签、提交时间
- 点击标题直接跳转详情页
- 支持直接访问 PDF 下载链接

### 3. 论文详情页
- 完整元数据展示（标题、作者、机构、日期）
- 论文摘要
- 直接链接到 arXiv PDF 和原始页面
- 一键复制引用格式：
  - BibTeX 格式
  - 标准学术引用（APA 风格）

## 技术栈

- **前端框架**: React 18 + TypeScript
- **构建工具**: Vite
- **路由**: React Router v6
- **样式**: 原生 CSS（无框架依赖）
- **数据源**: arXiv API

## 快速开始

### 安装依赖
```bash
npm install
```

### 开发模式（推荐）
```bash
npm run dev
```
> Vite 会自动配置代理，解决 CORS 跨域问题
> 访问 http://localhost:5173

### 生产环境部署
```bash
npm start
```
> 先构建前端，然后启动 Express 服务器（包含 API 代理）
> 访问 http://localhost:3001

### 仅构建前端
```bash
npm run build
```

## 项目结构

```
src/
├── components/          # UI 组件
│   ├── CategoryNav.tsx  # 分类导航
│   ├── PaperList.tsx    # 论文列表
│   └── PaperDetail.tsx  # 论文详情
├── pages/               # 页面组件
│   ├── HomePage.tsx     # 首页
│   └── PaperPage.tsx    # 论文详情页
├── services/            # 业务逻辑
│   └── arxiv.ts         # arXiv API 集成
├── types/               # TypeScript 类型定义
│   └── index.ts
├── styles/              # 样式文件
│   └── index.css
├── App.tsx              # 应用根组件
└── main.tsx             # 入口文件
```

## 设计原则

遵循 Linus Torvalds 的代码哲学：

1. **Good Taste（好品味）**
   - 消除特殊情况，统一的数据结构处理所有 CS 子领域
   - 无冗余分支判断

2. **Pragmatism（实用主义）**
   - 直接从 arXiv API 获取真实数据
   - 功能直接、可测试

3. **Simplicity（简洁执念）**
   - 每个组件单一职责
   - 函数短小精悍
   - 无不必要的抽象

## API 说明

本项目使用 [arXiv API](https://arxiv.org/help/api) 获取论文数据。

**CORS 解决方案**：

- **开发环境**：Vite 配置代理转发（自动处理）
- **生产环境**：Express 服务器提供 API 代理

**数据获取规则**：

- 每次请求默认获取 50 篇最新论文
- 按提交日期降序排列
- 支持按分类过滤

## License

MIT
