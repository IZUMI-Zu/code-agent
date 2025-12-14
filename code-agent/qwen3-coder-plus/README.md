---
agent generated with REASONING_MODEL=qwen/qwen3-coder-plus and LIGHTWEIGHT_MODEL=openai/gpt-4o-mini, around 3 rounds human interact, and the code still need human adjust 3 times.
---

# arXiv CS Daily

A web application for browsing daily computer science research papers from arXiv.

## Features

- View latest computer science papers from arXiv
- Browse papers by category (AI, ML, CV, CL, etc.)
- Search papers by keywords
- View paper details including abstract and metadata
- Responsive design for desktop and mobile devices

## Technologies Used

- React
- React Router
- arXiv API
- CSS3
- Vite (build tool)

## Getting Started

### Prerequisites

- Node.js (version 14 or higher)
- npm or yarn

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/arxiv-cs-daily.git
   ```

2. Navigate to the project directory:
   ```
   cd arxiv-cs-daily
   ```

3. Install dependencies:
   ```
   npm install
   ```

### Running the Application

To start the development server:
```
npm run dev
```

The application will be available at `http://localhost:5173`

### Building for Production

To create a production build:
```
npm run build
```

To preview the production build:
```
npm run preview
```

## Project Structure

```
arxiv-cs-daily/
├── public/
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── about/
│   │   ├── categories/
│   │   ├── details/
│   │   ├── errors/
│   │   ├── layout/
│   │   ├── navigation/
│   │   └── papers/
│   ├── hooks/
│   ├── pages/
│   ├── services/
│   ├── utils/
│   ├── App.css
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
├── index.html
└── package.json
```

## Available Scripts

- `npm run dev` - Starts the development server
- `npm run build` - Creates a production build
- `npm run preview` - Previews the production build locally
- `npm run lint` - Runs ESLint on the project

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [arXiv](https://arxiv.org/) for providing the API and hosting research papers
- [React](https://reactjs.org/) for the UI library
- [Vite](https://vitejs.dev/) for the build tool
