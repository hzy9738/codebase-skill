#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Version
const VERSION = '0.6.0';

// Find codebase-memory-mcp
function findCodebaseMemoryMcp() {
  const possiblePaths = [
    // Check PATH
    'codebase-memory-mcp',
    // Common locations
    path.join(process.env.HOME || '', '.local/bin/codebase-memory-mcp'),
    '/usr/local/bin/codebase-memory-mcp',
    '/opt/homebrew/bin/codebase-memory-mcp',
  ];

  for (const binaryPath of possiblePaths) {
    try {
      // Check if exists and is executable
      if (fs.existsSync(binaryPath)) {
        const stats = fs.statSync(binaryPath);
        if (stats.isFile() && (stats.mode & 0o111)) {
          return binaryPath;
        }
      }
    } catch (error) {
      // Continue checking other paths
    }
  }

  return null;
}

// Main CLI function
async function main() {
  const args = process.argv.slice(2);
  
  // Check for version flag
  if (args.includes('--version') || args.includes('-v')) {
    console.log(`codebase ${VERSION}`);
    return;
  }
  
  // Check for help flag
  if (args.includes('--help') || args.includes('-h') || args.length === 0) {
    printHelp();
    return;
  }
  
  // Find codebase-memory-mcp
  const cbmBinary = findCodebaseMemoryMcp();
  if (!cbmBinary) {
    console.error('Error: codebase-memory-mcp not found.');
    console.error('Please install it first:');
    console.error('  curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash');
    process.exit(1);
  }

  // Prepare arguments for codebase-memory-mcp cli
  const cbmArgs = ['cli', ...args];
  
  // Spawn the process
  const child = spawn(cbmBinary, cbmArgs, {
    stdio: 'inherit',
    env: process.env,
  });

  // Handle process exit
  child.on('close', (code) => {
    process.exit(code || 0);
  });

  child.on('error', (error) => {
    console.error('Error executing codebase-memory-mcp:', error.message);
    process.exit(1);
  });
}

// Print help message
function printHelp() {
  console.log(`codebase ${VERSION}`);
  console.log('Local repository-scoped wrapper around codebase-memory-mcp');
  console.log();
  console.log('Usage:');
  console.log('  codebase [command] [options]');
  console.log();
  console.log('Commands:');
  console.log('  install-runtime     Install codebase-memory-mcp into ~/.local/bin');
  console.log('  status              Show local index status for the current session');
  console.log('  index               Build the local index under .codebase/<session>');
  console.log('  refresh             Rebuild only when local index is stale');
  console.log('  projects            List indexed projects in local cache');
  console.log('  reset               Delete the local .codebase/<session> index');
  console.log('  self-check          Verify environment and repo wiring');
  console.log('  func                Search indexed functions and methods');
  console.log('  calls               Show callers and callees for a symbol');
  console.log('  snippet             Show source for a symbol');
  console.log('  search-graph        Direct wrapper around search_graph');
  console.log('  trace-path          Direct wrapper around trace_path');
  console.log('  search-code         Text/code search with graph-aware ranking');
  console.log('  query-graph         Run a graph query directly');
  console.log('  detect-changes      Show changed files and impacted symbols');
  console.log('  architecture        Get architecture summary');
  console.log('  schema              Get graph schema summary');
  console.log('  index-status        Get upstream index status');
  console.log('  adr                 Manage ADR content via upstream manage_adr');
  console.log('  ingest-traces       Ingest runtime traces from a JSON file');
  console.log();
  console.log('Options:');
  console.log('  -v, --version       Show version');
  console.log('  -h, --help          Show this help message');
  console.log('  -s, --session       Session ID override');
}

// Always run main
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});

module.exports = { main, findCodebaseMemoryMcp, VERSION };