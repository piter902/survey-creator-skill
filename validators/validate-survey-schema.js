#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ALLOWED_MEDIA_TYPES = new Set(['image', 'audio', 'video']);
const ALLOWED_QUESTION_TYPES = new Set(['radio', 'checkbox', 'input']);
const ALLOWED_DATA_TYPES = new Set([
  'email', 'tel', 'number', 'text', 'date', 'time', 'dateTime', 'dateRange', 'timeRange', 'dateTimeRange'
]);
const ID_PATTERN = /^[A-Za-z][A-Za-z0-9_-]*$/;
const MEDIA_URL_PATTERN = /^(https?:\/\/|data:(image|audio|video)\/)/i;

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function isBoolean(value) {
  return typeof value === 'boolean';
}

function isIntegerLike(value) {
  return Number.isInteger(value) || (typeof value === 'string' && /^\d+$/.test(value));
}

function makeReporter() {
  const errors = [];
  const warnings = [];
  return {
    error(path, message) { errors.push({ path, message }); },
    warn(path, message) { warnings.push({ path, message }); },
    result(normalized = null) {
      return {
        valid: errors.length === 0,
        errors,
        warnings,
        normalized,
      };
    }
  };
}

function assertAllowedKeys(node, allowedKeys, nodePath, reporter) {
  if (!isPlainObject(node)) return;
  for (const key of Object.keys(node)) {
    if (!allowedKeys.includes(key)) reporter.error(`${nodePath}.${key}`, `Unsupported field "${key}".`);
  }
}

function validateMediaList(media, nodePath, reporter, required = false) {
  if (media == null) {
    if (required) reporter.error(nodePath, 'Media must be an array.');
    return;
  }
  if (!Array.isArray(media)) {
    reporter.error(nodePath, 'Media must be an array.');
    return;
  }
  media.forEach((item, index) => {
    const itemPath = `${nodePath}[${index}]`;
    if (!isPlainObject(item)) {
      reporter.error(itemPath, 'Media item must be an object.');
      return;
    }
    assertAllowedKeys(item, ['type', 'url'], itemPath, reporter);
    if (!ALLOWED_MEDIA_TYPES.has(item.type)) reporter.error(`${itemPath}.type`, 'Media type must be image, audio, or video.');
    if (!isNonEmptyString(item.url)) reporter.error(`${itemPath}.url`, 'Media url must be a non-empty string.');
    else if (!MEDIA_URL_PATTERN.test(item.url)) reporter.error(`${itemPath}.url`, 'Media url must start with http://, https://, or a data:image/audio/video URL.');
  });
}

function validateRichTextString(value, nodePath, reporter, required = true) {
  if (value == null) {
    if (required) reporter.error(nodePath, 'Field is required and must be a string.');
    return;
  }
  if (typeof value !== 'string') reporter.error(nodePath, 'Field must be a string.');
}

function registerId(id, pathName, reporter, idMap) {
  if (!isNonEmptyString(id)) {
    reporter.error(pathName, 'id must be a non-empty string.');
    return;
  }
  if (!ID_PATTERN.test(id)) {
    reporter.error(pathName, 'id must start with a letter and contain only letters, numbers, underscores, or hyphens.');
    return;
  }
  const existing = idMap.get(id);
  if (existing) reporter.error(pathName, `Duplicate id "${id}" already used at ${existing}.`);
  else idMap.set(id, pathName);
}

