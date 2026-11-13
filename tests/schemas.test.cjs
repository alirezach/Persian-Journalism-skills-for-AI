'use strict';
// All fixtures are synthetic. This runner reads local schemas only and never fetches URLs.
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const Ajv = require('ajv');
const root = path.resolve(__dirname, '..');
const ajv = new Ajv({allErrors: true, validateSchema: true, coerceTypes: false, useDefaults: false, removeAdditional: false});
const files = fs.readdirSync(path.join(root, 'schemas')).filter(n => n.endsWith('.schema.json')).sort();
let passed = 0, failed = 0;
function test(name, fn) { try { fn(); passed++; console.log('PASS ' + name); } catch (e) { failed++; console.error('FAIL ' + name + ': ' + e.message); } }
for (const name of files) {
  const s = JSON.parse(fs.readFileSync(path.join(root, 'schemas', name), 'utf8'));
  test('metaschema ' + name, () => assert(ajv.validateSchema(s), JSON.stringify(ajv.errors)));
  ajv.addSchema(s);
}
const validate = r => { const v = ajv.getSchema('urn:pjai:schemas:' + r.record_type + ':0.1.0'); return Boolean(v && v(r)); };
const clone = v => JSON.parse(JSON.stringify(v));
const time = '2026-11-13T13:32:00Z';
const ref = (id, version=1) => ({record_id:id, record_version:version});
const privacy = () => ({classification:'internal',contains_personal_data:'no',release_status:'not_reviewed',review_ref:null});
const base = (type,id) => ({schema_version:'0.1.0',record_type:type,id,record_version:1,created_at:time,updated_at:time,privacy:privacy()});
const unit = () => ({kind:'count',label:'items',scale:1,currency:null,currency_namespace:'not_applicable'});
const check = () => ({name:'synthetic check',status:'passed',performed_at:time,actor:'fixture-runner',detail:'Synthetic test fixture only; not evidence of a real-world review.'});
function records() {
  const source = {...base('source','src-example'),title:'Synthetic source; not a real citation',source_type:'document',publisher:'Fixture publisher',location:{url:'https://example.org/synthetic-source',local_ref:null},publication_date:{original:'2026',calendar:'gregorian'},access_status:'available',accessed_at:time,inspection:{level:'full',notes:'Synthetic inspected-source state for tests only.'},version:{publisher_version:null,sha256:null},lineage:[],independence_group:'synthetic-chain-a',quality:{methodology:null,coverage:'Synthetic two-item population',currency:null,conflicts_of_interest:null},reuse:{license:null,redistribution:'unknown'},limitations:['Entire record is synthetic.']};
  const dataset = {...base('dataset','dset-example'),title:'Synthetic dataset',sources:[ref(source.id)],observation_unit:'item',population:{target:'Two synthetic items',covered:'Two synthetic items',exclusions:[]},sampling:'census',period:{original:'Synthetic year 2026',calendar:'gregorian',start:'2026-01-01',end:'2026-12-31'},geography:[{name:'Synthetic location',level:'fixture',code:null,boundary_version:null}],raw:{mode:'retrieval_manifest',location:'Synthetic input values: 10 and 20',sha256:null},variables:[{name:'amount',description:'Synthetic item count',data_type:'integer',unit:unit(),missing_tokens:['','NA']}],weights:{status:'not_applicable',variable:null},quality_checks:[check()],transformations:[],limitations:['No real-world data.'],open_questions:[]};
  const finding = {...base('finding','fnd-example'),question:'What is the synthetic mean?',result_statement:'The mean of the synthetic values is 15 items.',sources:[ref(source.id)],datasets:[ref(dataset.id)],population_inference:false,method:'Arithmetic mean: (10 + 20) / 2.',calculation_ref:'Synthetic fixture formula in tests/schemas.test.cjs',assumptions:['Two equally weighted synthetic items.'],measures:[{name:'mean',value:15,original_value:'15',missing_reason:'not_missing',unit:unit(),denominator:'2 synthetic items'}],status:'checked',verification:{state:'reproduced',checks:[check()]},uncertainty:'Exact arithmetic for two synthetic values, no population inference.',limitations:['Test fixture, not a real finding.']};
  const claim = {...base('claim','clm-example'),statement:'The synthetic mean is 15 items.',attributed_to:'fixture-author',context:'Synthetic assertion only.',as_of:null,priority:'high',status:'verified',evidence:[{source:ref(source.id),locator:'Synthetic fixture values 10 and 20',relation:'supports',excerpt:null,note:'Test-only evidence pointer.'}],finding_refs:[ref(finding.id)],decision:{reasoning:'Synthetic arithmetic: (10 + 20) / 2 = 15.',reviewer:'fixture-runner',reviewed_at:time},limitations:['Not a real-world verification.'],outstanding_checks:[]};
  const handoff = {...base('handoff','hnd-example'),from_role:'data-analysis',to_role:'data-journalism',scope:'Synthetic fixture handoff, not publication approval.',inputs:[ref(dataset.id)],outputs:[ref(finding.id),ref(claim.id)],work_done:['Synthetic calculation represented.'],not_checked:['Real sources, publication rights and field reporting.'],checks:[check()],status:'ready',blockers:[],next_actions:['Evaluate independently for a real project.'],external_actions:'not_authorized_by_this_record'};
  return [source,dataset,finding,claim,handoff];
}
function links(r) {
  if(r.record_type==='source') return r.lineage;
  if(r.record_type==='dataset') return r.sources;
  if(r.record_type==='finding') return [...r.sources,...r.datasets];
  if(r.record_type==='claim') return [...r.evidence.map(e=>e.source),...r.finding_refs];
  if(r.record_type==='handoff') return [...r.inputs,...r.outputs];
  return [];
}
// Limited deterministic semantic checks. Not a fact checker, permissions engine or anonymizer.
function bundleErrors(rs) {
  const errors=[], map=new Map(), key=r=>r.id+'@'+r.record_version, refkey=r=>r.record_id+'@'+r.record_version;
  for(const r of rs) {
    if(!validate(r)) errors.push('invalid record: '+r.id);
    if(map.has(key(r))) errors.push('duplicate version: '+key(r));
    map.set(key(r),r);
    if(Date.parse(r.updated_at)<Date.parse(r.created_at)) errors.push('reversed audit time: '+r.id);
  }
  if(errors.some(e=>e.startsWith('invalid record:'))) return errors;
  for(const r of rs) {
    for(const p of links(r)) if(!map.has(refkey(p))) errors.push('missing reference: '+refkey(p));
    if(r.record_type==='dataset') {
      const names=r.variables.map(v=>v.name);
      if(new Set(names).size!==names.length) errors.push('duplicate variable: '+r.id);
      if(r.weights.status==='provided') {
        const v=r.variables.find(v=>v.name===r.weights.variable);
        if(!v || !['number','integer'].includes(v.data_type)) errors.push('invalid weight variable: '+r.id);
      }
      if(r.period.start && r.period.end && r.period.start>r.period.end) errors.push('reversed period: '+r.id);
    }
    if(r.record_type==='claim' && ['verified','supported_with_limits','misleading','contradicted'].includes(r.status)) {
      for(const e of r.evidence.filter(e=>e.relation!=='context')) {
        const s=map.get(refkey(e.source));
        if(s && !['full','partial'].includes(s.inspection.level)) errors.push('uninspected decisive source: '+r.id);
      }
    }
    if(r.record_type==='finding' && r.status==='checked') {
      for(const p of r.datasets) {
        const d=map.get(refkey(p));
        if(!d) continue;
        if(d.quality_checks.some(c=>['failed','blocked'].includes(c.status))) errors.push('unresolved data check: '+r.id);
        if(r.population_inference && d.sampling==='probability' && d.weights.status!=='provided') errors.push('missing survey weights: '+r.id);
      }
    }
  }
  const done=new Set(), visiting=new Set();
  function visit(k) {
    if(visiting.has(k)) {errors.push('source lineage cycle: '+k);return;}
    if(done.has(k)) return;
    const r=map.get(k); if(!r || r.record_type!=='source') return;
    visiting.add(k); for(const p of r.lineage) visit(refkey(p)); visiting.delete(k); done.add(k);
  }
  for(const r of rs.filter(r=>r.record_type==='source')) visit(key(r));
  return errors;
}
for(const r of records()) test('valid '+r.record_type,()=>assert(validate(r)));
function schemaCase(name,index,mutate,expected) {test(name,()=>{const r=records()[index];mutate(r);assert.strictEqual(validate(r),expected);});}
schemaCase('reject unknown root field',0,r=>r.mystery=1,false);
schemaCase('reject wrong schema version',0,r=>r.schema_version='9.0.0',false);
schemaCase('reject wrong identifier prefix',0,r=>r.id='clm-bad',false);
schemaCase('reject revision zero',0,r=>r.record_version=0,false);
schemaCase('reject timestamp without timezone',0,r=>r.created_at='2026-11-13T13:32:00',false);
schemaCase('reject missing location',0,r=>{r.location.url=null;r.location.local_ref=null;},false);
schemaCase('reject inspected source without access time',0,r=>r.accessed_at=null,false);
schemaCase('accept uninspected unavailable source',0,r=>{r.inspection.level='none';r.accessed_at=null;r.access_status='unavailable';},true);
schemaCase('reject public release without review reference',0,r=>{r.privacy.classification='public';r.privacy.release_status='approved';},false);
schemaCase('reject confidential record direct release',0,r=>{r.privacy.classification='confidential';r.privacy.release_status='approved';r.privacy.review_ref='review-fixture';},false);
schemaCase('accept public review metadata with reference',0,r=>{r.privacy.classification='public';r.privacy.release_status='approved';r.privacy.review_ref='synthetic-review-reference';},true);
schemaCase('reject stored copy without checksum',1,r=>r.raw.mode='stored_copy',false);
schemaCase('reject provided weights without variable',1,r=>r.weights.status='provided',false);
schemaCase('reject zero unit scale',1,r=>r.variables[0].unit.scale=0,false);
schemaCase('allow explicit unknown dataset unit',1,r=>{r.variables[0].unit.kind='unknown';r.variables[0].unit.label=null;r.variables[0].unit.scale=null;},true);
schemaCase('reject zero marked missing',2,r=>{r.measures[0].value=0;r.measures[0].missing_reason='unavailable';},false);
schemaCase('accept genuine zero',2,r=>r.measures[0].value=0,true);
schemaCase('reject null marked present',2,r=>r.measures[0].value=null,false);
schemaCase('accept explicit missing result',2,r=>{r.status='draft';r.measures[0].value=null;r.measures[0].missing_reason='unavailable';},true);
schemaCase('reject checked result with unknown unit',2,r=>r.measures[0].unit.kind='unknown',false);
schemaCase('reject checked money without currency',2,r=>r.measures[0].unit.kind='money',false);
schemaCase('accept explicit project toman unit',2,r=>{r.measures[0].unit={kind:'money',label:'toman',scale:1,currency:'IRT',currency_namespace:'project'};},true);
schemaCase('reject checked result without calculation reference',2,r=>r.calculation_ref=null,false);
schemaCase('reject local toman code labeled ISO',2,r=>{r.measures[0].unit={kind:'money',label:'toman',scale:1,currency:'IRT',currency_namespace:'ISO4217'};},false);
schemaCase('accept explicit rial currency metadata',2,r=>{r.measures[0].unit={kind:'money',label:'rial',scale:1,currency:'IRR',currency_namespace:'ISO4217'};},true);
schemaCase('reject checked rate without denominator',2,r=>{r.measures[0].unit.kind='rate';r.measures[0].denominator=null;},false);
schemaCase('reject checked result without passed check',2,r=>r.verification.checks=[],false);
schemaCase('reject check claimed unrun but timestamped',2,r=>r.verification.checks[0].status='not_run',false);
schemaCase('reject verified claim without evidence',3,r=>r.evidence=[],false);
schemaCase('reject decisive evidence without locator',3,r=>r.evidence[0].locator=' ',false);
schemaCase('reject verdict without reasoning',3,r=>r.decision.reasoning=null,false);
schemaCase('reject contradicted claim without counterevidence',3,r=>r.status='contradicted',false);
schemaCase('accept unresolved claim without evidence',3,r=>{r.status='unresolved';r.evidence=[];r.outstanding_checks=['Need primary material.'];},true);
schemaCase('reject unresolved claim with no open check',3,r=>r.status='unresolved',false);
schemaCase('reject limited support without limitation',3,r=>{r.status='supported_with_limits';r.limitations=[];},false);
schemaCase('reject ready handoff with blocker',4,r=>r.blockers=['Unresolved unit.'],false);
schemaCase('reject blocked handoff without blocker',4,r=>r.status='blocked',false);
schemaCase('reject forged publication authority in handoff',4,r=>r.external_actions='publish_now',false);
function bundleCase(name,mutate,expectError) {test(name,()=>{const rs=records();mutate(rs);const errors=bundleErrors(rs);assert.strictEqual(errors.length>0,expectError,JSON.stringify(errors));});}
bundleCase('accept linked baseline',()=>{},false);
bundleCase('reject missing source record',rs=>rs.splice(0,1),true);
bundleCase('reject missing referenced version',rs=>rs[1].sources[0].record_version=2,true);
bundleCase('reject duplicate id and version',rs=>rs.push(clone(rs[0])),true);
bundleCase('allow two explicit versions',rs=>{const s=clone(rs[0]);s.record_version=2;rs.push(s);},false);
bundleCase('reject reversed audit time',rs=>rs[0].updated_at='2025-01-01T00:00:00Z',true);
bundleCase('reject unknown weight column',rs=>rs[1].weights={status:'provided',variable:'missing_weight'},true);
bundleCase('reject nonnumeric weight column',rs=>{rs[1].weights={status:'provided',variable:'amount'};rs[1].variables[0].data_type='string';},true);
bundleCase('reject duplicate variable names',rs=>rs[1].variables.push(clone(rs[1].variables[0])),true);
bundleCase('reject reversed statistical period',rs=>rs[1].period.start='2027-01-01',true);
bundleCase('reject snippet-only decisive evidence',rs=>rs[0].inspection.level='snippet',true);
bundleCase('accept inspected relevant source portion',rs=>rs[0].inspection.level='partial',false);
bundleCase('reject circular source lineage',rs=>rs[0].lineage=[ref(rs[0].id)],true);
bundleCase('reject checked finding on failed data check',rs=>rs[1].quality_checks[0].status='failed',true);
bundleCase('reject population inference without required weights',rs=>{rs[2].population_inference=true;rs[1].sampling='probability';rs[1].weights={status:'required_missing',variable:null};},true);
bundleCase('retain descriptive draft with missing weights',rs=>{rs[2].status='draft';rs[2].population_inference=false;rs[1].sampling='probability';rs[1].weights={status:'required_missing',variable:null};},false);
test('validation does not mutate input',()=>{const rs=records();const before=JSON.stringify(rs);bundleErrors(rs);assert.strictEqual(JSON.stringify(rs),before);});
test('synthetic arithmetic is reproducible',()=>assert.strictEqual((10+20)/2,records()[2].measures[0].value));
console.log(JSON.stringify({passed,failed,node:process.version,ajv:require('ajv/package.json').version,dialect:'Draft-07',scope:'Synthetic structural and limited relational tests; no editorial or real-world verification.'}));
process.exitCode=failed?1:0;
