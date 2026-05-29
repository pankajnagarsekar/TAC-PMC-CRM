// metro.config.js
const { getDefaultConfig } = require("expo/metro-config");
const path = require('path');
const { FileStore } = require('metro-cache');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

// 1. Watch all files within the workspace
config.watchFolders = [workspaceRoot];

// 2. Ignore build artifacts and temp directories to prevent watch errors
config.resolver.blockList = [
  /.*\.next\/.*/,
  /.*\.turbo\/.*/,
  /.*\/dist\/.*/,
  /.*\/build\/.*/
];

// 3. Let Metro know where to look for find dependencies
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

// Use a stable on-disk store (shared across web/android)
const cacheRoot = process.env.METRO_CACHE_ROOT || path.join(projectRoot, '.metro-cache');
config.cacheStores = [
  new FileStore({ root: path.join(cacheRoot, 'cache') }),
];

// Reduce the number of workers to decrease resource usage
config.maxWorkers = 2;

// 4. Force Metro to resolve react and react-dom to the project local node_modules
// This prevents duplicate React instances in the monorepo
config.resolver.extraNodeModules = {
  'react': path.resolve(projectRoot, 'node_modules/react'),
  'react-dom': path.resolve(projectRoot, 'node_modules/react-dom'),
};

module.exports = config;