function validateInputLikeAttribute(attr, nodePath, reporter) {
  if (!isPlainObject(attr)) {
    reporter.error(nodePath, 'attribute must be an object.');
    return;
  }
  assertAllowedKeys(attr, ['required', 'placeholder', 'maxLength', 'minLength', 'dataType', 'media'], nodePath, reporter);
  if (attr.required != null && !isBoolean(attr.required)) reporter.error(`${nodePath}.required`, 'required must be boolean.');
  if (attr.placeholder != null && typeof attr.placeholder !== 'string') reporter.error(`${nodePath}.placeholder`, 'placeholder must be a string.');
  if (attr.maxLength != null && !isIntegerLike(attr.maxLength)) reporter.error(`${nodePath}.maxLength`, 'maxLength must be an integer or numeric string.');
  if (attr.minLength != null && !isIntegerLike(attr.minLength)) reporter.error(`${nodePath}.minLength`, 'minLength must be an integer or numeric string.');
  if (attr.dataType != null && !ALLOWED_DATA_TYPES.has(attr.dataType)) reporter.error(`${nodePath}.dataType`, `Unsupported dataType "${attr.dataType}".`);
  if (attr.media != null) validateMediaList(attr.media, `${nodePath}.media`, reporter);
  if (isIntegerLike(attr.maxLength) && isIntegerLike(attr.minLength) && Number(attr.maxLength) < Number(attr.minLength)) {
    reporter.error(nodePath, 'maxLength cannot be smaller than minLength.');
  }
}

function validateChild(child, childPath, reporter, idMap) {
  if (!isPlainObject(child)) {
    reporter.error(childPath, 'Child must be an object.');
    return;
  }
  assertAllowedKeys(child, ['type', 'id', 'title', 'attribute'], childPath, reporter);
  if (child.type !== 'input') reporter.error(`${childPath}.type`, 'Child type must be input.');
  registerId(child.id, `${childPath}.id`, reporter, idMap);
  validateRichTextString(child.title, `${childPath}.title`, reporter, true);
  if (child.attribute != null) validateInputLikeAttribute(child.attribute, `${childPath}.attribute`, reporter);
}

function validateOptionAttribute(questionType, attr, pathName, reporter) {
  if (!isPlainObject(attr)) {
    reporter.error(pathName, 'attribute must be an object.');
    return;
  }
  const baseKeys = ['random', 'media'];
  const checkboxKeys = ['exclusive', 'mutual-exclusion'];
  assertAllowedKeys(attr, questionType === 'checkbox' ? [...baseKeys, ...checkboxKeys] : baseKeys, pathName, reporter);
  if (attr.random != null && !isBoolean(attr.random)) reporter.error(`${pathName}.random`, 'random must be boolean.');
  if (attr.media != null) validateMediaList(attr.media, `${pathName}.media`, reporter);
  if (questionType === 'checkbox') {
    if (attr.exclusive != null && !isBoolean(attr.exclusive)) reporter.error(`${pathName}.exclusive`, 'exclusive must be boolean.');
    if (attr['mutual-exclusion'] != null && !isBoolean(attr['mutual-exclusion'])) reporter.error(`${pathName}.mutual-exclusion`, 'mutual-exclusion must be boolean.');
    if (attr.exclusive === true && attr['mutual-exclusion'] === true) reporter.error(pathName, 'exclusive and mutual-exclusion cannot both be true on the same option.');
  }
}

function validateQuestionBase(question, questionPath, reporter, idMap) {
  if (!isPlainObject(question)) {
    reporter.error(questionPath, 'Question must be an object.');
    return false;
  }
  registerId(question.id, `${questionPath}.id`, reporter, idMap);
  validateRichTextString(question.title, `${questionPath}.title`, reporter, true);
  validateRichTextString(question.description, `${questionPath}.description`, reporter, false);
  return true;
}

