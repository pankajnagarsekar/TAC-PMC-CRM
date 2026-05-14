const { spawnSync } = require('child_process');
const path = require('path');
const os = require('os');

// Resolve the root .venv path
const venvPath = path.resolve(__dirname, '..', '.venv');
const pythonPath = os.platform() === 'win32' 
  ? path.join(venvPath, 'Scripts', 'python.exe')
  : path.join(venvPath, 'bin', 'python');

const args = process.argv.slice(2);

// Run the python command
const result = spawnSync(pythonPath, args, { 
    stdio: 'inherit',
    // On Windows, shell: true is often needed for path resolution if not using absolute paths
    // but here we are using absolute path, so let's try without first.
    shell: os.platform() === 'win32'
});

if (result.error) {
    console.error('Failed to start python process:', result.error.message);
    process.exit(1);
}

process.exit(result.status ?? 0);
