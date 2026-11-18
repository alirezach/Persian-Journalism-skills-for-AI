#!/usr/bin/env node
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const root = path.resolve(__dirname,'..');
const read = name => fs.readFileSync(path.join(root,name),'utf8');
const pkg=JSON.parse(read('package.json'));
const lock=JSON.parse(read('package-lock.json'));
const workflow=yaml.load(read('.github/workflows/test.yml'));
let passed=0, failed=0;
function test(name,fn){try{fn();passed++;console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+': '+e.message);}}
test('one canonical full-suite entry point',()=>assert.equal(pkg.scripts.test,'node scripts/testing/run-all.cjs'));
test('compatibility entry uses the same runner',()=>assert.equal(JSON.parse(read('tests/package.json')).scripts.test,'node ../scripts/testing/run-all.cjs'));
test('lockfile identity matches the project',()=>{assert.equal(lock.lockfileVersion,3);assert.equal(lock.name,pkg.name);assert.equal(lock.version,pkg.version);assert.equal(lock.packages[''].version,pkg.version);});
test('direct production and development dependencies match lock',()=>{assert.deepEqual(lock.packages[''].dependencies,pkg.dependencies);assert.deepEqual(lock.packages[''].devDependencies,pkg.devDependencies);});
test('all locked third-party packages have version, registry origin and integrity',()=>{const rows=Object.entries(lock.packages).filter(([p])=>p);assert(rows.length>0);for(const [p,v] of rows){assert(/^node_modules\//.test(p));assert.equal(typeof v.version,'string');assert(v.version.length);const u=new URL(v.resolved);assert.equal(u.protocol,'https:');assert.equal(u.hostname,'registry.npmjs.org');assert(!u.username&&!u.password&&!u.search);assert(/^sha512-[A-Za-z0-9+/]+=*$/.test(v.integrity));assert(!v.link);}});
test('triggers use main pushes, normal PRs and manual runs',()=>{assert.deepEqual(Object.keys(workflow.on).sort(),['pull_request','push','workflow_dispatch']);assert.deepEqual(workflow.on.push.branches,['main']);assert.deepEqual(workflow.on.pull_request.branches,['main']);});
test('workflow token is read-only',()=>assert.deepEqual(workflow.permissions,{contents:'read'}));
const jobs=Object.values(workflow.jobs), steps=jobs.flatMap(j=>j.steps);
test('one bounded job without elevated job permissions',()=>{assert.equal(jobs.length,1);assert.equal(jobs[0]['runs-on'],'ubuntu-24.04');assert(jobs[0]['timeout-minutes']>0&&jobs[0]['timeout-minutes']<=15);assert(!jobs[0].permissions);});
test('official actions are pinned to full commit hashes',()=>{const actions=steps.filter(s=>s.uses);assert.equal(actions.length,3);for(const s of actions)assert(/^actions\/(checkout|setup-node|setup-python)@[0-9a-f]{40}$/.test(s.uses));});
test('checkout does not retain credentials or opt into unsafe PR checkout',()=>{const s=steps.find(s=>s.uses&&s.uses.startsWith('actions/checkout@'));assert.equal(s.with['persist-credentials'],false);assert(!s.with['allow-unsafe-pr-checkout']);});
test('CI installs locked dependencies before the canonical test command',()=>{const i=steps.findIndex(s=>s.run==='npm ci --include=dev --ignore-scripts --no-audit --no-fund');const t=steps.findIndex(s=>s.run==='npm test');assert(i>=0&&t>i);assert.equal(steps.filter(s=>s.run==='npm test').length,1);});
test('CI checks tracked files after testing',()=>{assert.equal(steps.at(-1).run,'git diff --exit-code');});
console.log(JSON.stringify({suite:'locked-ci-contracts',passed,failed,scope:'Static lockfile/workflow contracts, not a hosted GitHub Actions run or security audit.'}));
process.exitCode=failed?1:0;