function validateSelectionQuestion(question, questionPath, reporter, idMap) {
  const type = question.type;
  assertAllowedKeys(question, ['type', 'id', 'title', 'description', 'attribute', 'option'], questionPath, reporter);
  if (!validateQuestionBase(question, questionPath, reporter, idMap)) return;
  if (!isPlainObject(question.attribute)) reporter.error(`${questionPath}.attribute`, 'attribute must be an object.');
  else {
    assertAllowedKeys(question.attribute, ['required', 'random', 'media'], `${questionPath}.attribute`, reporter);
    if (question.attribute.required != null && !isBoolean(question.attribute.required)) reporter.error(`${questionPath}.attribute.required`, 'required must be boolean.');
    if (question.attribute.random != null && !isBoolean(question.attribute.random)) reporter.error(`${questionPath}.attribute.random`, 'random must be boolean.');
    if (question.attribute.media != null) validateMediaList(question.attribute.media, `${questionPath}.attribute.media`, reporter);
  }
  if (!Array.isArray(question.option) || question.option.length === 0) {
    reporter.error(`${questionPath}.option`, 'option must be a non-empty array.');
    return;
  }
  question.option.forEach((option, index) => {
    const optionPath = `${questionPath}.option[${index}]`;
    if (!isPlainObject(option)) {
      reporter.error(optionPath, 'Option must be an object.');
      return;
    }
    assertAllowedKeys(option, ['title', 'id', 'child', 'attribute'], optionPath, reporter);
    registerId(option.id, `${optionPath}.id`, reporter, idMap);
    validateRichTextString(option.title, `${optionPath}.title`, reporter, true);
    if (option.attribute != null) validateOptionAttribute(type, option.attribute, `${optionPath}.attribute`, reporter);
    if (option.child != null) {
      if (!Array.isArray(option.child) || option.child.length === 0) reporter.error(`${optionPath}.child`, 'child must be a non-empty array when present.');
      else option.child.forEach((child, childIndex) => validateChild(child, `${optionPath}.child[${childIndex}]`, reporter, idMap));
    }
  });
}

function validateInputQuestion(question, questionPath, reporter, idMap) {
  assertAllowedKeys(question, ['type', 'id', 'title', 'description', 'attribute', 'option'], questionPath, reporter);
  if (!validateQuestionBase(question, questionPath, reporter, idMap)) return;
  if (!isPlainObject(question.attribute)) reporter.error(`${questionPath}.attribute`, 'attribute must be an object.');
  else {
    assertAllowedKeys(question.attribute, ['required', 'media'], `${questionPath}.attribute`, reporter);
    if (question.attribute.required != null && !isBoolean(question.attribute.required)) reporter.error(`${questionPath}.attribute.required`, 'required must be boolean.');
    if (question.attribute.media != null) validateMediaList(question.attribute.media, `${questionPath}.attribute.media`, reporter);
  }
  if (!Array.isArray(question.option) || question.option.length === 0) {
    reporter.error(`${questionPath}.option`, 'option must be a non-empty array.');
    return;
  }
  question.option.forEach((option, index) => {
    const optionPath = `${questionPath}.option[${index}]`;
    if (!isPlainObject(option)) {
      reporter.error(optionPath, 'Option must be an object.');
      return;
    }
    assertAllowedKeys(option, ['title', 'id', 'attribute'], optionPath, reporter);
    registerId(option.id, `${optionPath}.id`, reporter, idMap);
    validateRichTextString(option.title, `${optionPath}.title`, reporter, true);
    validateInputLikeAttribute(option.attribute, `${optionPath}.attribute`, reporter);
  });
}

function validateSurveyNode(survey, reporter, idMap) {
  const nodePath = 'survey';
  if (!isPlainObject(survey)) {
    reporter.error(nodePath, 'survey must be an object.');
    return;
  }
  assertAllowedKeys(survey, ['type', 'id', 'title', 'description', 'attribute'], nodePath, reporter);
  if (survey.type !== 'survey') reporter.error(`${nodePath}.type`, 'survey.type must equal "survey".');
  registerId(survey.id, `${nodePath}.id`, reporter, idMap);
  validateRichTextString(survey.title, `${nodePath}.title`, reporter, true);
  validateRichTextString(survey.description, `${nodePath}.description`, reporter, false);
  if (!isPlainObject(survey.attribute)) {
    reporter.error(`${nodePath}.attribute`, 'survey.attribute must be an object.');
    return;
  }
  assertAllowedKeys(survey.attribute, ['onePageOneQuestion', 'allowBack', 'media'], `${nodePath}.attribute`, reporter);
  if (!isBoolean(survey.attribute.onePageOneQuestion)) reporter.error(`${nodePath}.attribute.onePageOneQuestion`, 'onePageOneQuestion must be boolean.');
  if (!isBoolean(survey.attribute.allowBack)) reporter.error(`${nodePath}.attribute.allowBack`, 'allowBack must be boolean.');
  if (survey.attribute.media != null) validateMediaList(survey.attribute.media, `${nodePath}.attribute.media`, reporter);
}

