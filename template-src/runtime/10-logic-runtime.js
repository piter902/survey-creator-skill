    function questionNumber(questionId) {
      return (questionOrder.get(questionId) ?? 0) + 1;
    }

    function questionById(questionId) {
      return answerableQuestions.find((question) => question.id === questionId) || null;
    }


    function flattenAnswerValue(value) {
      if (value == null) return [];
      if (typeof value === 'object') {
        const start = value.start != null ? String(value.start) : '';
        const end = value.end != null ? String(value.end) : '';
        return [start, end, `${start} ${end}`.trim()].filter(Boolean);
      }
      return [String(value)];
    }

    function selectedOptionIds(answer) {
      if (!answer) return [];
      if (answer.questionType === 'radio' && answer.value?.optionId) return [answer.value.optionId];
      if (answer.questionType === 'checkbox') return (answer.value || []).map((item) => item.optionId).filter(Boolean);
      return [];
    }

    function scalarAnswerValues(answer) {
      if (!answer) return [];
      const values = [];
      if (answer.questionType === 'radio') {
        values.push(...selectedOptionIds(answer));
        (answer.value?.child || []).forEach((item) => values.push(...flattenAnswerValue(item.value)));
      } else if (answer.questionType === 'checkbox') {
        (answer.value || []).forEach((item) => {
          if (item.optionId) values.push(String(item.optionId));
          (item.child || []).forEach((child) => values.push(...flattenAnswerValue(child.value)));
        });
      } else if (answer.questionType === 'input') {
        (answer.value || []).forEach((item) => values.push(...flattenAnswerValue(item.value)));
      } else if (answer.questionType === 'score') {
        (answer.value || []).forEach((item) => values.push(String(item.score)));
      } else if (answer.questionType === 'nps') {
        if (answer.value?.score != null) values.push(String(answer.value.score));
      }
      return values.filter(Boolean);
    }

    function compareLogicValue(actual, expected) {
      if (expected == null) return false;
      return String(actual) === String(expected);
    }

    function evaluateLogicCondition(condition) {
      const answer = cache.answers?.[condition.questionId];
      const operator = condition.operator;
      const optionIds = selectedOptionIds(answer);
      const scalarValues = scalarAnswerValues(answer);
      if (operator === 'answered') return !!answer;
      if (operator === 'not_answered') return !answer;
      if (operator === 'selected') return optionIds.includes(condition.optionId);
      if (operator === 'not_selected') return !optionIds.includes(condition.optionId);
      if (operator === 'exists') return optionIds.some((id) => (condition.optionIds || []).includes(id));
      if (operator === 'not_exists') return optionIds.every((id) => !(condition.optionIds || []).includes(id));
      if (operator === 'contains') {
        if (condition.optionId) return optionIds.includes(condition.optionId);
        return scalarValues.some((value) => String(value).includes(String(condition.value ?? '')));
      }
      if (operator === 'not_contains') {
        if (condition.optionId) return !optionIds.includes(condition.optionId);
        return scalarValues.every((value) => !String(value).includes(String(condition.value ?? '')));
      }
      if (operator === 'eq') return scalarValues.some((value) => compareLogicValue(value, condition.value));
      if (operator === 'neq') return !!answer && scalarValues.every((value) => !compareLogicValue(value, condition.value));
      if (operator === 'gt') return scalarValues.some((value) => Number(value) > Number(condition.value));
      if (operator === 'lt') return scalarValues.some((value) => Number(value) < Number(condition.value));
      return false;
    }

    function computeLogicState() {
      const hiddenQuestions = new Set(logicShowQuestionTargets);
      const hiddenOptions = new Set(logicShowOptionTargets);
      const jumpTargets = new Map();
      const autoSelects = [];
      let activeFinishId = defaultFinishScreen.id;
      logicRules.forEach((rule) => {
        if (!rule?.when || !rule?.action) return;
        if (!evaluateLogicCondition(rule.when)) return;
        const action = rule.action;
        const optionKey = action.targetQuestionId && action.targetOptionId ? `${action.targetQuestionId}::${action.targetOptionId}` : null;
        if (action.type === 'show_question' && action.targetQuestionId) hiddenQuestions.delete(action.targetQuestionId);
        if (action.type === 'hide_question' && action.targetQuestionId) hiddenQuestions.add(action.targetQuestionId);
        if (action.type === 'show_option' && optionKey) hiddenOptions.delete(optionKey);
        if (action.type === 'hide_option' && optionKey) hiddenOptions.add(optionKey);
        if ((action.type === 'jump_to_question' || action.type === 'jump_to_page') && action.targetQuestionId && rule.when.questionId) {
          jumpTargets.set(rule.when.questionId, action.targetQuestionId);
        }
        if (action.type === 'end_survey' && rule.when.questionId) {
          const targetFinishId = finishScreenIds.has(action.targetQuestionId) ? action.targetQuestionId : defaultFinishScreen.id;
          jumpTargets.set(rule.when.questionId, targetFinishId);
          activeFinishId = targetFinishId;
        }
        if (action.type === 'auto_select_option' && optionKey) autoSelects.push({ questionId: action.targetQuestionId, optionId: action.targetOptionId });
      });
      return { hiddenQuestions, hiddenOptions, jumpTargets, autoSelects, activeFinishId };
    }

    function isQuestionHidden(questionId) {
      return logicState.hiddenQuestions.has(questionId);
    }

    function isQuestionSkipped(questionId) {
      return logicState.skippedQuestions.has(questionId);
    }

    function isQuestionUnavailable(questionId) {
      return isQuestionHidden(questionId) || isQuestionSkipped(questionId);
    }

    function isOptionHidden(questionId, optionId) {
      return logicState.hiddenOptions.has(`${questionId}::${optionId}`);
    }

    function clearQuestionState(question) {
      const screen = document.querySelector(dataSelector('screen-id', question.id));
      if (!screen) return;
      screen.querySelectorAll('input, textarea').forEach((input) => {
        input.value = '';
        input.checked = false;
      });
      screen.querySelectorAll('.score-pill').forEach((pill) => {
        pill.classList.remove('is-active');
        pill.setAttribute('aria-pressed', 'false');
      });
      screen.querySelectorAll('.error').forEach((el) => el.classList.remove('is-visible'));
      screen.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));
    }

    function clearFieldValue(field) {
      if (!field) return;
      if (field.matches('[data-range-type]')) {
        field.querySelectorAll('input').forEach((input) => { input.value = ''; });
        return;
      }
      if (field.matches('input, textarea')) field.value = '';
      field.querySelectorAll('input, textarea').forEach((input) => { input.value = ''; input.checked = false; });
    }

    function clearUnavailableState() {
      answerableQuestions.forEach((question) => {
        if (isQuestionUnavailable(question.id)) {
          delete cache.answers[question.id];
          clearQuestionState(question);
        }
        (question.option || []).forEach((option) => {
          if (!isOptionHidden(question.id, option.id)) return;
          const selectors = [
            `.option${dataSelector('option-id', option.id)} input`,
            `${dataSelector('option-field', option.id)} ${dataSelector('option-id', option.id)}`,
            `${dataSelector('score-option', option.id)} .score-pill`,
            `${dataSelector('nps-option', option.id)} .score-pill`
          ];
          document.querySelectorAll(selectors.join(',')).forEach((node) => {
            if (node.matches('input')) node.checked = false;
            if (node.matches('.score-pill')) {
              node.classList.remove('is-active');
              node.setAttribute('aria-pressed', 'false');
            }
          });
          document.querySelectorAll(`${dataSelector('option-field', option.id)} ${dataSelector('option-id', option.id)}, ${dataSelector('child-wrap', option.id)} [data-child-id]`).forEach(clearFieldValue);
        });
      });
    }

    function applyAutoSelects() {
      logicState.autoSelects.forEach(({ questionId, optionId }) => {
        if (isQuestionUnavailable(questionId) || isOptionHidden(questionId, optionId)) return;
        const input = document.querySelector(`.option${dataSelector('option-id', optionId)} input${selectorAttr('name', questionId)}`);
        if (!input) return;
        if (input.type === 'radio') {
          document.querySelectorAll(`input${selectorAttr('name', questionId)}`).forEach((node) => { if (node !== input) node.checked = false; });
        }
        input.checked = true;
      });
    }

    function syncCacheFromDom(save = true) {
      answerableQuestions.forEach((question) => {
        if (isQuestionUnavailable(question.id)) {
          delete cache.answers[question.id];
          return;
        }
        const collected = collectQuestion(question);
        if (collected) cache.answers[question.id] = collected;
        else delete cache.answers[question.id];
      });
      if (save) saveCache();
    }

    function computeSkippedQuestions(jumpTargets) {
      const skippedQuestions = new Set();
      const orderedScreens = screens().filter((screen) => !['survey', 'finish', 'survey-all'].includes(screen.dataset.schemaType));
      const screenIndexMap = new Map(orderedScreens.map((screen, index) => [screen.dataset.screenId, index]));
      jumpTargets.forEach((targetId, sourceQuestionId) => {
        const sourceScreenId = resolveScreenId(sourceQuestionId) || sourceQuestionId;
        const targetScreenId = resolveScreenId(targetId) || targetId;
        const sourceIndex = screenIndexMap.get(sourceScreenId);
        const targetIndex = screenIndexMap.get(targetScreenId);
        if (sourceIndex == null) return;
        const endExclusive = finishScreenIds.has(targetId)
          ? orderedScreens.length
          : targetIndex;
        if (endExclusive == null || endExclusive <= sourceIndex + 1) return;
        for (let index = sourceIndex + 1; index < endExclusive; index += 1) {
          questionsOnScreen(orderedScreens[index]).forEach((question) => skippedQuestions.add(question.id));
        }
      });
      return skippedQuestions;
    }

    function applyLogicRuntime(options = {}) {
      const preserveActiveId = options.preserveActiveId || document.querySelector('.screen.is-active')?.dataset.screenId || null;
      logicState = computeLogicState();
      logicState.skippedQuestions = computeSkippedQuestions(logicState.jumpTargets);
      document.querySelectorAll('[data-screen-id][data-schema-type]').forEach((node) => {
        let hidden = false;
        if (node.dataset.schemaType === 'finish') {
          hidden = node.dataset.screenId !== logicState.activeFinishId;
        } else if (!['survey', 'finish', 'survey-all'].includes(node.dataset.schemaType)) {
          if (node.dataset.schemaType === 'page') {
            const pageQuestions = questionsOnScreen(node);
            hidden = pageQuestions.length > 0 ? pageQuestions.every((question) => isQuestionUnavailable(question.id)) : false;
          } else {
            hidden = isQuestionUnavailable(node.dataset.screenId);
          }
        }
        node.classList.toggle('is-hidden-by-logic', hidden);
        node.dataset.logicHidden = hidden ? 'true' : 'false';
        if (hidden) node.classList.remove('is-active');
      });
      answerableQuestions.forEach((question) => {
        (question.option || []).forEach((option) => {
          const hidden = isOptionHidden(question.id, option.id);
          const selector = [
            `.option${dataSelector('option-id', option.id)}`,
            dataSelector('option-field', option.id),
            dataSelector('score-option', option.id),
            dataSelector('nps-option', option.id)
          ].join(',');
          document.querySelectorAll(selector).forEach((node) => {
            node.classList.toggle('is-hidden-by-logic', hidden);
            node.dataset.logicHidden = hidden ? 'true' : 'false';
          });
        });
      });
      clearUnavailableState();
      applyAutoSelects();
      updateChildVisibility();
      syncCacheFromDom(false);
      const visibleIds = visibleScreens().map((screen) => screen.dataset.screenId);
      const nextActiveId = preserveActiveId && visibleIds.includes(preserveActiveId) ? preserveActiveId : visibleIds[0] || null;
      if (nextActiveId) showById(nextActiveId);
      else saveCache();
    }
