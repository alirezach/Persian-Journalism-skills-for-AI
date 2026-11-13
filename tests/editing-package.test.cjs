'use strict';
// Static source/fixture contracts. These never grade model outputs.
const assert=require('assert');const fs=require('fs');const path=require('path');const yaml=require('js-yaml');
const root=path.resolve(__dirname,'..');const read=p=>fs.readFileSync(path.join(root,p),'utf8');
let passed=0,failed=0;function test(n,f){try{f();passed++;console.log('PASS '+n);}catch(e){failed++;console.error('FAIL '+n+': '+e.message);}}
const text=read('skills/persian-editing/SKILL.md');const match=text.match(/^---\n([\s\S]*?)\n---\n/);assert(match);const meta=yaml.load(match[1]);
const manifest=JSON.parse(read('skills/persian-editing/build-manifest.json'));const fixtures=JSON.parse(read('tests/fixtures/editing-cases.json'));
test('frontmatter name matches directory and convention',()=>{assert.strictEqual(meta.name,'persian-editing');assert(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(meta.name));assert(meta.name.length<=64);});
test('description is bounded and meaningful',()=>{assert(typeof meta.description==='string');assert(meta.description.length>0&&meta.description.length<=1024);assert(meta.description.includes('ویرایش'));});
test('optional metadata is string-to-string',()=>{for(const [k,v] of Object.entries(meta.metadata)){assert.strictEqual(typeof k,'string');assert.strictEqual(typeof v,'string');}assert.strictEqual(meta.metadata.version,'0.1.0');assert.strictEqual(meta.metadata.status,'experimental');});
test('no unneeded vendor permissions',()=>{assert(!('allowed-tools'in meta));assert(!('compatibility'in meta));assert.strictEqual(meta.license,'MIT');});
test('entry stays under 500 lines',()=>assert(text.split('\n').length<500));
test('three intervention levels are present',()=>{for(const x of ['نمونه‌خوانی','ویرایش زبانی','بازنویسی'])assert(text.includes(x));});
test('source links resolve relative to skill root',()=>{for(const m of text.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)){assert(fs.statSync(path.resolve(root,'skills/persian-editing',m[1])).isFile());}});
test('package maps versions and every rewrite to a real resource',()=>{assert.strictEqual(manifest.version,meta.metadata.version);assert.strictEqual(manifest.files.length,12);for(const [old,target] of Object.entries(manifest.entry_rewrites)){assert(text.includes(']('+old+')'));assert(manifest.files.some(r=>r.source===old.slice(6)&&r.target===target));}});
test('all package sources are UTF-8 text without NUL',()=>{for(const row of manifest.files){const s=read(row.source);assert(!s.includes(String.fromCharCode(0)));}});
test('fixtures explicitly have no evaluation results',()=>{assert.strictEqual(fixtures.evaluation_status,'not_run');assert.strictEqual(fixtures.skill_version,meta.metadata.version);for(const c of fixtures.cases){assert(c.synthetic);assert.strictEqual(c.status,'not_run');assert(!('output'in c));}});
test('twelve unique acceptance scenarios are supplied',()=>{assert.strictEqual(fixtures.cases.length,12);assert.strictEqual(new Set(fixtures.cases.map(c=>c.id)).size,12);});
test('every scenario has criteria and forbidden outcomes',()=>{for(const c of fixtures.cases){assert(c.acceptance.length>0);assert(c.critical_failures.length>0);assert(c.prompt.includes('متن:'));}});
test('protected spans exist verbatim in test input',()=>{for(const c of fixtures.cases)for(const s of c.protected_spans)assert(c.prompt.includes(s));});
test('scenarios cover all three levels',()=>assert.deepStrictEqual([...new Set(fixtures.cases.map(c=>c.mode))].sort(),['language-edit','proofread','rewrite']));
test('runtime instructions contain no internal skill references',()=>{for(const r of manifest.files.filter(r=>r.source.startsWith('skills/'))){assert(!/https:\/\/skill-|load_skill|functions\.|bk-button/.test(read(r.source)));}});
test('catalog editing lifecycle differs from the seven planned skills',()=>{const c=yaml.load(read('catalog.yaml'));const e=c.skills.find(s=>s.name==='persian-editing');assert.strictEqual(e.status,'experimental');assert.strictEqual(e.version,meta.metadata.version);assert.strictEqual(c.skills.filter(s=>s.status==='planned').length,7);});
console.log(JSON.stringify({suite:'editing-static-contracts',passed,failed,scope:'Metadata, source links and synthetic fixture contracts; not behavioral evaluation.'}));process.exitCode=failed?1:0;
