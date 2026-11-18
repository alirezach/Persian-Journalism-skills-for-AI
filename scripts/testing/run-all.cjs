#!/usr/bin/env node
'use strict';
// One entry point for the repository's JavaScript suites and Python discovery.
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const ROOT = path.resolve(__dirname, '../..');
const PYTHON_PROBE = 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)';

function discover(root) {
  const dir = path.join(root, 'tests');
  const entries = fs.readdirSync(dir, {withFileTypes: true});
  const javascript = entries.filter(x => x.isFile() && x.name.endsWith('.test.cjs'))
    .map(x => path.join(dir, x.name)).sort();
  const python = entries.filter(x => x.isFile() && /^test_.*\.py$/.test(x.name))
    .map(x => x.name).sort();
  if (!javascript.length || !python.length) throw new Error('Refusing an empty JavaScript or Python suite.');
  return {javascript, python};
}

function findPython(env, spawn = spawnSync) {
  const candidates = env.PYTHON ? [env.PYTHON] : ['python3', 'python'];
  for (const command of candidates) {
    const result = spawn(command, ['-c', PYTHON_PROBE], {env, encoding: 'utf8', shell: false});
    if (!result.error && !result.signal && result.status === 0) return command;
  }
  throw new Error('Python 3.10+ is required. Set PYTHON to an executable path (not a shell command).');
}

function run({root = ROOT, env = process.env, spawn = spawnSync, log = console.log} = {}) {
  const suites = discover(root);
  const childEnv = {...env, PYTHONDONTWRITEBYTECODE: '1'};
  const python = findPython(childEnv, spawn);
  const commands = suites.javascript.map(file => ({name: path.basename(file), exe: process.execPath, args: [file]}));
  commands.push({name: 'Python unittest discovery (includes real package builds)', exe: python,
    args: ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v']});
  let failures = 0;
  log(`Discovered ${suites.javascript.length} JavaScript suites and ${suites.python.length} top-level Python modules.`);
  for (const command of commands) {
    log(`\n>>> ${command.name}`);
    const result = spawn(command.exe, command.args,
      {cwd: root, env: childEnv, stdio: 'inherit', shell: false});
    if (result.error || result.signal || result.status !== 0) {
      failures++;
      log(`FAILED ${command.name}: ${result.error ? result.error.message : result.signal || result.status}`);
    }
  }
  log(`\nSuite commands: ${commands.length - failures} passed, ${failures} failed. See suite output for check counts.`);
  return failures ? 1 : 0;
}

module.exports = {discover, findPython, run};
if (require.main === module) {
  try {
    if (process.argv.length > 2) throw new Error('No partial-suite flags are accepted. Run npm test for the full suite.');
    process.exitCode = run();
  } catch (error) {
    console.error(`Test runner failed: ${error.message}`);
    process.exitCode = 1;
  }
}
