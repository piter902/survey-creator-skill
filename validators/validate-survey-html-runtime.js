#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function makeReporter() {
  const errors = [];
  const warnings = [];
  return {
    error(path, message) { errors.push({ path, message }); },
    warn(path, message) { warnings.push({ path, message }); },
    result(extra = {}) { return { valid: errors.length === 0, errors, warnings, ...extra }; },
  };
}

function has(text, pattern) {
  return typeof pattern === 'string' ? text.includes(pattern) : pattern.test(text);
}

function checkPattern(text, reporter, key, message, pattern, level = 'error') {
  if (!has(text, pattern)) reporter[level](key, message);
}

function extractSurveySchemaLiteral(html) {
  const marker = 'const surveySchema =';
  const start = html.indexOf(marker);
  if (start === -1) return null;
  const from = html.indexOf('{', start);
  if (from === -1) return null;
  let depth = 0;
  let inSingle = false;
  let inDouble = false;
  let inTemplate = false;
  let escaped = false;
  for (let i = from; i < html.length; i++) {
    const ch = html[i];
    if (escaped) { escaped = false; continue; }
    if (ch === '\\') { escaped = true; continue; }
    if (!inDouble && !inTemplate && ch === '\'') { inSingle = !inSingle; continue; }
    if (!inSingle && !inTemplate && ch === '"') { inDouble = !inDouble; continue; }
    if (!inSingle && !inDouble && ch === '`') { inTemplate = !inTemplate; continue; }
    if (inSingle || inDouble || inTemplate) continue;
    if (ch === '{') depth++;
    if (ch === '}') {
      depth--;
      if (depth === 0) return html.slice(from, i + 1);
    }
  }
  return null;
}

