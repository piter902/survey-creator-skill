#!/usr/bin/env node
'use strict';

const fs = require('fs');

const ALLOWED_QUESTION_TYPES = new Set(['radio', 'checkbox', 'input']);
const ALLOWED_DATA_TYPES = new Set([
  'email', 'tel', 'number', 'text', 'date', 'time', 'dateTime', 'dateRange', 'timeRange', 'dateTimeRange'
]);
const RANGE_DATA_TYPES = new Set(['dateRange', 'timeRange', 'dateTimeRange']);
const SCALAR_DATA_TYPES = new Set(['email', 'tel', 'number', 'text', 'date', 'time', 'dateTime']);

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function isIsoDateString(value) {
  return isNonEmptyString(value) && !Number.isNaN(Date.parse(value));
}

function makeReporter() {
  const errors = [];
  const warnings = [];
  return {
    error(path, message) { errors.push({ path, message }); },
    warn(path, message) { warnings.push({ path, message }); },
    result() { return { valid: errors.length === 0, errors, warnings }; }
  };
}

function assertAllowedKeys(node, allowedKeys, nodePath, reporter) {
  if (!isPlainObject(node)) return;
  for (const key of Object.keys(node)) {
    if (!allowedKeys.includes(key)) reporter.error(`${nodePath}.${key}`, `Unsupported field "${key}".`);
  }
}

function validateRangeObject(value, nodePath, reporter) {
  if (!isPlainObject(value)) {
    reporter.error(nodePath, 'Range value must be an object with start/end.');
    return;
  }
  assertAllowedKeys(value, ['start', 'end'], nodePath, reporter);
  if (!isNonEmptyString(value.start)) reporter.error(`${nodePath}.start`, 'start must be a non-empty string.');
  if (!isNonEmptyString(value.end)) reporter.error(`${nodePath}.end`, 'end must be a non-empty string.');
}

function validateChildAnswer(child, nodePath, reporter) {
  if (!isPlainObject(child)) {
    reporter.error(nodePath, 'Child answer must be an object.');
    return;
  }
  assertAllowedKeys(child, ['childId', 'dataType', 'value'], nodePath, reporter);
  if (!isNonEmptyString(child.childId)) reporter.error(`${nodePath}.childId`, 'childId must be a non-empty string.');
  if (!ALLOWED_DATA_TYPES.has(child.dataType)) reporter.error(`${nodePath}.dataType`, `Unsupported dataType "${child.dataType}".`);
  if (RANGE_DATA_TYPES.has(child.dataType)) validateRangeObject(child.value, `${nodePath}.value`, reporter);
  else if (SCALAR_DATA_TYPES.has(child.dataType)) {
    if (!isNonEmptyString(child.value)) reporter.error(`${nodePath}.value`, 'Scalar child value must be a non-empty string.');
  } else {
    reporter.error(`${nodePath}.dataType`, 'Unknown child dataType.');
  }
}

function validateRadioValue(value, nodePath, reporter) {
  if (!isPlainObject(value)) {
    reporter.error(nodePath, 'Radio value must be an object.');
    return;
  }
  assertAllowedKeys(value, ['optionId', 'child'], nodePath, reporter);
  if (!isNonEmptyString(value.optionId)) reporter.error(`${nodePath}.optionId`, 'optionId must be a non-empty string.');
  if (value.child != null) {
    if (!Array.isArray(value.child)) reporter.error(`${nodePath}.child`, 'child must be an array.');
    else value.child.forEach((item, index) => validateChildAnswer(item, `${nodePath}.child[${index}]`, reporter));
  }
}

function validateCheckboxValue(value, nodePath, reporter) {
  if (!Array.isArray(value) || value.length === 0) {
    reporter.error(nodePath, 'Checkbox value must be a non-empty array.');
    return;
  }
  value.forEach((item, index) => {
    const itemPath = `${nodePath}[${index}]`;
    if (!isPlainObject(item)) {
      reporter.error(itemPath, 'Checkbox item must be an object.');
      return;
    }
    assertAllowedKeys(item, ['optionId', 'child'], itemPath, reporter);
    if (!isNonEmptyString(item.optionId)) reporter.error(`${itemPath}.optionId`, 'optionId must be a non-empty string.');
    if (item.child != null) {
      if (!Array.isArray(item.child)) reporter.error(`${itemPath}.child`, 'child must be an array.');
      else item.child.forEach((child, childIndex) => validateChildAnswer(child, `${itemPath}.child[${childIndex}]`, reporter));
    }
  });
}

