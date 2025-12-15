# Code Agent Examples

Complete arXiv CS Daily applications comparing Code Agent (with different models) against industry baseline tools.

## Project Overview

All examples implement identical requirements to enable fair comparison across different AI coding assistants and LLM providers.

### Original Requirements

The following system prompt was used across all implementations:

> Build an "arXiv CS Daily" webpage with three core functionalities to deliver a streamlined experience for tracking daily computer science preprints:
>
> **Domain-Specific Navigation System**
> Implement categorized navigation based on arXiv's primary CS fields (cs.AI, cs.TH, cs.SY, etc.). This enables users to quickly filter and switch between major subfields, ensuring easy access to their areas of interest.
>
> **Daily Updated Paper List**
> Create a daily updated list displaying the latest papers with essential details only. Each entry may include the paper title (hyperlinked to its detail page), submission time, and the specific arXiv field tag (e.g., [cs.CV]).
>
> **Dedicated Paper Detail Page**
> Design a comprehensive detail page that centralizes critical resources: direct PDF link (hosted on arXiv), core metadata (title, authors with affiliations, submission date), and citation generation tools supporting common formats (BibTeX, standard academic citation) with one-click copy functionality.

## Project Comparison

### Code Agent Examples (Multi-Model)

| Dimension             | Claude Sonnet 4.5   | DeepSeek Chat v3                | Qwen3 Coder Plus                |
| --------------------- | ------------------- | ------------------------------- | ------------------------------- |
| **Tool**              | Code Agent          | Code Agent                      | Code Agent                      |
| **Reasoning Model**   | claude-sonnet-4.5   | deepseek-chat                   | qwen/qwen3-coder-plus           |
| **Lightweight Model** | gpt-4o-mini         | deepseek-chat                   | gpt-4o-mini                     |
| **Language**          | JavaScript          | TypeScript                      | JavaScript                      |
| **Human Interaction** | 3 chat rounds       | 2 chat rounds                   | 3 rounds + 3 manual adjustments |
| **Manual Fixes**      | 0                   | 0                               | 3                               |
| **Issues Resolved**   | CORS (prompted)     | CORS (Node) + Tailwind          | CORS (prompted)                 |
| **Backend Included**  | No                  | Yes (Node.js proxy)             | No                              |
| **Total LOC**         | ~1528               | ~2396                           | ~1840                           |

### Baseline Tools (Industry Comparison)

| Dimension             | Claude Code         | Gemini CLI          |
| --------------------- | ------------------- | ------------------- |
| **Tool**              | Claude Code (CLI)   | gemini-cli          |
| **Model**             | claude-sonnet-4.5   | gemini-3-pro        |
| **Language**          | TypeScript          | TypeScript          |
| **Human Interaction** | 2 chat rounds       | 3 chat rounds       |
| **Manual Fixes**      | 0                   | 0                   |
| **Tool Calls**        | N/A                 | 35 (100% success)   |
| **Issues Resolved**   | CORS (auto)         | CORS + API params   |
| **Backend Included**  | Yes (Express)       | No                  |
| **Total LOC**         | ~791                | ~704                |

## Common Features

All four projects implement complete arXiv CS Daily applications:

### Core Functionality

- Browse arXiv Computer Science papers
- Filter by category (AI/ML/CV/NLP/etc. 20+ categories)
- View paper details (abstract, authors, metadata)
- Generate citations (BibTeX/APA)
- Responsive design (desktop/tablet/mobile)

### Tech Stack

- **Frontend Framework**: React 19.x
- **Routing**: React Router DOM 7.x
- **Build Tool**: Vite 7.x
- **HTTP Client**: Axios
- **API**: arXiv Export API (XML)

## Quick Start

### Code Agent Examples

**1. Claude Sonnet 4.5 Version**

```bash
cd code-agent/claude-sonnet-4.5
npm install
npm run dev
```

**2. DeepSeek Chat v3 Version**

```bash
cd code-agent/deepseek-v3
npm install
npm run dev
# In a separate terminal, start the proxy server
cd code-agent/deepseek-v3/server
npm install && npm start
```

> Includes Node.js backend proxy (`server/server.js`)

**3. Qwen3 Coder Plus Version**

```bash
cd code-agent/qwen3-coder-plus
npm install
npm run dev
```

### Baseline Tools

**4. Claude Code**

```bash
cd baseline/claude-code
npm install
npm run dev
```

> Includes Express backend proxy for production (`npm start`)

**5. Gemini CLI**

```bash
cd baseline/gemini
npm install
npm run dev
```

All applications run at `http://localhost:5173` by default.

## Architecture Differences

### Code Agent Examples

#### Claude Sonnet 4.5 Version

**Directory Structure**:

```bash
src/
├── components/          # Flat component layer
│   ├── Navigation.jsx
│   ├── PaperCard.jsx
│   └── CitationTools.jsx
├── pages/              # Page components
│   ├── PaperList.jsx
│   └── PaperDetail.jsx
├── services/           # API calls
│   └── arxivApi.js
└── constants/          # Configuration
    └── categories.js
```

**Observations**:

- 4 top-level directories in src/
- Components not grouped by feature
- Service layer separated
- Constants centralized

#### Qwen3 Coder Plus Version

