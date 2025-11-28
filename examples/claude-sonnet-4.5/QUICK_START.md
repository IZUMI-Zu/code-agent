# ⚡ Quick Start Guide

Get the arXiv CS Daily app running in 5 minutes!

## 🎯 Prerequisites

Before you begin, ensure you have:
- **Node.js** 18 or higher ([Download](https://nodejs.org/))
- **npm** (comes with Node.js)
- A code editor (VS Code recommended)
- A terminal/command prompt

### Check Your Setup

```bash
node --version  # Should be v18.0.0 or higher
npm --version   # Should be 9.0.0 or higher
```

---

## 🚀 Installation (3 Steps)

### Step 1: Get the Code

```bash
# Clone the repository
git clone <your-repo-url>
cd arxiv-cs-daily
```

Or download and extract the ZIP file.

### Step 2: Install Dependencies

```bash
npm install
```

This will install:
- React 19.2.0
- React Router DOM 7.9.6
- Axios 1.13.2
- date-fns 4.1.0
- Vite 7.2.4
- And other dev dependencies

**Expected time**: 1-2 minutes

### Step 3: Start Development Server

```bash
npm run dev
```

You should see:

```
  VITE v7.2.4  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**Open your browser** to `http://localhost:5173/`

🎉 **You're done!** The app should be running.

---

## 🎮 Using the App

### Browse Papers
1. The app loads with "All CS" papers by default
2. Click any category in the navigation bar to filter
3. Scroll through the paper cards

### View Paper Details
1. Click on any paper card
2. View full abstract, authors, and metadata
3. Click "View PDF" or "View on arXiv"

### Generate Citations
1. On a paper detail page, click "Show Citation Tools"
2. Choose BibTeX or APA format
3. Click "Copy" to copy to clipboard
4. Paste into your document

### Filter Today's Papers
1. On the main page, toggle "Today's Papers Only"
2. Only papers published today will show

---

## 📂 Project Structure (Simplified)

```
arxiv-cs-daily/
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/           # Main pages (List, Detail)
│   ├── services/        # API calls
│   └── App.jsx          # Main app with routing
├── package.json         # Dependencies
└── vite.config.js       # Vite configuration
```

---

## 🛠️ Available Commands

```bash
# Development
npm run dev          # Start dev server (http://localhost:5173)

# Production
npm run build        # Build for production (output: dist/)
npm run preview      # Preview production build

# Code Quality
npm run lint         # Run ESLint
```

---

## 🔧 Common Issues & Solutions

### Issue: Port 5173 already in use

**Solution**: Kill the process or use a different port

```bash
# Use different port
npm run dev -- --port 3000
```

### Issue: `npm install` fails

**Solution**: Clear cache and retry

```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Issue: API calls fail with CORS error

**Solution**: This is expected in development. The Vite proxy handles it.

Check `vite.config.js`:
```javascript
server: {
  proxy: {
    '/api/arxiv': {
      target: 'https://export.arxiv.org/api/query',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api\/arxiv/, '')
    }
  }
}
```

### Issue: Blank page after build

**Solution**: Check the base path in `vite.config.js`

```javascript
export default defineConfig({
  base: '/',  // Change if deploying to subdirectory
  // ...
})
```

### Issue: Hot reload not working

**Solution**: Restart the dev server

```bash
# Press Ctrl+C to stop
npm run dev  # Start again
```

---

## 🎨 Customization Quick Tips

### Change Theme Colors

Edit `src/App.css`:

```css
/* Find this line */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Change to your colors */
background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
```

### Change Default Category

Edit `src/pages/PaperList.jsx`:

```javascript
// Find this line
const [selectedCategory, setSelectedCategory] = useState('cs.*');

// Change to specific category
const [selectedCategory, setSelectedCategory] = useState('cs.AI');
```

### Change Number of Papers

Edit `src/services/arxivApi.js`:

```javascript
// Find this line
max_results: 50,

// Change to your preferred number
max_results: 100,
```

---

## 📚 Next Steps

### Learn the Codebase
1. Read [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for architecture
2. Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for features
3. Explore the code starting from `src/App.jsx`

### Make Changes
1. Edit a component in `src/components/`
2. Save the file
3. See changes instantly in browser (hot reload)

### Deploy
1. Read [DEPLOYMENT.md](DEPLOYMENT.md) for deployment options
2. Build: `npm run build`
3. Deploy `dist/` folder to your platform

### Test
1. Use [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
2. Test all features before deploying
3. Check on different devices

---

## 🆘 Getting Help

### Documentation
- [README.md](README.md) - Full documentation
- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - Architecture details
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide

### External Resources
- [React Docs](https://react.dev) - React documentation
- [Vite Docs](https://vitejs.dev) - Vite documentation
- [arXiv API](https://arxiv.org/help/api) - API documentation

### Community
- GitHub Issues - Report bugs
- GitHub Discussions - Ask questions
- Stack Overflow - General React/Vite questions

---

## ✅ Checklist

Before you start coding:

- [ ] Node.js 18+ installed
- [ ] npm installed
- [ ] Code editor ready
- [ ] Repository cloned
- [ ] Dependencies installed (`npm install`)
- [ ] Dev server running (`npm run dev`)
- [ ] App opens in browser
- [ ] All features work

---

## 🎯 Quick Reference

### File Locations

| What | Where |
|------|-------|
| Add component | `src/components/YourComponent.jsx` |
| Add page | `src/pages/YourPage.jsx` |
| Add route | `src/App.jsx` |
| Add API call | `src/services/arxivApi.js` |
| Add styles | `src/components/YourComponent.css` |
| Add constant | `src/constants/yourConstants.js` |

### Import Patterns

```javascript
// React
import { useState, useEffect } from 'react';

// Router
import { useNavigate, useParams } from 'react-router-dom';

// Components
import Navigation from '../components/Navigation';

// Services
import { fetchPapers } from '../services/arxivApi';

// Constants
import { CS_CATEGORIES } from '../constants/categories';

// Styles
import './YourComponent.css';
```

### Common Hooks

```javascript
// State
const [value, setValue] = useState(initialValue);

// Effect
useEffect(() => {
  // Side effect here
}, [dependencies]);

// Navigation
const navigate = useNavigate();
navigate('/path');

// URL params
const { id } = useParams();
```

---

## 🚀 You're Ready!

You now have everything you need to:
- ✅ Run the app locally
- ✅ Understand the structure
- ✅ Make changes
- ✅ Deploy to production

**Happy coding! 🎉**

---

*Need more details? Check out the full [README.md](README.md)*
