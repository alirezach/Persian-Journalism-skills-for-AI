'use strict';
const fs = require('fs');
const path = require('path');
const Ajv = require('ajv');
const VERSION = '0.1.0';
const MAX_RECORDS = 1000;
const MAX_ISSUES = 100;
const schemaDir = path.resolve(__dirname, '../../schemas');
const schemaFiles = {
  common: 'common.schema.json', source: 'source-record.schema.json',
  claim: 'claim-record.schema.json', dataset: 'dataset-record.schema.json',
  finding: 'finding-record.schema.json', handoff: 'handoff.schema.json'
};
let validators;
function getValidators() {
  if (validators) return validators;
  const ajv = new Ajv({allErrors: false, format: 'full', validateSchema: true, strictNumbers: true,
    coerceTypes: false, useDefaults: false, removeAdditional: false, ownProperties: true});
  for (const [kind, file] of Object.entries(schemaFiles)) {
    const schema = JSON.parse(fs.readFileSync(path.join(schemaDir, file), 'utf8'));
    if (schema.$id !== `urn:pjai:schemas:${kind}:${VERSION}`) throw new Error('Local schema identity mismatch');
    ajv.addSchema(schema);
  }
  validators = new Map(Object.keys(schemaFiles).filter(k => k !== 'common')
    .map(k => [k, ajv.getSchema(`urn:pjai:schemas:${k}:${VERSION}`)]));
  return validators;
}
function refs(record) {
  switch (record.record_type) {
    case 'source': return record.lineage;
    case 'dataset': return record.sources;
    case 'finding': return [...record.sources, ...record.datasets];
    case 'claim': return [...record.evidence.map(e => e.source), ...record.finding_refs];
    case 'handoff': return [...record.inputs, ...record.outputs];
    default: return [];
  }
}
const key = r => `${r.id}@${r.record_version}`;
const refKey = r => `${r.record_id}@${r.record_version}`;
function validateRecords(input, options = {}) {
  const errors = [], warnings = [], checksRun = ['input'];
  let issueCount = 0, relationshipsComplete = true, recordsChecked = 0;
  const issue = (list, code, index, detail = {}) => {
    issueCount++;
    // Keep errors visible even if warnings reached the display limit first.
    if (list === errors && errors.length + warnings.length >= MAX_ISSUES && warnings.length) warnings.pop();
    if (errors.length + warnings.length < MAX_ISSUES) list.push({code, record_index: index, ...detail});
  };
  let errorCount = 0, warningCount = 0;
  const fail = (c, i = null, d = {}) => { errorCount++; issue(errors, c, i, d); };
  const warn = (c, i = null) => { warningCount++; issue(warnings, c, i); };
  const records = Array.isArray(input) ? input : [input];
  function finish() {
    return {validator_version: '0.3.0-tooling', schema_version: VERSION,
      scope: 'structure_and_declared_relationships', valid: errorCount === 0,
      status: errorCount ? 'invalid' : warningCount ? 'valid_with_warnings' : 'valid',
      records_received: records.length, records_checked: recordsChecked, checks_run: checksRun,
      relationships_complete: relationshipsComplete, error_count: errorCount, warning_count: warningCount,
      issues_truncated: issueCount > MAX_ISSUES, errors, warnings,
      not_verified: ['factual_accuracy', 'analysis_method', 'publication_authority', 'privacy_safety', 'real_inspection', 'model_behavior']};
  }
  if (records.length === 0 || records.length > MAX_RECORDS) {
    fail('RECORD_COUNT_LIMIT'); relationshipsComplete = false; return finish();
  }
  const byType = getValidators();
  checksRun.push('schema');
  records.forEach((r, i) => {
    recordsChecked++;
    if (!r || typeof r !== 'object' || Array.isArray(r)) { fail('RECORD_OBJECT_REQUIRED', i); return; }
    const validator = byType.get(r.record_type);
    if (!validator) { fail('UNKNOWN_RECORD_TYPE', i); return; }
    if (!validator(r)) {
      const e = validator.errors[0];
      // Only trusted schema metadata is reported. Never echo user values or arbitrary field names.
      fail('SCHEMA', i, {keyword: e.keyword, schema_path: e.schemaPath});
      return;
    }
    if (!Number.isSafeInteger(r.record_version) || refs(r).some(p => !Number.isSafeInteger(p.record_version)))
      fail('UNSAFE_RECORD_VERSION', i);
  });
  if (errorCount) { relationshipsComplete = false; return finish(); }
  checksRun.push('versioned_references', 'chronology', 'dataset_metadata', 'evidence_inspection', 'finding_checks', 'handoff_checks', 'lineage');
  const map = new Map(), index = new Map();
  records.forEach((r, i) => {
    if (map.has(key(r))) { fail('DUPLICATE_RECORD_VERSION', i); relationshipsComplete = false; }
    map.set(key(r), r); index.set(key(r), i);
    const created = Date.parse(r.created_at), updated = Date.parse(r.updated_at);
    if (!Number.isFinite(created) || !Number.isFinite(updated)) fail('UNCOMPARABLE_AUDIT_TIME', i);
    else if (updated < created) fail('REVERSED_AUDIT_TIME', i);
    if (r.privacy.release_status === 'approved') warn('DECLARED_REVIEW_NOT_INDEPENDENTLY_VERIFIED', i);
  });
  records.forEach((r, i) => {
    for (const p of refs(r)) {
      if (!map.has(refKey(p))) {
        relationshipsComplete = false;
        if (options.allowExternalRefs === true) warn('EXTERNAL_REFERENCE_UNRESOLVED', i);
        else fail('MISSING_REFERENCE', i);
      }
    }
    if (r.record_type === 'dataset') {
      const names = r.variables.map(v => v.name);
      if (new Set(names).size !== names.length) fail('DUPLICATE_VARIABLE', i);
      if (r.weights.status === 'provided') {
        const variable = r.variables.find(v => v.name === r.weights.variable);
        if (!variable || !['number', 'integer'].includes(variable.data_type)) fail('INVALID_WEIGHT_VARIABLE', i);
      }
      if (r.period.start && r.period.end && r.period.start > r.period.end) fail('REVERSED_PERIOD', i);
      if (r.variables.some(v => v.unit.kind === 'unknown')) warn('DATASET_UNIT_UNKNOWN', i);
    }
    if (r.record_type === 'claim') {
      if (r.as_of && r.as_of.start && r.as_of.end && r.as_of.start > r.as_of.end) fail('REVERSED_PERIOD', i);
      if (['verified', 'supported_with_limits', 'misleading', 'contradicted'].includes(r.status)) {
        const decisive = r.evidence.filter(e => e.relation !== 'context');
        if (decisive.length === 0) fail('NO_DECISIVE_EVIDENCE', i);
        for (const e of decisive) {
          const s = map.get(refKey(e.source));
          if (s && !['full', 'partial'].includes(s.inspection.level)) fail('UNINSPECTED_DECISIVE_SOURCE', i);
        }
        if (decisive.length > 1) {
          const sources = decisive.map(e => map.get(refKey(e.source))).filter(Boolean);
          const groups = sources.map(s => s.independence_group).filter(Boolean);
          if (new Set(groups).size < groups.length || new Set(decisive.map(e => refKey(e.source))).size < decisive.length)
            warn('SHARED_EVIDENCE_CHAIN', i);
          if (groups.length < decisive.length) warn('EVIDENCE_INDEPENDENCE_UNRESOLVED', i);
        }
        for (const p of r.finding_refs) {
          const f = map.get(refKey(p));
          if (f && f.status !== 'checked') fail('UNCHECKED_FINDING_FOR_DECIDED_CLAIM', i);
        }
      }
    }
    if (r.record_type === 'handoff' && r.status === 'ready' && r.checks.some(c => ['failed', 'blocked'].includes(c.status)))
      fail('UNRESOLVED_HANDOFF_CHECK', i);
    if (r.record_type === 'finding' && r.status === 'checked') {
      if (r.verification.checks.some(c => ['failed', 'blocked'].includes(c.status))) fail('UNRESOLVED_FINDING_CHECK', i);
      for (const p of r.datasets) {
        const d = map.get(refKey(p));
        if (!d) continue;
        if (d.quality_checks.some(c => ['failed', 'blocked'].includes(c.status))) fail('UNRESOLVED_DATA_CHECK', i);
        if (r.population_inference && d.sampling === 'probability' && d.weights.status !== 'provided') fail('MISSING_SURVEY_WEIGHTS', i);
        if (r.population_inference && ['unknown', 'non_probability', 'administrative'].includes(d.sampling)) warn('POPULATION_GENERALIZATION_NEEDS_REVIEW', i);
      }
    }
  });
  // Iterative traversal avoids recursion over arbitrary lineage depth.
  const color = new Map();
  for (const start of records.filter(r => r.record_type === 'source')) {
    if (color.get(key(start)) === 2) continue;
    const stack = [{k: key(start), leave: false}];
    while (stack.length) {
      const item = stack.pop(), r = map.get(item.k);
      if (!r || r.record_type !== 'source') continue;
      if (item.leave) { color.set(item.k, 2); continue; }
      if (color.get(item.k) === 1) { fail('SOURCE_LINEAGE_CYCLE', index.get(item.k)); continue; }
      if (color.get(item.k) === 2) continue;
      color.set(item.k, 1); stack.push({k: item.k, leave: true});
      for (const p of [...r.lineage].reverse()) stack.push({k: refKey(p), leave: false});
    }
  }
  return finish();
}
module.exports = {validateRecords, MAX_RECORDS, MAX_ISSUES};
