'use strict';
// Configuration and template invariants, not model or typography-rendering tests.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const root = path.resolve(__dirname, '..');
const load = p => yaml.load(fs.readFileSync(path.join(root,p),'utf8'));
let passed=0, failed=0;
function test(name,fn){try{fn();passed++;console.log('PASS '+name);}catch(e){failed++;console.error('FAIL '+name+': '+e.message);}}
const locale=load('profiles/locales/fa-IR.yaml'),house=load('profiles/house-style/default-fa.yaml');
test('locale identity and version are explicit',()=>{assert.strictEqual(locale.id,'fa-IR');assert.strictEqual(locale.kind,'locale');assert.strictEqual(locale.profile_version,'0.1.0');});
test('house style is replaceable, not a universal correctness claim',()=>{assert.strictEqual(house.scope,'replaceable-editorial-preferences');assert.strictEqual(house.orthography.alternatives_are_errors,false);assert.strictEqual(house.locale_profile,locale.id);assert.strictEqual(house.profile_version,'0.1.0');});
test('Persian language does not activate Iran context',()=>{assert.strictEqual(locale.language,'fa');assert.strictEqual(locale.scope,'presentation-only');assert.strictEqual(locale.automatic_iran_context,false);});
test('display and machine digits are separate',()=>{assert.strictEqual(locale.numbers.display_digits,'persian');assert.strictEqual(locale.numbers.machine_digits,'ascii');assert.strictEqual(locale.numbers.scientific_precision,'preserve');});
test('Persian punctuation uses the intended Unicode characters',()=>{assert.strictEqual(locale.punctuation.comma,'\u060c');assert.strictEqual(locale.numbers.decimal_separator,'\u066b');assert.strictEqual(locale.numbers.grouping_separator,'\u066c');});
test('contextual spelling preserves hamza and paragraphs',()=>{assert.strictEqual(locale.text.character_normalization,'persian-prose-only');assert.strictEqual(locale.text.zwnj,'contextual');assert(locale.text.preserve_hamza);assert(locale.text.preserve_paragraphs_and_indentation);assert.strictEqual(locale.text.persian_yeh,'\u06cc');assert.strictEqual(locale.text.persian_kaf,'\u06a9');});
test('exact text, code and source strings are protected',()=>{const p=locale.text.preserve_exact;assert.strictEqual(new Set(p).size,p.length);for(const k of ['direct-quotations','non-persian-passages','urls-and-emails','identifiers-and-codes','formulas-and-statistical-notation','software-versions','bibliographic-source-strings'])assert(p.includes(k));});
test('bidi settings do not authorize changes to identifiers',()=>{assert.strictEqual(locale.text.direction,'rtl');assert.strictEqual(locale.bidi.latin_spans,'isolate-ltr-where-supported');assert.strictEqual(locale.bidi.hidden_marks,'only-for-demonstrated-display-defect-never-inside-identifiers');});
test('no automatic calendar or currency conversions',()=>{assert(locale.calendar.preserve_source_calendar);assert.strictEqual(locale.calendar.automatic_conversion,false);assert(locale.money.preserve_source_unit);assert.strictEqual(locale.money.automatic_rial_toman_conversion,false);assert.strictEqual(locale.money.automatic_fx_conversion,false);});
test('deliverable register outranks chat tone',()=>{assert.strictEqual(house.register.infer_from_chat_tone,false);assert.deepStrictEqual(house.register.selection_order,['explicit-deliverable-instruction','deliverable-type','audience-and-destination','house-style']);});
test('conservative editing is not automatic summarization',()=>{assert(house.intervention.proofread_preserves_structure);assert(house.intervention.summarize_only_when_requested);assert(house.intervention.keep_good_text_unchanged);});
test('ezafe form is explicit and replaceable',()=>assert.strictEqual(house.orthography.ezafe_after_silent_heh,'خانهٔ'));
test('no forbidden-word list or forced colloquial voice',()=>{assert.deepStrictEqual(house.voice.forbidden_word_list,[]);assert.strictEqual(house.voice.forced_colloquial_social_posts,false);assert(house.voice.preserve_authorial_position);});
test('preferences cannot override fidelity, privacy or evidence',()=>{for(const v of Object.values(house.precedence))assert.strictEqual(v,true);assert.strictEqual(Object.keys(house.precedence).length,3);});
test('bibliography script and evidence locators are preserved',()=>{assert(house.citations.preserve_source_locator);assert(house.citations.preserve_bibliography_script);assert(house.citations.reformat_only_if_requested);});
const headers={
  'translation-decisions.csv':['segment_id','source_version','source_term','sense_and_context','chosen_equivalent','alternatives','reason','reference','status','reviewer','reviewed_at'],
  'claim-ledger.csv':['claim_id','record_version','statement','attributed_to','context','as_of_original','as_of_calendar','as_of_start','as_of_end','priority','status','evidence_json','finding_refs_json','reasoning','reviewer','reviewed_at','limitations','outstanding_checks','privacy_classification'],
  'data-dictionary.csv':['dataset_id','dataset_version','variable','description','data_type','observation_unit','population','unit_kind','unit_label','scale','currency','currency_namespace','calendar','missing_tokens_json','weight_role','source_refs_json','notes'],
  'correction-log.csv':['correction_id','change_type','discovered_at','affected_record_id','affected_version','original_text_or_value','corrected_text_or_value','reason','evidence_refs_json','review_status','publication_status','authorized_by','published_at']
};
for(const [name,expected] of Object.entries(headers))test('empty CSV contract '+name,()=>{
  const text=fs.readFileSync(path.join(root,'templates',name),'utf8');const lines=text.trimEnd().split(/\r?\n/);assert.strictEqual(lines.length,1);const cols=lines[0].split(',');assert.deepStrictEqual(cols,expected);assert.strictEqual(new Set(cols).size,cols.length);cols.forEach(c=>assert(/^[a-z][a-z0-9_]*$/.test(c)));
});
test('exactly eight human working templates are supplied',()=>{
  const expected=['README.md','project-brief.md','translation-decisions.csv','claim-ledger.csv','data-dictionary.csv','methodology.md','publication-checklist.md','correction-log.csv','handoff.md'];assert.deepStrictEqual(fs.readdirSync(path.join(root,'templates')).sort(),expected.sort());
});
test('publication checklist starts unreviewed',()=>{const text=fs.readFileSync(path.join(root,'templates/publication-checklist.md'),'utf8');assert(text.includes('- [ ]'));assert(!/- \[[xX]\]/.test(text));assert(text.includes('بررسی‌نشده'));});
test('handoff form does not grant external authority',()=>{const text=fs.readFileSync(path.join(root,'templates/handoff.md'),'utf8');assert(text.includes('not_authorized_by_this_record'));assert(text.includes('مجوز انتشار نیست'));});
test('package version matches the catalog release',()=>{const pkg=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8'));assert.strictEqual(pkg.version,load('catalog.yaml').project.release);assert(pkg.private);assert.strictEqual(pkg.dependencies.ajv,'6.15.0');assert.strictEqual(pkg.devDependencies['js-yaml'],'4.3.2');});
console.log(JSON.stringify({suite:'profiles-and-templates',passed,failed,node:process.version,yaml:require('js-yaml/package.json').version,scope:'Declarative configuration and blank-template checks only; no model behavior or rendering evaluation.'}));
process.exitCode=failed?1:0;
