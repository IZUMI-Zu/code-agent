const shell = require('shelljs');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const distDir = path.join(rootDir, 'dist');

// Define projects and their deployment paths
const projects = [
  { path: 'baseline/claude-code', urlPath: '/baseline/claude-code' },
  { path: 'baseline/gemini', urlPath: '/baseline/gemini' },
  { path: 'code-agent/claude-sonnet-4.5', urlPath: '/code-agent/claude-sonnet-4.5' },
  { path: 'code-agent/deepseek-v3', urlPath: '/code-agent/deepseek-v3' },
  { path: 'code-agent/qwen3-coder-plus', urlPath: '/code-agent/qwen3-coder-plus', installFlags: '--legacy-peer-deps' }
];

// Clean and create dist
if (fs.existsSync(distDir)) {
  shell.rm('-rf', distDir);
}
shell.mkdir('-p', distDir);

// Build Landing Page (Simple Copy for now, or generate)
const landingPageSrc = path.join(rootDir, 'index.html');
if (fs.existsSync(landingPageSrc)) {
  shell.cp(landingPageSrc, path.join(distDir, 'index.html'));
} else {
  // Generate a basic landing page if it doesn't exist
  const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COMP7103 Examples</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; line-height: 1.5; }
        h1 { border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .card a { text-decoration: none; color: inherit; display: block; }
        .card h2 { margin: 0 0 0.5rem 0; color: #2563eb; }
        .tag { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem; font-weight: 500; margin-right: 0.5rem; }
        .tag-baseline { background: #f3f4f6; color: #374151; }
        .tag-agent { background: #eff6ff; color: #1e40af; }
    </style>
</head>
<body>
    <h1>COMP7103 Project Examples</h1>
    <p>Select an implementation to view:</p>
    
    <div id="projects">
        ${projects.map(p => `
        <div class="card">
            <a href="${p.urlPath}/">
                <h2>${p.path.split('/').pop()}</h2>
                <p><span class="tag ${p.path.startsWith('baseline') ? 'tag-baseline' : 'tag-agent'}">${p.path.split('/')[0]}</span> ${p.path}</p>
            </a>
        </div>
        `).join('')}
    </div>
</body>
</html>
  `;
  fs.writeFileSync(path.join(distDir, 'index.html'), htmlContent);
}

// Build Projects
projects.forEach(project => {
  const projectPath = path.join(rootDir, project.path);
  console.log(`\n🚀 Building ${project.path}...`);
  
  if (!fs.existsSync(projectPath)) {
    console.warn(`⚠️ Project directory not found: ${project.path}`);
    return;
  }

  shell.cd(projectPath);
  
  // Install dependencies
  console.log('Installing dependencies...');
  shell.exec(`npm install --no-audit --no-fund ${project.installFlags || ''}`, { silent: true });

  // Build
  console.log('Building...');
  // Pass base path to Vite. 
  // Note: We force VITE_API_BASE_URL to /api for uniform proxy access if supported
  const buildCmd = `npm run build -- --base=${project.urlPath}/`;
  const envVars = { ...process.env, VITE_API_BASE_URL: '/api' };
  
  const result = shell.exec(buildCmd, { env: envVars });
  
  if (result.code !== 0) {
    console.error(`❌ Build failed for ${project.path}`);
    return; // Continue to next project? Or exit? Let's continue.
  }

  // Move dist
  const targetDir = path.join(distDir, project.urlPath);
  shell.mkdir('-p', targetDir);
  
  // Most Vite apps output to 'dist'
  const projectDist = path.join(projectPath, 'dist');
  if (fs.existsSync(projectDist)) {
    shell.cp('-R', `${projectDist}/*`, targetDir);
    console.log(`✅ Deployed to ${project.urlPath}`);
  } else {
    console.error(`❌ Dist folder not found for ${project.path}`);
  }
});

console.log('\n✨ All builds completed.');
