#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const MAX_BYTES = 2 * 1024 * 1024;
const MAX_DEPTH = 64;
function problem(code) { const e = new Error(code); e.code = code; return e; }
function preflight(text) {
  const stack = [];
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      const start = i; let closed = false;
      for (i++; i < text.length; i++) {
        if (text[i] === '\\') { i++; continue; }
        if (text[i] === '"') { closed = true; break; }
      }
      if (!closed) throw problem('JSON_PARSE');
      const parent = stack[stack.length - 1];
      if (parent && parent.object && parent.expectKey) {
        let name;
        try { name = JSON.parse(text.slice(start, i + 1)); } catch (_) { throw problem('JSON_PARSE'); }
        if (parent.keys.has(name)) throw problem('DUPLICATE_JSON_KEY');
        parent.keys.add(name); parent.expectKey = false;
      }
    } else if (c === '{' || c === '[') {
      stack.push({object: c === '{', expectKey: c === '{', keys: new Set()});
      if (stack.length > MAX_DEPTH) throw problem('JSON_DEPTH_LIMIT');
    } else if (c === '}' || c === ']') stack.pop();
    else if (c === ',' && stack.length && stack[stack.length - 1].object) stack[stack.length - 1].expectKey = true;
  }
}
async function readBounded(stream) {
  let size = 0; const chunks = [];
  for await (const chunk of stream) {
    const b = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    size += b.length;
    if (size > MAX_BYTES) { stream.destroy(); throw problem('INPUT_SIZE_LIMIT'); }
    chunks.push(b);
  }
  // Reject invalid UTF-8 rather than replacing source bytes silently.
  try { return new TextDecoder('utf-8', {fatal: true}).decode(Buffer.concat(chunks)); }
  catch (_) { throw problem('INVALID_UTF8'); }
}
function help() {
  return 'Usage: node scripts/validation/validate-records.cjs (--input FILE | --stdin) [--allow-external-refs]\n' +
    'Accepts one JSON record or a nonempty array. Reads only the explicit local input and bundled schemas.\n' +
    'No URLs are opened; no input is modified. Limits: 2 MiB, depth 64, 1000 records, 100 reported issues.\n' +
    'Exit 0: structurally valid (possibly with warnings); 1: invalid records; 2: input/setup error.\n' +
    'Validity is NOT factual verification, privacy clearance or publication authority.\n';
}
async function main(args) {
  if (args.length === 1 && args[0] === '--help') { process.stdout.write(help()); return; }
  let file = null, stdin = false, allowExternalRefs = false;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--input' && file === null && i + 1 < args.length && !args[i + 1].startsWith('--')) file = args[++i];
    else if (arg === '--stdin' && !stdin) stdin = true;
    else if (arg === '--allow-external-refs' && !allowExternalRefs) allowExternalRefs = true;
    else throw problem('USAGE');
  }
  if ((file !== null) === stdin) throw problem('USAGE');
  let stream;
  if (stdin) stream = process.stdin;
  else {
    if (/^[a-z][a-z0-9+.-]*:/i.test(file) && !path.isAbsolute(file)) throw problem('LOCAL_INPUT_ONLY');
    let stat;
    try { stat = fs.statSync(file); } catch (_) { throw problem('INPUT_READ'); }
    if (!stat.isFile()) throw problem('REGULAR_FILE_REQUIRED');
    if (stat.size > MAX_BYTES) throw problem('INPUT_SIZE_LIMIT');
    stream = fs.createReadStream(file);
  }
  const text = await readBounded(stream);
  preflight(text);
  let input;
  try { input = JSON.parse(text); } catch (_) { throw problem('JSON_PARSE'); }
  let report;
  try { report = require('./records.cjs').validateRecords(input, {allowExternalRefs}); }
  catch (_) { throw problem('VALIDATOR_SETUP'); }
  process.stdout.write(JSON.stringify(report, null, 2) + '\n');
  process.exitCode = report.valid ? 0 : 1;
}
if (require.main === module) main(process.argv.slice(2)).catch(e => {
  const safeCodes = new Set(['USAGE','LOCAL_INPUT_ONLY','INPUT_READ','REGULAR_FILE_REQUIRED','INPUT_SIZE_LIMIT','INVALID_UTF8','JSON_PARSE','DUPLICATE_JSON_KEY','JSON_DEPTH_LIMIT','VALIDATOR_SETUP']);
  const code = safeCodes.has(e.code) ? e.code : 'INPUT_READ';
  process.stdout.write(JSON.stringify({valid:false,status:'input_error',code,scope:'input_or_setup',not_verified:['factual_accuracy','publication_authority','privacy_safety']})+'\n');
  process.exitCode = 2;
});
module.exports = {preflight, MAX_BYTES, MAX_DEPTH};