function validateInputValue(value, nodePath, reporter) {
  if (!Array.isArray(value) || value.length === 0) {
    reporter.error(nodePath, 'Input value must be a non-empty array.');
    return;
  }
  value.forEach((item, index) => {
    const itemPath = `${nodePath}[${index}]`;
    if (!isPlainObject(item)) {
      reporter.error(itemPath, 'Input item must be an object.');
      return;
    }
    assertAllowedKeys(item, ['optionId', 'dataType', 'value'], itemPath, reporter);
    if (!isNonEmptyString(item.optionId)) reporter.error(`${itemPath}.optionId`, 'optionId must be a non-empty string.');
    if (!ALLOWED_DATA_TYPES.has(item.dataType)) reporter.error(`${itemPath}.dataType`, `Unsupported dataType "${item.dataType}".`);
    if (RANGE_DATA_TYPES.has(item.dataType)) validateRangeObject(item.value, `${itemPath}.value`, reporter);
    else if (SCALAR_DATA_TYPES.has(item.dataType)) {
      if (!isNonEmptyString(item.value)) reporter.error(`${itemPath}.value`, 'Scalar input value must be a non-empty string.');
    } else {
      reporter.error(`${itemPath}.dataType`, 'Unknown input dataType.');
    }
  });
}

function validateAnswer(answer, nodePath, reporter) {
  if (!isPlainObject(answer)) {
    reporter.error(nodePath, 'Answer must be an object.');
    return;
  }
  assertAllowedKeys(answer, ['questionId', 'questionType', 'value'], nodePath, reporter);
  if (!isNonEmptyString(answer.questionId)) reporter.error(`${nodePath}.questionId`, 'questionId must be a non-empty string.');
  if (!ALLOWED_QUESTION_TYPES.has(answer.questionType)) {
    reporter.error(`${nodePath}.questionType`, `Unsupported questionType "${answer.questionType}".`);
    return;
  }
  if (answer.value == null) {
    reporter.error(`${nodePath}.value`, 'value is required for answered questions.');
    return;
  }
  if (answer.questionType === 'radio') validateRadioValue(answer.value, `${nodePath}.value`, reporter);
  if (answer.questionType === 'checkbox') validateCheckboxValue(answer.value, `${nodePath}.value`, reporter);
  if (answer.questionType === 'input') validateInputValue(answer.value, `${nodePath}.value`, reporter);
}

function validateSurveyPayload(payload) {
  const reporter = makeReporter();
  if (!isPlainObject(payload)) {
    reporter.error('payload', 'Payload must be an object.');
    return reporter.result();
  }
  assertAllowedKeys(payload, ['surveyId', 'submittedAt', 'answers'], 'payload', reporter);
  if (!isNonEmptyString(payload.surveyId)) reporter.error('payload.surveyId', 'surveyId must be a non-empty string.');
  if (!Number.isInteger(payload.submittedAt) || payload.submittedAt < 0) reporter.error('payload.submittedAt', 'submittedAt must be a non-negative integer timestamp.');
  if (!Array.isArray(payload.answers)) {
    reporter.error('payload.answers', 'answers must be an array.');
  } else {
    const questionIds = new Set();
    payload.answers.forEach((answer, index) => {
      validateAnswer(answer, `payload.answers[${index}]`, reporter);
      if (isPlainObject(answer) && isNonEmptyString(answer.questionId)) {
        if (questionIds.has(answer.questionId)) reporter.error(`payload.answers[${index}].questionId`, `Duplicate questionId "${answer.questionId}" in answers.`);
        questionIds.add(answer.questionId);
      }
    });
  }
  return reporter.result();
}

function readInputArg(fileArg) {
  if (fileArg) return fs.readFileSync(fileArg, 'utf8');
  return fs.readFileSync(0, 'utf8');
}

function printHumanReport(report) {
  if (report.valid) console.log('✅ Survey payload is valid.');
  else console.log('❌ Survey payload is invalid.');
  if (report.errors.length) {
    console.log('\nErrors:');
    report.errors.forEach((item, idx) => console.log(`${idx + 1}. [${item.path}] ${item.message}`));
  }
  if (report.warnings.length) {
    console.log('\nWarnings:');
    report.warnings.forEach((item, idx) => console.log(`${idx + 1}. [${item.path}] ${item.message}`));
  }
}

function main() {
  const args = process.argv.slice(2);
  const jsonOutput = args.includes('--json');
  const fileArg = args.find((arg) => !arg.startsWith('--'));
  let raw;
  try {
    raw = readInputArg(fileArg);
  } catch (error) {
    console.error(`Failed to read payload input: ${error.message}`);
    process.exit(1);
  }
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (error) {
    console.error(`Invalid JSON: ${error.message}`);
    process.exit(1);
  }
  const report = validateSurveyPayload(payload);
  if (jsonOutput) console.log(JSON.stringify(report, null, 2));
  else printHumanReport(report);
  process.exit(report.valid ? 0 : 1);
}

if (require.main === module) main();

module.exports = {
  validateSurveyPayload,
};
