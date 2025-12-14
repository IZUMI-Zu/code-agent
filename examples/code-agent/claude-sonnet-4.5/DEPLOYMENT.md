# 🚀 Deployment Guide

This guide covers deploying the arXiv CS Daily application to various platforms.

## 📋 Pre-Deployment Checklist

- [ ] Test the production build locally
- [ ] Verify all API calls work
- [ ] Check responsive design on different devices
- [ ] Test all navigation and routing
- [ ] Ensure error handling works properly

## 🏗️ Build for Production

```bash
# Install dependencies
npm install

# Create production build
npm run build

# Preview production build locally
npm run preview
```

The build output will be in the `dist/` directory.

## 🌐 Deployment Options

### Option 1: Vercel (Recommended)

**Pros**: Zero config, automatic HTTPS, global CDN, free tier
**Cons**: May need backend for CORS handling

#### Steps:

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Deploy**
   ```bash
   vercel
   ```

3. **Configure (vercel.json)**
   ```json
   {
     "rewrites": [
       {
         "source": "/api/arxiv/:path*",
         "destination": "https://export.arxiv.org/api/query/:path*"
       }
     ]
   }
   ```

4. **Environment Variables** (if needed)
   - Set in Vercel dashboard
   - Or use `.env.production`

#### Alternative: GitHub Integration
1. Push code to GitHub
2. Import repository in Vercel dashboard
3. Deploy automatically on push

---

### Option 2: Netlify

**Pros**: Easy setup, free tier, form handling, serverless functions
**Cons**: May need serverless function for CORS

#### Steps:

1. **Install Netlify CLI**
   ```bash
   npm install -g netlify-cli
   ```

2. **Deploy**
   ```bash
   netlify deploy --prod
   ```

3. **Configure (_redirects file)**
   Create `public/_redirects`:
   ```
   /api/arxiv/*  https://export.arxiv.org/api/query/:splat  200
   ```

4. **Or use netlify.toml**
   ```toml
   [[redirects]]
     from = "/api/arxiv/*"
     to = "https://export.arxiv.org/api/query/:splat"
     status = 200
   ```

#### Alternative: Drag & Drop
1. Build locally: `npm run build`
2. Drag `dist/` folder to Netlify dashboard

---

### Option 3: GitHub Pages

**Pros**: Free, simple, integrated with GitHub
**Cons**: Static only, CORS issues, requires hash routing

#### Steps:

1. **Install gh-pages**
   ```bash
   npm install --save-dev gh-pages
   ```

2. **Update package.json**
   ```json
   {
     "homepage": "https://yourusername.github.io/arxiv-cs-daily",
     "scripts": {
       "predeploy": "npm run build",
       "deploy": "gh-pages -d dist"
     }
   }
   ```

3. **Update vite.config.js**
   ```javascript
   export default defineConfig({
     base: '/arxiv-cs-daily/',
     // ... rest of config
   })
   ```

4. **Deploy**
   ```bash
   npm run deploy
   ```

5. **Enable GitHub Pages**
   - Go to repository settings
   - Enable Pages from `gh-pages` branch

**Note**: GitHub Pages doesn't support proxying, so you'll need to handle CORS differently.

---

### Option 4: Railway

**Pros**: Backend support, databases, automatic HTTPS
**Cons**: Requires backend setup for proxy

#### Steps:

1. **Create railway.json**
   ```json
   {
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "npm run preview",
       "restartPolicyType": "ON_FAILURE"
     }
   }
   ```

2. **Deploy via CLI**
   ```bash
   npm install -g @railway/cli
   railway login
   railway init
   railway up
   ```

3. **Or connect GitHub**
   - Link repository in Railway dashboard
   - Auto-deploy on push

---

### Option 5: Custom Server (VPS/Cloud)

**Pros**: Full control, can add backend
**Cons**: More setup, maintenance required

#### Using Nginx:

1. **Build the app**
   ```bash
   npm run build
   ```

2. **Copy dist/ to server**
   ```bash
   scp -r dist/* user@server:/var/www/arxiv-cs-daily/
   ```

3. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       root /var/www/arxiv-cs-daily;
       index index.html;

       # SPA routing
       location / {
           try_files $uri $uri/ /index.html;
       }

       # Proxy arXiv API
       location /api/arxiv/ {
           proxy_pass https://export.arxiv.org/api/query/;
           proxy_set_header Host export.arxiv.org;
       }
   }
   ```

4. **Restart Nginx**
   ```bash
   sudo systemctl restart nginx
   ```

---

## 🔧 Handling CORS in Production

### Method 1: Backend Proxy (Recommended)

Create a simple Express.js proxy:

```javascript
// server.js
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.static('dist'));

app.get('/api/arxiv', async (req, res) => {
  try {
    const response = await axios.get('https://export.arxiv.org/api/query', {
      params: req.query
    });
    res.send(response.data);
  } catch (error) {
    res.status(500).send(error.message);
  }
});

app.get('*', (req, res) => {
  res.sendFile(__dirname + '/dist/index.html');
});

app.listen(3000);
```

### Method 2: Serverless Function

**Vercel Function** (`api/arxiv.js`):
```javascript
export default async function handler(req, res) {
  const response = await fetch(
    `https://export.arxiv.org/api/query?${new URLSearchParams(req.query)}`
  );
  const data = await response.text();
  res.status(200).send(data);
}
```

**Netlify Function** (`netlify/functions/arxiv.js`):
```javascript
exports.handler = async (event) => {
  const response = await fetch(
    `https://export.arxiv.org/api/query?${event.rawQuery}`
  );
  const data = await response.text();
  return {
    statusCode: 200,
    body: data
  };
};
```

### Method 3: Update API Service

If CORS works in production, update `src/services/arxivApi.js`:

```javascript
const API_BASE_URL = import.meta.env.PROD 
  ? 'https://export.arxiv.org/api/query'
  : '/api/arxiv';
```

---

## 🔐 Environment Variables

Create `.env.production`:

```env
VITE_API_BASE_URL=https://your-backend.com/api/arxiv
VITE_APP_TITLE=arXiv CS Daily
```

Access in code:
```javascript
const apiUrl = import.meta.env.VITE_API_BASE_URL;
```

---

## 📊 Performance Optimization

### 1. Enable Compression
Most platforms enable this by default, but verify:
- Gzip/Brotli compression
- Asset caching headers

### 2. Lazy Loading
Already implemented via React Router's lazy loading.

### 3. CDN
Use a CDN for static assets:
- Vercel/Netlify provide this automatically
- For custom servers, use Cloudflare or similar

### 4. Code Splitting
Vite handles this automatically, but verify:
```bash
npm run build -- --report
```

---

## 🧪 Testing Production Build

Before deploying:

```bash
# Build
npm run build

# Preview locally
npm run preview

# Test on different devices
# Use ngrok for external testing
npx ngrok http 4173
```

---

## 📈 Monitoring & Analytics

### Add Google Analytics

1. **Install**
   ```bash
   npm install react-ga4
   ```

2. **Initialize in main.jsx**
   ```javascript
   import ReactGA from 'react-ga4';
   ReactGA.initialize('G-XXXXXXXXXX');
   ```

### Add Error Tracking (Sentry)

1. **Install**
   ```bash
   npm install @sentry/react
   ```

2. **Initialize**
   ```javascript
   import * as Sentry from "@sentry/react";
   Sentry.init({ dsn: "your-dsn" });
   ```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm ci
      - run: npm run build
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dist
```

---

## 🆘 Troubleshooting

### Issue: Blank page after deployment
- Check browser console for errors
- Verify `base` in vite.config.js matches deployment path
- Ensure all routes use BrowserRouter correctly

### Issue: API calls failing
- Check CORS configuration
- Verify proxy/serverless function is working
- Test API endpoint directly

### Issue: 404 on refresh
- Configure server for SPA routing
- Add redirects/rewrites for all routes to index.html

### Issue: Assets not loading
- Check `base` path in vite.config.js
- Verify asset paths are relative
- Check network tab for 404s

---

## 📚 Additional Resources

- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [React Router Deployment](https://reactrouter.com/en/main/guides/deployment)
- [Vercel Documentation](https://vercel.com/docs)
- [Netlify Documentation](https://docs.netlify.com/)

---

**Happy Deploying! 🚀**
