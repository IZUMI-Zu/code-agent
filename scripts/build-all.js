const shell = require('shelljs');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const distDir = path.join(rootDir, 'dist');

// Define projects and their deployment paths
const projects = [
  { path: 'landing', urlPath: '/', isLanding: true, outputDir: 'out' }, // Next.js landing page
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

  let buildCmd, envVars, projectDist;

  if (project.isLanding) {
    // Next.js landing page
    buildCmd = 'npm run build';
    envVars = process.env;
    projectDist = path.join(projectPath, project.outputDir || 'out');
  } else {
    // Vite projects
    buildCmd = `npm run build -- --base=${project.urlPath}/`;
    envVars = { ...process.env, VITE_API_BASE_URL: '/api' };
    projectDist = path.join(projectPath, 'dist');
  }

  const result = shell.exec(buildCmd, { env: envVars });

  if (result.code !== 0) {
    console.error(`❌ Build failed for ${project.path}`);
    return;
  }

  // Move dist
  const targetDir = project.isLanding ? distDir : path.join(distDir, project.urlPath);
  if (!project.isLanding) {
    shell.mkdir('-p', targetDir);
  }

  if (fs.existsSync(projectDist)) {
    shell.cp('-R', `${projectDist}/*`, targetDir);
    console.log(`✅ Deployed to ${project.urlPath}`);
  } else {
    console.error(`❌ Dist folder not found for ${project.path}`);
  }
});

console.log('\n✨ All builds completed.');
