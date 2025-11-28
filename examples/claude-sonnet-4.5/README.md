# 📚 arXiv CS Daily

A modern, responsive web application for browsing the latest Computer Science papers from arXiv. Built with React and Vite, featuring a beautiful gradient UI and comprehensive paper details.

![arXiv CS Daily](https://img.shields.io/badge/React-19.2.0-blue)
![Vite](https://img.shields.io/badge/Vite-7.2.4-purple)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

### 📖 Browse Papers
- **Category Filtering**: 20+ Computer Science categories (AI, ML, CV, NLP, etc.)
- **Today's Papers**: Quick filter for papers published today
- **Responsive Grid**: Adapts to mobile, tablet, and desktop screens
- **Beautiful Cards**: Modern design with gradient accents and hover effects

### 📄 Paper Details
- **Full Information**: Title, authors, affiliations, abstract, categories
- **Direct Links**: PDF download and arXiv abstract page
- **Citation Tools**: Generate BibTeX and APA citations with one click
- **Copy to Clipboard**: Easy citation copying with visual feedback

### 🎨 Modern UI/UX
- **Gradient Theme**: Professional purple gradient design
- **Smooth Animations**: Transitions and hover effects
- **Loading States**: Elegant spinners during data fetch
- **Error Handling**: Helpful messages with retry options
- **Mobile-First**: Fully responsive on all devices

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd arxiv-cs-daily

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
arxiv-cs-daily/
├── src/
│   ├── components/          # Reusable components
│   │   ├── Navigation.jsx   # Category navigation bar
│   │   ├── PaperCard.jsx    # Paper preview card
│   │   └── CitationTools.jsx # Citation generator
│   ├── pages/               # Page components
│   │   ├── PaperList.jsx    # Main listing page
│   │   └── PaperDetail.jsx  # Paper detail page
│   ├── services/            # API services
│   │   └── arxivApi.js      # arXiv API integration
│   ├── constants/           # App constants
│   │   └── categories.js    # CS categories data
│   ├── App.jsx              # Main app with routing
│   └── main.jsx             # Entry point
├── vite.config.js           # Vite configuration
└── package.json             # Dependencies
```

## 🎯 Available Categories

- **All CS** - All Computer Science papers
- **AI** - Artificial Intelligence
- **CL** - Computation and Language (NLP)
- **CV** - Computer Vision and Pattern Recognition
- **LG** - Machine Learning
- **NE** - Neural and Evolutionary Computing
- **RO** - Robotics
- **SE** - Software Engineering
- **DB** - Databases
- **DC** - Distributed, Parallel, and Cluster Computing
- **IR** - Information Retrieval
- **NI** - Networking and Internet Architecture
- **OS** - Operating Systems
- **PF** - Performance
- **PL** - Programming Languages
- **CR** - Cryptography and Security
- **GT** - Computer Science and Game Theory
- **HC** - Human-Computer Interaction
- **MA** - Multiagent Systems
- **SI** - Social and Information Networks
- **SY** - Systems and Control

## 🛠️ Technologies

- **React 19.2.0** - UI framework
- **React Router DOM 7.9.6** - Client-side routing
- **Axios 1.13.2** - HTTP client for API calls
- **date-fns 4.1.0** - Date formatting utilities
- **Vite 7.2.4** - Build tool and dev server
- **CSS3** - Modern styling with gradients and animations

## 🌐 API Integration

### Development Mode
The app uses a Vite proxy to bypass CORS restrictions:
- Local endpoint: `/api/arxiv`
- Proxies to: `https://export.arxiv.org/api/query`

### Production Mode
For production deployment, you have two options:

1. **Backend Proxy** (Recommended)
   - Set up a backend server to proxy arXiv API requests
   - Update `arxivApi.js` to use your backend endpoint

2. **Direct API Calls**
   - May encounter CORS issues in some browsers
   - arXiv API allows some cross-origin requests

## 📝 Usage Examples

### Browse Papers by Category
1. Click on a category in the navigation bar
2. Papers will load automatically
3. Use "Today's Papers" toggle to filter recent papers

### View Paper Details
1. Click on any paper card
2. View full abstract, authors, and metadata
3. Download PDF or visit arXiv page
4. Generate citations in BibTeX or APA format

### Copy Citations
1. Open a paper detail page
2. Click "Show Citation Tools"
3. Choose BibTeX or APA format
4. Click "Copy" button
5. Paste into your document

## 🎨 Customization

### Change Theme Colors
Edit the gradient colors in CSS files:
```css
/* Primary gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Adjust to your preferred colors */
background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
```

### Add More Categories
Edit `src/constants/categories.js`:
```javascript
export const CS_CATEGORIES = [
  // Add your category
  {
    id: 'cs.XX',
    name: 'Your Category',
    description: 'Description here'
  },
  // ...
];
```

## 🐛 Known Issues & Limitations

1. **CORS in Production**: Direct arXiv API calls may fail without backend proxy
2. **Rate Limiting**: arXiv recommends 3 seconds between requests
3. **No Caching**: Data refetches on each navigation (consider adding React Query)
4. **XML Parsing**: Relies on browser DOMParser (supported in all modern browsers)

## 🚧 Future Enhancements

- [ ] Search functionality
- [ ] Pagination for large result sets
- [ ] Favorites/bookmarks system
- [ ] Dark mode toggle
- [ ] Export citations to .bib file
- [ ] Date range filtering
- [ ] Sort options (date, relevance, citations)
- [ ] Share paper links
- [ ] Progressive Web App (PWA) support
- [ ] Backend API for better CORS handling

## 📄 License

MIT License - feel free to use this project for personal or commercial purposes.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

For questions or suggestions, please open an issue on GitHub.

## 🙏 Acknowledgments

- [arXiv](https://arxiv.org/) for providing the free API
- [Vite](https://vitejs.dev/) for the amazing build tool
- [React](https://react.dev/) for the UI framework

---

**Made with ❤️ and React**

*Happy paper browsing! 📚✨*
