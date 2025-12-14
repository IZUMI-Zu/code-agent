# arXiv CS Daily

A streamlined, modern web interface for tracking daily Computer Science preprints from arXiv.

## Features

- **Domain-Specific Navigation**: Quickly filter papers by major Computer Science subfields (AI, CV, NLP, etc.).
- **Daily Updated Lists**: View the most recent submissions with a clean, clutter-free interface.
- **Detailed Paper Views**:
  - Read abstracts.
  - Direct links to PDFs.
  - One-click BibTeX citation generation.

## tech Stack

- **Frontend**: React 18 + TypeScript
- **Build Tool**: Vite
- **Routing**: React Router DOM
- **Styling**: Custom CSS (responsive, clean design)
- **Data Source**: arXiv Public API

## Getting Started

1.  Install dependencies:
    ```bash
    npm install
    ```

2.  Start the development server:
    ```bash
    npm run dev
    ```

3.  Open your browser at `http://localhost:5173`.

## Building for Production

To create a production build:

```bash
npm run build
```

The artifacts will be generated in the `dist/` directory.