function validateHtmlRuntime(html) {
  const reporter = makeReporter();

  checkPattern(html, reporter, 'html.doctype', 'HTML must include <!DOCTYPE html>.', /<!DOCTYPE html>/i);
  checkPattern(html, reporter, 'html.form', 'HTML must include a real <form> element.', /<form\b/i);
  checkPattern(html, reporter, 'html.schema', 'HTML should contain a surveySchema object.', 'const surveySchema =');
  checkPattern(html, reporter, 'runtime.render', 'HTML should render screens from schema.', 'render()');
  checkPattern(html, reporter, 'runtime.assemblePayload', 'HTML should define assemblePayload().', 'function assemblePayload()');
  checkPattern(html, reporter, 'runtime.validateQuestion', 'HTML should define validateQuestion().', 'function validateQuestion(');
  checkPattern(html, reporter, 'runtime.bindEvents', 'HTML should define bindEvents().', 'function bindEvents()');
  checkPattern(html, reporter, 'runtime.childVisibility', 'HTML should manage child visibility.', 'function updateChildVisibility()');
  checkPattern(html, reporter, 'runtime.localStorageSet', 'HTML should persist step cache with localStorage.setItem.', 'localStorage.setItem(');
  checkPattern(html, reporter, 'runtime.localStorageRemove', 'HTML should clear cache with localStorage.removeItem after submit.', 'localStorage.removeItem(');
  checkPattern(html, reporter, 'runtime.resumePrompt', 'HTML should support checkpoint resume prompt from localStorage cache.', 'function openResumePrompt(');
  checkPattern(html, reporter, 'runtime.consoleLog', 'HTML should output payload with console.log.', /console\.log\((payload|assemblePayload\(\))\)/);
  checkPattern(html, reporter, 'runtime.optionId', 'HTML should preserve option ids in DOM using data-option-id.', 'data-option-id');
  checkPattern(html, reporter, 'runtime.childId', 'HTML should preserve child ids in DOM using data-child-id.', 'data-child-id');
  checkPattern(html, reporter, 'runtime.exclusive', 'HTML should implement checkbox exclusive logic.', 'dataset.exclusive');
  checkPattern(html, reporter, 'runtime.mutual', 'HTML should implement checkbox mutual-exclusion logic.', 'dataset.mutualExclusion');
  checkPattern(html, reporter, 'runtime.submitIntercept', 'HTML should intercept form submit.', "form.addEventListener('submit'");
  checkPattern(html, reporter, 'runtime.changeIntercept', 'HTML should react to checkbox/input changes.', "form.addEventListener('change'");
  checkPattern(html, reporter, 'runtime.inputIntercept', 'HTML should react to input changes for cache persistence.', "form.addEventListener('input'");
  if (has(html, 'postSubmit')) {
    checkPattern(html, reporter, 'runtime.postSubmit', 'HTML with finish postSubmit should normalize and execute post-submit actions.', 'function runPostSubmitAction(');
    checkPattern(html, reporter, 'runtime.postSubmit.redirect', 'HTML with finish postSubmit should support redirect execution.', 'function navigateAfterSubmit(');
  }

  if (has(html, 'onePageOneQuestion')) {
    checkPattern(html, reporter, 'runtime.screens', 'Step mode should define screens().', 'function screens()');
    checkPattern(html, reporter, 'runtime.show', 'Step mode should define show().', 'function show(');
    checkPattern(html, reporter, 'runtime.currentQuestion', 'Step mode should define currentQuestion().', 'function currentQuestion()');
  }

  if (has(html, 'exclusive') && !has(html, '!== e.target')) {
    reporter.warn('runtime.exclusive.detail', 'Exclusive logic exists but could not find explicit exclusion of the current checkbox from clearing.');
  }

  if (has(html, 'mutual-exclusion') && !has(html, 'otherMutual')) {
    reporter.warn('runtime.mutual.detail', 'mutual-exclusion appears in schema/text but grouped clearing logic was not clearly detected.');
  }

  if (has(html, 'renderRich(') && !has(html, 'function sanitizeRichText(')) {
    reporter.warn('runtime.richtext', 'Rich-text rendering detected without explicit sanitizeRichText() hook.');
  }
  if (has(html, 'renderRich(') && !has(html, 'sanitizeRichText(')) {
    reporter.warn('runtime.richtext.sanitizer', 'Rich-text rendering detected without sanitizer hook; production use should add a whitelist sanitizer.');
  }

  const schemaLiteral = extractSurveySchemaLiteral(html);
  if (!schemaLiteral) reporter.warn('runtime.schema.extract', 'Could not extract surveySchema literal from HTML.');
  if (schemaLiteral && /randomId\(\)/.test(schemaLiteral)) {
    reporter.warn('runtime.dynamicIds', 'surveySchema contains runtime-generated ids. Production surveys should pre-freeze ids before delivery to users.');
  }
  if (schemaLiteral && !/randomId\(\)/.test(schemaLiteral)) {
    reporter.warn('runtime.staticSchemaOnly', 'Schema literal was extracted. For stronger safety, validate it separately with validate-survey-schema.js.');
  }

  const supportsRange = has(html, 'dateRange') && has(html, 'timeRange') && has(html, 'dateTimeRange');
  if (supportsRange) checkPattern(html, reporter, 'runtime.rangeObject', 'Range values should serialize to { start, end }.', /start[\s\S]*end/);

  const summary = {
    checks: {
      doctype: has(html, /<!DOCTYPE html>/i),
      form: has(html, /<form\b/i),
      schema: has(html, 'const surveySchema ='),
      assemblePayload: has(html, 'function assemblePayload()'),
      localStorage: has(html, 'localStorage.setItem(') && has(html, 'localStorage.removeItem('),
      resumePrompt: has(html, 'function openResumePrompt('),
      exclusive: has(html, 'dataset.exclusive'),
      mutualExclusion: has(html, 'dataset.mutualExclusion'),
      childVisibility: has(html, 'function updateChildVisibility()'),
      postSubmit: has(html, 'function runPostSubmitAction('),
    }
  };

  return reporter.result(summary);
}

function main() {
  const args = process.argv.slice(2);
  const json = args.includes('--json');
  const fileArg = args.find(arg => !arg.startsWith('--'));
  if (!fileArg) {
    console.error('Usage: validate-survey-html-runtime.js /absolute/path/to/file.html [--json]');
    process.exit(1);
  }
  const filePath = path.resolve(process.cwd(), fileArg);
  let html = '';
  try {
    html = fs.readFileSync(filePath, 'utf8');
  } catch (error) {
    console.error(`Failed to read HTML file: ${error.message}`);
    process.exit(1);
  }
  const report = validateHtmlRuntime(html);
  if (json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log(report.valid ? '✅ HTML runtime contract check passed.' : '❌ HTML runtime contract check failed.');
    if (report.errors.length) {
      console.log('\nErrors:');
      report.errors.forEach((item, idx) => console.log(`${idx + 1}. [${item.path}] ${item.message}`));
    }
    if (report.warnings.length) {
      console.log('\nWarnings:');
      report.warnings.forEach((item, idx) => console.log(`${idx + 1}. [${item.path}] ${item.message}`));
    }
  }
  process.exit(report.valid ? 0 : 1);
}

if (require.main === module) main();

module.exports = { validateHtmlRuntime, extractSurveySchemaLiteral };
