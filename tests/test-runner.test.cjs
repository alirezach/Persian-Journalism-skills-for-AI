#!/usr/bin/env node
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {discover, findPython, run} = require('../scripts/testing/run-all.cjs');
let passed = 0, failed = 0;
function test(name, fn) {try {fn(); passed++; console.log('PASS '+name);} catch(e) {failed++; console.error('FAIL '+name+': '+e.message);}}
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pjai-runner-'));
const dir = path.join(root, 'tests');fs.mkdirSync(dir);
for (const name of ['z.test.cjs','a.test.cjs','test_two.py','test_one.py','README.md','not-a-test.py']) fs.writeFileSync(path.join(dir,name),'');
const ok = {status:0, signal:null};
try {
  test('discovers all JS suites in stable order',()=>assert.deepEqual(discover(root).javascript.map(x=>path.basename(x)),['a.test.cjs','z.test.cjs']));
  test('discovers the current Python filename convention',()=>assert.deepEqual(discover(root).python,['test_one.py','test_two.py']));
  test('new JS suite is included without editing a command',()=>{const p=path.join(dir,'new.test.cjs');fs.writeFileSync(p,'');assert.equal(discover(root).javascript.length,3);fs.unlinkSync(p);});
  test('empty suites fail closed',()=>{const empty=path.join(root,'empty');fs.mkdirSync(path.join(empty,'tests'),{recursive:true});assert.throws(()=>discover(empty),/empty/);});
  test('python3 is preferred',()=>assert.equal(findPython({},()=>ok),'python3'));
  test('python fallback is supported',()=>assert.equal(findPython({},exe=>exe==='python3'?{error:new Error('missing')}:ok),'python'));
  test('explicit executable path with spaces stays one executable',()=>{let actual;const exe='/temporary path/python';assert.equal(findPython({PYTHON:exe},x=>{actual=x;return ok;}),exe);assert.equal(actual,exe);});
  test('invalid explicit Python is not silently replaced',()=>{let n=0;assert.throws(()=>findPython({PYTHON:'missing'},()=>{n++;return {status:1};}),/Python/);assert.equal(n,1);});
  test('old or missing Python is rejected',()=>assert.throws(()=>findPython({},()=>({status:1})),/3.10/));
  function execute(failAt=-1, failure={status:1}) {
    const calls=[];
    const code=run({root,env:{PYTHON:'selected-python'},log:()=>{},spawn:(exe,args,options)=>{
      if(args[0]==='-c')return ok;
      calls.push({exe,args,options});return calls.length-1===failAt?failure:ok;
    }});return {code,calls};
  }
  test('success requires all suites',()=>assert.equal(execute().code,0));
  test('JS failure remains failure even if Python passes',()=>assert.equal(execute(0).code,1));
  test('Python discovery failure propagates',()=>assert.equal(execute(2).code,1));
  test('spawn errors fail closed',()=>assert.equal(execute(0,{error:new Error('spawn failed')}).code,1));
  test('terminated suites fail closed',()=>assert.equal(execute(0,{status:null,signal:'SIGTERM'}).code,1));
  test('later suites still run after failure',()=>assert.equal(execute(0).calls.length,3));
  test('Python discovery runs once, not normalization twice',()=>assert.deepEqual(execute().calls.filter(x=>x.exe==='selected-python').map(x=>x.args),[['-m','unittest','discover','-s','tests','-p','test_*.py','-v']]));
  test('commands use trusted root, inherited output and no shell',()=>{for(const x of execute().calls){assert.equal(x.options.cwd,root);assert.equal(x.options.stdio,'inherit');assert.equal(x.options.shell,false);assert.equal(x.options.env.PYTHONDONTWRITEBYTECODE,'1');}});
} finally {fs.rmSync(root,{recursive:true,force:true});}
console.log(JSON.stringify({suite:'unified-test-runner',passed,failed,scope:'Discovery and failure propagation with synthetic child-process results.'}));
process.exitCode=failed?1:0;