**Directory Structure**:

```bash
src/
├── components/         # Feature-grouped components
│   ├── about/
│   ├── categories/
│   ├── details/
│   ├── errors/
│   ├── navigation/
│   └── papers/
├── hooks/             # Custom hooks
├── services/          # API calls
├── utils/             # Utility functions
└── pages/             # Page assembly
```

**Observations**:

- 5 top-level directories in src/
- Components grouped by feature domain
- Separate hooks/ and utils/ directories
- More granular file splitting

#### DeepSeek Chat v3 Version

**Directory Structure**:

```bash
src/
├── components/         # UI components
├── pages/             # Page components
├── services/          # API services
├── test/              # Tests
└── utils/             # Utilities
server/                # Backend Proxy
└── server.js
```

**Observations**:

- 5 top-level directories in src/
- Separate backend proxy server (Node.js)
- TypeScript implementation
- Includes test directory
- Agent self-corrected Tailwind CSS version issues

### Baseline Tools

#### Claude Code

**Directory Structure**:

```bash
src/
├── components/         # UI components
│   ├── CategoryNav.tsx
│   ├── PaperList.tsx
│   └── PaperDetail.tsx
├── pages/             # Page containers
│   ├── HomePage.tsx
│   └── PaperPage.tsx
├── services/          # API integration
│   └── arxiv.ts
├── types/             # TypeScript definitions
│   └── index.ts
└── styles/            # CSS files
    └── index.css
```

**Observations**:

- 5 top-level directories in src/
- TypeScript for type safety
- Separate types/ directory for interfaces
- Backend proxy (server.js) at project root
- Native CSS without framework dependencies

#### Gemini CLI

**Directory Structure**:

```bash
src/
├── components/         # UI components with co-located CSS
│   ├── Layout.tsx/css
│   ├── Navbar.tsx/css
│   ├── PaperDetail.tsx/css
│   └── PaperList.tsx/css
├── services/          # API integration
│   └── arxivApi.ts
├── types/             # TypeScript definitions
│   └── index.ts
├── App.tsx/css        # Root component
└── main.tsx           # Entry point
```

**Observations**:

- 3 top-level directories in src/
- Co-located CSS with components
- React 19.2.0 (latest)
- Minimal structure, high cohesion
- Vite proxy configured for CORS

## Generation Process

### Agent Workflow

```bash
User Requirements
   ↓
Planner Analyzes → Generate task plan
   ↓
Coder Implements → Write core functionality
   ↓
Reviewer Checks → Code quality review
   ↓
Human Confirms → Tool execution authorization
   ↓
Delivery Complete
```

### Human Interaction Points

- Tool execution confirmation (file writes, shell commands)
- Manual adjustments (Qwen3: 3 times, Claude: 0 times)
- Style and copy refinements

## Performance Comparison

### Lines of Code

**Code Agent Examples**:

| Model                  | Total LOC | JSX/TSX | CSS  | Language   | React Version |
| ---------------------- | --------- | ------- | ---- | ---------- | ------------- |
| **Claude Sonnet 4.5**  | ~1528     | ~441    | ~794 | JavaScript | 19.x          |
| **DeepSeek Chat v3**   | ~2396     | ~1758   | ~50  | TypeScript | 19.x          |
| **Qwen3 Coder Plus**   | ~1840     | ~529    | ~1026| JavaScript | 19.x          |

**Baseline Tools**:

| Tool              | Total LOC | JSX/TSX | CSS | Language   | React Version |
| ----------------- | --------- | ------- | --- | ---------- | ------------- |
| **Claude Code**   | ~791      | ~311    | ~304| TypeScript | 18.x          |
| **Gemini CLI**    | ~704      | ~237    | ~312| TypeScript | 19.2 (latest) |

**Key Observations**:

- **Gemini CLI** produces the most concise code:
  - Co-located CSS reduces file overhead
  - Minimal component hierarchy
  - Direct API integration without abstraction layers
- **Claude Code** balances structure and simplicity
- **Code Agent** versions include more UI refinements and feature completeness

## Improvement Opportunities

### 1. CORS Handling

**Code Agent**:
- **Claude Sonnet 4.5**: Required explicit user prompt to configure Vite proxy
- **DeepSeek Chat v3**: ✅ Auto-implemented Node.js backend proxy
- **Qwen3 Coder Plus**: Required explicit user prompt to configure Vite proxy

**Baseline Tools**:
- **Claude Code**: ✅ Auto-detected (Vite proxy + Express backend)
- **Gemini CLI**: ✅ Auto-detected and configured (Vite proxy)

### 2. Caching Strategy

**Problem**: Data refetched on every navigation

**Solution**:

```javascript
// Use React Query
import { useQuery } from '@tanstack/react-query';

const { data } = useQuery({
  queryKey: ['papers', category],
  queryFn: () => fetchPapers(category),
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

### 3. Performance Optimization

**Problem**: Large list rendering may lag

**Solution**:

```javascript
// Virtual scrolling
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={papers.length}
  itemSize={120}
>
  {PaperRow}
</FixedSizeList>
```

## Usage Notes

### Running the Examples

Both projects require Node.js 18+ and standard React development setup. The examples run independently without shared dependencies.

---

**Back to**: [Main README](../README.md)
