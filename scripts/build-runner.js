const { spawnSync } = require('child_process');
const path = require('path');
const os = require('os');

// Target argument parsing
const target = process.argv[2];
const validTargets = ['web', 'mobile', 'all'];

if (!target || !validTargets.includes(target)) {
  console.error(`Error: Invalid or missing target. Please specify one of: ${validTargets.join(', ')}`);
  console.error('Usage: node scripts/build-runner.js <target>');
  process.exit(1);
}

const isWin = os.platform() === 'win32';

function runCommand(command, args, cwd, name) {
  console.log(`\n========================================================================`);
  console.log(`[BUILD RUNNER] Running step: ${name}`);
  console.log(`Command: ${command} ${args.join(' ')}`);
  console.log(`Directory: ${cwd}`);
  console.log(`========================================================================\n`);

  let resolvedCommand = command;
  if (isWin && (command === 'pnpm' || command === 'npm' || command === 'npx')) {
    resolvedCommand = `${command}.cmd`;
  }

  const result = spawnSync(resolvedCommand, args, {
    cwd,
    stdio: 'inherit',
    shell: isWin
  });

  if (result.error) {
    console.error(`\nFailed to start process: ${result.error.message}`);
    printErrorAndExit(name, `${command} ${args.join(' ')}`, result.error.message);
  }

  if (result.status !== 0) {
    printErrorAndExit(name, `${command} ${args.join(' ')}`, `Exit code ${result.status}`);
  }
}

function printErrorAndExit(stepName, cmdString, errorDetail) {
  console.error(`\n\x1b[41m\x1b[37m========================================================================\x1b[0m`);
  console.error(`\x1b[31m[ERROR] BUILD FAILURE in step: ${stepName}\x1b[0m`);
  console.error(`Command: ${cmdString}`);
  console.error(`Detail: ${errorDetail}`);
  console.error(`\n\x1b[33mAI AGENT INSTRUCTION:\x1b[0m`);
  console.error(`A build or lint error was encountered. Please review the terminal logs above`);
  console.error(`to find the exact file and lines causing the failure. Fix the issue in the`);
  console.error(`codebase, and then re-run the build script to verify.`);
  console.error(`\x1b[41m\x1b[37m========================================================================\x1b[0m\n`);
  process.exit(1);
}

const rootDir = path.resolve(__dirname, '..');
const apiDir = path.join(rootDir, 'apps', 'api');
const webDir = path.join(rootDir, 'apps', 'web');
const mobileDir = path.join(rootDir, 'apps', 'mobile');

console.log(`Starting build runner for target: ${target.toUpperCase()}`);

// 1. Build API (Common to both web and mobile)
if (target === 'web' || target === 'mobile' || target === 'all') {
  // Compile all Python files to check syntax
  runCommand('node', ['../../scripts/run-python.js', '-m', 'compileall', 'app'], apiDir, 'API - Python Syntax Compile Check');
  
  // Lint API
  runCommand('pnpm', ['run', 'lint'], apiDir, 'API - Flake8 Linting');

  // Test API (run tests)
  runCommand('pnpm', ['run', 'test'], apiDir, 'API - Pytest Validation');

  // Sweep any leftover test databases (as a backup / verification)
  runCommand('node', ['../../scripts/run-python.js', '../../scripts/cleanup-test-dbs.py'], apiDir, 'API - Sweeping Leftover Test DBs');
}

// 2. Build Web Application UI
if (target === 'web' || target === 'all') {
  // Run Next.js production build
  runCommand('pnpm', ['run', 'build'], webDir, 'Web App UI - Next.js Production Build');
}

// 3. Build Mobile Application UI
if (target === 'mobile' || target === 'all') {
  // Typecheck Mobile app
  runCommand('pnpm', ['exec', 'tsc', '--noEmit'], mobileDir, 'Mobile UI - TypeScript Compile Check');

  // Lint Mobile app
  runCommand('pnpm', ['run', 'lint'], mobileDir, 'Mobile UI - ESLint Check');
}

console.log(`\n\x1b[32m========================================================================\x1b[0m`);
console.log(`\x1b[32m[SUCCESS] Build for target "${target}" completed successfully with zero errors!\x1b[0m`);
console.log(`\x1b[32m========================================================================\x1b[0m\n`);