function normalizeFinishNodes(finish, reporter) {
  if (isPlainObject(finish)) {
    if (reporter) reporter.warn('finish', 'finish object has been normalized to a one-item array; prefer finish: [{...}] as the canonical shape.');
    return [finish];
  }
  if (Array.isArray(finish)) {
    if (!finish.length) {
      if (reporter) reporter.error('finish', 'finish must contain at least one finish object.');
      return [];
    }
    return finish;
  }
  if (reporter) reporter.error('finish', 'finish must be an array of finish objects.');
  return [];
}

function validateFinishNodes(finishRaw, reporter, idMap) {
  const finishNodes = normalizeFinishNodes(finishRaw, reporter);
  const normalized = [];
  finishNodes.forEach((finish, index) => {
    const nodePath = `finish[${index}]`;
    if (!isPlainObject(finish)) {
      reporter.error(nodePath, 'finish item must be an object.');
      return;
    }
    assertAllowedKeys(finish, ['type', 'id', 'title', 'description', 'media'], nodePath, reporter);
    if (finish.type !== 'finish') reporter.error(`${nodePath}.type`, 'finish.type must equal "finish".');
    if (finish.id != null) registerId(finish.id, `${nodePath}.id`, reporter, idMap);
    validateRichTextString(finish.title, `${nodePath}.title`, reporter, true);
    validateRichTextString(finish.description, `${nodePath}.description`, reporter, false);
    if (finish.media != null) validateMediaList(finish.media, `${nodePath}.media`, reporter);
    normalized.push(finish);
  });
  return normalized;
}

function validateSurveySchema(schema) {
  const reporter = makeReporter();
  const idMap = new Map();

  if (!isPlainObject(schema)) {
    reporter.error('schema', 'Top-level schema must be an object with survey/questions/finish.');
    return reporter.result(null);
  }

  assertAllowedKeys(schema, ['survey', 'questions', 'finish'], 'schema', reporter);
  validateSurveyNode(schema.survey, reporter, idMap);

  if (!Array.isArray(schema.questions)) {
    reporter.error('questions', 'questions must be an array.');
  } else {
    schema.questions.forEach((question, index) => {
      const questionPath = `questions[${index}]`;
      if (!isPlainObject(question)) {
        reporter.error(questionPath, 'Question must be an object.');
        return;
      }
      if (!ALLOWED_QUESTION_TYPES.has(question.type)) {
        reporter.error(`${questionPath}.type`, `Unsupported question type "${question.type}".`);
        return;
      }
      if (question.type === 'radio' || question.type === 'checkbox') validateSelectionQuestion(question, questionPath, reporter, idMap);
      if (question.type === 'input') validateInputQuestion(question, questionPath, reporter, idMap);
    });
  }

  const normalizedFinish = validateFinishNodes(schema.finish, reporter, idMap);

  return reporter.result({
    survey: schema.survey,
    questions: Array.isArray(schema.questions) ? schema.questions : [],
    finish: normalizedFinish,
  });
}

function readInputArg(fileArg) {
  if (fileArg) {
    const target = path.resolve(process.cwd(), fileArg);
    return fs.readFileSync(target, 'utf8');
  }
  return fs.readFileSync(0, 'utf8');
}

function printHumanReport(report) {
  if (report.valid) {
    console.log('✅ Survey schema is valid.');
  } else {
    console.log('❌ Survey schema is invalid.');
  }
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

  let raw = '';
  try {
    raw = readInputArg(fileArg);
  } catch (error) {
    console.error(`Failed to read schema input: ${error.message}`);
    process.exit(1);
  }

  let schema;
  try {
    schema = JSON.parse(raw);
  } catch (error) {
    console.error(`Invalid JSON: ${error.message}`);
    process.exit(1);
  }

  const report = validateSurveySchema(schema);
  if (jsonOutput) console.log(JSON.stringify(report, null, 2));
  else printHumanReport(report);
  process.exit(report.valid ? 0 : 1);
}

if (require.main === module) main();

module.exports = {
  validateSurveySchema,
  ALLOWED_DATA_TYPES,
  ALLOWED_QUESTION_TYPES,
};
