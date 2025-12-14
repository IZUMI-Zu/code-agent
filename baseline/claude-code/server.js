// ============================================================
// arXiv API 代理服务器
// 设计原则：单一职责 - 转发请求，解决 CORS 问题
// ============================================================

import express from 'express';
import cors from 'cors';

const app = express();
const PORT = 3001;

// ==================== CORS 配置 ====================
app.use(cors());

// ==================== 静态文件服务（生产环境） ====================
app.use(express.static('dist'));

// ==================== arXiv API 代理 ====================
app.get('/api/arxiv', async (req, res) => {
  try {
    // 构建 arXiv API URL
    const queryString = new URLSearchParams(req.query).toString();
    const arxivUrl = `https://export.arxiv.org/api/query?${queryString}`;

    // 转发请求
    const response = await fetch(arxivUrl);
    const data = await response.text();

    // 返回 XML 数据
    res.set('Content-Type', 'application/xml');
    res.send(data);
  } catch (error) {
    console.error('arXiv API 请求失败:', error);
    res.status(500).json({ error: 'Failed to fetch from arXiv API' });
  }
});

// ==================== 启动服务器 ====================
app.listen(PORT, () => {
  console.log(`arXiv CS Daily 服务器运行在 http://localhost:${PORT}`);
  console.log(`API 代理: http://localhost:${PORT}/api/arxiv`);
});
