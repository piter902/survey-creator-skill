    function extractFieldValue(field) {
      if (!field) return null;
      if (field.matches('[data-range-type]')) {
        const start = field.querySelector('[data-range-role="start"]')?.value || '';
        const end = field.querySelector('[data-range-role="end"]')?.value || '';
        return start || end ? { start, end } : null;
      }
      const value = (field.value || '').trim();
      return value || null;
    }

    function validateByDataType(field, attr = {}) {
      const type = attr.dataType || 'text';
      const value = extractFieldValue(field);
      const empty = !value || (typeof value === 'object' && !value.start && !value.end);
      if (attr.required && empty) return '该字段必填';
      if (empty) return '';
      const scalar = typeof value === 'object' ? `${value.start || ''}${value.end || ''}` : value;
      if (attr.minLength && scalar.length < Number(attr.minLength)) return `至少 ${attr.minLength} 字`;
      if (attr.maxLength && scalar.length > Number(attr.maxLength)) return `最多 ${attr.maxLength} 字`;
      if (type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return '邮箱格式不正确';
      if (type === 'tel' && !/^[+()\-\s\d]{6,20}$/.test(value)) return '请输入有效电话';
      if (type === 'number' && Number.isNaN(Number(value))) return '请输入有效数字';
      if (type === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(value)) return '请输入有效日期';
      if (type === 'time' && !/^\d{2}:\d{2}$/.test(value)) return '请输入有效时间';
      if (type === 'dateTime' && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) return '请输入有效日期时间';
      if ((type === 'dateRange' || type === 'timeRange' || type === 'dateTimeRange') && (!value.start || !value.end)) return '请完整填写开始和结束';
      return '';
    }

    function readChildAnswers(optionEl) {
      const wrap = optionEl.querySelector('.child-list');
      if (!wrap || !wrap.classList.contains('is-visible')) return [];
      return Array.from(wrap.querySelectorAll('[data-child-id]')).map((field) => ({
        childId: field.dataset.childId,
        dataType: JSON.parse(field.dataset.inputAttribute || '{}').dataType || 'text',
        value: extractFieldValue(field)
      })).filter((item) => item.value);
    }

    function collectQuestion(question) {
      const screen = document.querySelector(dataSelector('screen-id', question.id));
      if (!screen || isQuestionUnavailable(question.id)) return null;

      if (question.type === 'radio') {
        const checked = Array.from(screen.querySelectorAll(`input${selectorAttr('name', question.id)}:checked`)).find((input) => !isOptionHidden(question.id, input.value));
        if (!checked) return null;
        const optionEl = checked.closest('.option');
        const child = readChildAnswers(optionEl);
        const value = { optionId: checked.value };
        if (child.length) value.child = child;
        return { questionType: question.type, value };
      }

      if (question.type === 'checkbox') {
        const checked = Array.from(screen.querySelectorAll(`input${selectorAttr('name', question.id)}:checked`)).filter((input) => !isOptionHidden(question.id, input.value));
        if (!checked.length) return null;
        return {
          questionType: question.type,
          value: checked.map((input) => {
            const optionEl = input.closest('.option');
            const item = { optionId: input.value };
            const child = readChildAnswers(optionEl);
            if (child.length) item.child = child;
            return item;
          })
        };
      }

      if (question.type === 'input') {
        const value = question.option.filter((opt) => !isOptionHidden(question.id, opt.id)).map((opt) => {
          const field = screen.querySelector(dataSelector('option-id', opt.id));
          const extracted = extractFieldValue(field);
          if (!extracted) return null;
          return { optionId: opt.id, dataType: opt.attribute?.dataType || 'text', value: extracted };
        }).filter(Boolean);
        if (!value.length) return null;
        return { questionType: question.type, value };
      }

      if (question.type === 'score') {
        const value = Array.from(screen.querySelectorAll('[data-score-option]')).filter((row) => !row.classList.contains('is-hidden-by-logic')).map((row) => {
          const optionId = row.dataset.scoreOption;
          const active = row.querySelector('.score-pill.is-active');
          if (!active) return null;
          return { optionId, score: Number(active.dataset.scoreValue) };
        }).filter(Boolean);
        if (!value.length) return null;
        return { questionType: question.type, value };
      }

      if (question.type === 'nps') {
        const row = Array.from(screen.querySelectorAll('[data-nps-option]')).find((node) => !node.classList.contains('is-hidden-by-logic'));
        const active = row?.querySelector('.score-pill.is-active');
        if (!row || !active) return null;
        return { questionType: question.type, value: { optionId: row.dataset.npsOption, score: Number(active.dataset.scoreValue) } };
      }

      return null;
    }

    function validateQuestion(question) {
      if (!question || isQuestionUnavailable(question.id)) return true;
      const screen = document.querySelector(dataSelector('screen-id', question.id));
      if (!screen) return true;
      screen.querySelectorAll('.error').forEach((el) => el.classList.remove('is-visible'));
      screen.querySelectorAll('.is-invalid').forEach((el) => el.classList.remove('is-invalid'));

      const collected = collectQuestion(question);
      if (question.attribute?.required && !collected) {
        screen.querySelector('[data-error]')?.classList.add('is-visible');
        return false;
      }

      if (question.type === 'input') {
        for (const opt of question.option.filter((item) => !isOptionHidden(question.id, item.id))) {
          const field = screen.querySelector(dataSelector('option-id', opt.id));
          const msg = validateByDataType(field, opt.attribute || {});
          if (msg) {
            field.classList.add('is-invalid');
            const err = screen.querySelector('[data-error]');
            if (err) {
              err.textContent = msg;
              err.classList.add('is-visible');
            }
            return false;
          }
        }
      }

      if (question.type === 'score' && question.attribute?.required) {
        const rows = Array.from(screen.querySelectorAll('[data-score-option]')).filter((row) => !row.classList.contains('is-hidden-by-logic'));
        const complete = rows.every((row) => row.querySelector('.score-pill.is-active'));
        if (!complete) {
          screen.querySelector('[data-error]')?.classList.add('is-visible');
          return false;
        }
      }

      if (question.type === 'nps' && question.attribute?.required) {
        const row = Array.from(screen.querySelectorAll('[data-nps-option]')).find((node) => !node.classList.contains('is-hidden-by-logic'));
        if (!row?.querySelector('.score-pill.is-active')) {
          screen.querySelector('[data-error]')?.classList.add('is-visible');
          return false;
        }
      }

      for (const optionEl of screen.querySelectorAll('.option')) {
        const checked = optionEl.querySelector('input:checked');
        if (!checked) continue;
        const childFields = optionEl.querySelectorAll('[data-child-id]');
        for (const field of childFields) {
          const attr = JSON.parse(field.dataset.inputAttribute || '{}');
          const msg = validateByDataType(field, attr);
          if (msg) {
            field.classList.add('is-invalid');
            const err = optionEl.querySelector(dataSelector('child-error', field.dataset.childId));
            if (err) {
              err.textContent = msg;
              err.classList.add('is-visible');
            }
            return false;
          }
        }
      }
      return true;
    }

    function persist(question, save = true) {
      if (!question) return;
      const collected = collectQuestion(question);
      if (collected) cache.answers[question.id] = collected;
      else delete cache.answers[question.id];
      if (save) saveCache();
    }

    function hydrateRangeField(field, value) {
      if (!field || !value || typeof value !== 'object') return;
      const start = field.querySelector('[data-range-role="start"]');
      const end = field.querySelector('[data-range-role="end"]');
      if (start) start.value = value.start || '';
      if (end) end.value = value.end || '';
    }

    function hydrateAll() {
      Object.entries(cache.answers || {}).forEach(([questionId, answer]) => {
        const screen = document.querySelector(dataSelector('screen-id', questionId));
        if (!screen) return;

        if (answer.questionType === 'radio') {
          const input = screen.querySelector(`input${selectorAttr('value', answer.value.optionId)}`);
          if (input) input.checked = true;
          (answer.value.child || []).forEach((item) => {
            const child = screen.querySelector(dataSelector('child-id', item.childId));
            if (!child) return;
            if (child.matches('[data-range-type]')) hydrateRangeField(child, item.value);
            else child.value = typeof item.value === 'object' ? '' : (item.value || '');
          });
        }

        if (answer.questionType === 'checkbox') {
          (answer.value || []).forEach((item) => {
            const input = screen.querySelector(`input${selectorAttr('value', item.optionId)}`);
            if (input) input.checked = true;
            (item.child || []).forEach((childItem) => {
              const child = screen.querySelector(dataSelector('child-id', childItem.childId));
              if (!child) return;
              if (child.matches('[data-range-type]')) hydrateRangeField(child, childItem.value);
              else child.value = typeof childItem.value === 'object' ? '' : (childItem.value || '');
            });
          });
        }

        if (answer.questionType === 'input') {
          (answer.value || []).forEach((item) => {
            const field = screen.querySelector(dataSelector('option-id', item.optionId));
            if (!field) return;
            if (field.matches('[data-range-type]')) hydrateRangeField(field, item.value);
            else field.value = typeof item.value === 'object' ? '' : (item.value || '');
          });
        }

        if (answer.questionType === 'score') {
          (answer.value || []).forEach((item) => {
            const button = screen.querySelector(`${dataSelector('score-option-id', item.optionId)}${dataSelector('score-value', formatScoreValue(item.score))}`);
            if (button) updateScoreDisplay(button);
          });
        }


        if (answer.questionType === 'nps') {
          const button = screen.querySelector(`${dataSelector('score-option-id', answer.value.optionId)}${dataSelector('score-value', formatScoreValue(answer.value.score))}`);
          if (button) updateScoreDisplay(button);
        }
      });
      updateChildVisibility();
    }

    function assemblePayload() {
      answerableQuestions.forEach((q) => persist(q));
      const extra = (() => {
        const params = new URLSearchParams(window.location.search || '');
        const data = {};
        params.forEach((value, key) => {
          if (Object.prototype.hasOwnProperty.call(data, key)) {
            if (Array.isArray(data[key])) data[key].push(value);
            else data[key] = [data[key], value];
          } else {
            data[key] = value;
          }
        });
        return data;
      })();
      return {
        surveyId,
        submittedAt: Date.now(),
        extra,
        answers: Object.entries(cache.answers).filter(([questionId]) => !isQuestionHidden(questionId)).map(([questionId, answer]) => ({
          questionId,
          questionType: answer.questionType,
          value: answer.value
        })).filter((item) => !isQuestionUnavailable(item.questionId))
      };
    }

    function currentQuestion() {
      return currentScreenQuestions()[0] || null;
    }

    function currentScreenQuestions() {
      const screen = visibleScreens()[current] || screens()[current];
      return questionsOnScreen(screen);
    }

    function currentScreenId() {
      return (visibleScreens()[current] || screens()[current])?.dataset.screenId || document.querySelector('.screen.is-active')?.dataset.screenId || null;
    }

    function hasResumeCandidate() {
      const answerCount = Object.keys(cache.answers || {}).length;
      if (!answerCount) return false;
      const updatedAtMs = Date.parse(cache.updatedAt || '');
      if (Number.isNaN(updatedAtMs)) return false;
      return updatedAtMs <= pageLoadStartedAt;
    }

    function resetQuestionStates() {
      answerableQuestions.forEach((question) => clearQuestionState(question));
    }

    function resetForFreshStart() {
      localStorage.removeItem(cacheKey);
      cache = emptyCache();
      logicState = { hiddenQuestions: new Set(), hiddenOptions: new Set(), skippedQuestions: new Set(), jumpTargets: new Map(), autoSelects: [] };
      form.reset();
      resetQuestionStates();
      updateChildVisibility();
      applyLogicRuntime({ preserveActiveId: surveySchema.survey.id });
      showById(surveySchema.survey.id, false);
      saveCache();
    }

    function dismissResumePrompt() {
      document.querySelector('.resume-overlay')?.remove();
    }

    function openResumePrompt() {
      dismissResumePrompt();
      const overlay = document.createElement('div');
      overlay.className = 'resume-overlay is-visible';
      const lastSaved = formatResumeTime(cache.updatedAt);
      overlay.innerHTML = `
        <div class="resume-dialog" role="dialog" aria-modal="true" aria-labelledby="resumeDialogTitle">
          <div class="resume-dialog-kicker">断点续答</div>
          <h2 class="resume-dialog-title" id="resumeDialogTitle">检测到你上次有未完成的作答</h2>
          <p class="resume-dialog-desc">你可以继续上次离开的进度，也可以清空已有内容，重新开始本次问卷。</p>
          <div class="resume-dialog-meta">${escapeHtml(lastSaved ? `上次保存时间：${lastSaved}` : '已为你保留上次的作答进度。')}</div>
          <div class="resume-dialog-actions">
            <button class="btn secondary" type="button" data-resume-restart>重新开始作答</button>
            <button class="btn" type="button" data-resume-continue>继续上次作答</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
      overlay.querySelector('[data-resume-restart]')?.addEventListener('click', () => {
        dismissResumePrompt();
        resetForFreshStart();
      }, { once: true });
      overlay.querySelector('[data-resume-continue]')?.addEventListener('click', () => {
        dismissResumePrompt();
        const resumeTarget = cache.meta?.lastScreenId || surveySchema.survey.id;
        applyLogicRuntime({ preserveActiveId: resumeTarget });
        showById(resumeTarget, false);
      }, { once: true });
    }

    function persistQuestions(questions, save = true) {
      questions.forEach((question) => persist(question, false));
      if (save) saveCache();
    }

    function validateQuestions(questions) {
      for (const question of questions) {
        if (!validateQuestion(question)) return false;
      }
      return true;
    }

    function activeFinishScreen() {
      const activeId = logicState.activeFinishId || currentScreenId();
      return finishScreens.find((item) => item.id === activeId)
        || finishScreens.find((item) => item.id === currentScreenId())
        || defaultFinishScreen;
    }

    function submitStatusNode() {
      return document.querySelector('.screen.is-active [data-submit-status]') || form.querySelector('[data-submit-status]');
    }

    function setSubmitStatus(message, actionsHtml = '') {
      const node = submitStatusNode();
      if (!node) return;
      node.innerHTML = `<div class="submit-status-card"><div class="submit-status-text">${escapeHtml(message)}</div>${actionsHtml}</div>`;
      node.classList.add('is-visible');
    }

    function setSubmitButtonsDisabled(disabled) {
      document.querySelectorAll('button[type="submit"]').forEach((button) => { button.disabled = disabled; });
    }

    function submitEndpoint() {
      const configured = surveySchema.survey.attribute?.submitEndpoint || surveySchema.survey.submitEndpoint;
      return typeof configured === 'string' && configured.trim() ? configured.trim() : DEFAULT_SUBMIT_ENDPOINT;
    }

    function isLocalPreview() {
      return window.location.protocol === 'file:';
    }

    async function submitPayload(payload) {
      window.__surveyPayloads = Array.isArray(window.__surveyPayloads) ? window.__surveyPayloads : [];
      window.__surveyPayloads.push(payload);
      console.log(payload);

      if (typeof window.__surveySubmit === 'function') {
        return window.__surveySubmit(payload, { endpoint: submitEndpoint(), surveyId });
      }

      if (isLocalPreview()) {
        return { ok: true, localPreview: true };
      }

      let response;
      try {
        response = await fetch(submitEndpoint(), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(payload),
          credentials: 'same-origin'
        });
      } catch (error) {
        return {
          ok: false,
          code: 'NETWORK_ERROR',
          message: '提交失败，请检查网络后重试。',
          detail: String(error && error.message ? error.message : error)
        };
      }

      let data = null;
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        try {
          data = await response.json();
        } catch {
          data = null;
        }
      }

      if (!response.ok) {
        return {
          ok: false,
          code: data?.code || `HTTP_${response.status}`,
          message: data?.message || '提交失败，请稍后重试。',
          status: response.status
        };
      }

      if (data && data.ok === false) {
        return {
          ok: false,
          code: data.code || 'SUBMIT_REJECTED',
          message: data.message || '提交未通过服务端校验，请检查填写内容后重试。'
        };
      }

      return data || { ok: true };
    }

    function resetAfterSubmit() {
      cache = { surveyId, updatedAt: new Date().toISOString(), answers: {} };
      form.reset();
      updateChildVisibility();
      show(0, false);
    }

    function navigateAfterSubmit(action) {
      const record = {
        type: action.type,
        url: action.url,
        mode: action.mode,
        delayMs: action.delayMs,
        openIn: action.openIn,
        surveyId,
        triggeredAt: new Date().toISOString()
      };
      window.__surveyRedirects = Array.isArray(window.__surveyRedirects) ? window.__surveyRedirects : [];
      window.__surveyRedirects.push(record);
      if (typeof window.__surveyNavigate === 'function') {
        window.__surveyNavigate(record);
        return;
      }
      if (action.openIn === 'blank') {
        const opened = window.open(action.url, '_blank', 'noopener,noreferrer');
        if (!opened) window.location.assign(action.url);
        return;
      }
      window.location.assign(action.url);
    }

    function runPostSubmitAction(finish, payload) {
      const action = normalizePostSubmitAction(finish?.postSubmit);
      window.__surveySubmitEvents = Array.isArray(window.__surveySubmitEvents) ? window.__surveySubmitEvents : [];
      window.__surveySubmitEvents.push({
        surveyId,
        finishId: finish?.id || defaultFinishScreen.id,
        submittedAt: payload?.submittedAt || Date.now(),
        postSubmit: action
      });

      if (!action) {
        resetAfterSubmit();
        alert('提交成功，感谢你的填写。');
        return;
      }

      setSubmitButtonsDisabled(true);
      const immediateActionHtml = action.mode === 'delay'
        ? `<div class="submit-status-actions"><button class="btn secondary" type="button" data-submit-go-now>立即前往</button></div>`
        : '';

      if (action.mode === 'delay') {
        const renderCountdown = () => {
          const seconds = Math.max(1, Math.ceil(action.delayMs / 1000));
          setSubmitStatus(`提交成功，${seconds} 秒后将跳转至下一步。`, immediateActionHtml);
          submitStatusNode()?.querySelector('[data-submit-go-now]')?.addEventListener('click', () => navigateAfterSubmit(action), { once: true });
        };
        renderCountdown();
        const startedAt = Date.now();
        const timer = window.setInterval(() => {
          const remaining = Math.max(0, action.delayMs - (Date.now() - startedAt));
          const seconds = Math.max(1, Math.ceil(remaining / 1000));
          setSubmitStatus(`提交成功，${seconds} 秒后将跳转至下一步。`, immediateActionHtml);
          submitStatusNode()?.querySelector('[data-submit-go-now]')?.addEventListener('click', () => navigateAfterSubmit(action), { once: true });
          if (remaining <= 0) {
            window.clearInterval(timer);
            navigateAfterSubmit(action);
          }
        }, 250);
        return;
      }

      setSubmitStatus('提交成功，正在前往下一步...');
      navigateAfterSubmit(action);
    }

    function bindEvents() {
      form.addEventListener('click', (e) => {
        if (e.target.matches('[data-next]')) {
          const questions = currentScreenQuestions();
          if (!validateQuestions(questions)) return;
          persistQuestions(questions, false);
          const preserveId = currentScreenId();
          applyLogicRuntime({ preserveActiveId: preserveId });
          const nextTarget = questions.map((question) => logicState.jumpTargets.get(question.id)).find(Boolean);
          if (nextTarget) showById(nextTarget);
          else show(current + 1);
        }
        if (e.target.matches('[data-prev]')) {
          persistQuestions(currentScreenQuestions(), false);
          applyLogicRuntime({ preserveActiveId: currentScreenId() });
          show(current - 1);
        }
        const scoreBtn = e.target.closest('.score-pill');
        if (scoreBtn) {
          updateScoreDisplay(scoreBtn);
          const questions = currentScreenQuestions();
          if (questions.length) {
            persistQuestions(questions, false);
            applyLogicRuntime({ preserveActiveId: currentScreenId() });
          }
        }
      });

      form.addEventListener('change', (e) => {
        if (e.target.matches('input[type="checkbox"]')) {
          const option = e.target.closest('.option');
          const all = Array.from(e.target.closest('.options').querySelectorAll('input[type="checkbox"]'));
          const exclusive = option?.dataset.exclusive === 'true';
          const mutual = option?.dataset.mutualExclusion === 'true';
          if (e.target.checked && exclusive) {
            all.forEach((item) => { if (item !== e.target) item.checked = false; });
          } else if (e.target.checked) {
            all.forEach((item) => { if (item.closest('.option')?.dataset.exclusive === 'true') item.checked = false; });
          }
          if (e.target.checked && mutual) {
            all.forEach((item) => {
              const otherMutual = item.closest('.option')?.dataset.mutualExclusion === 'true';
              if (item !== e.target && otherMutual) item.checked = false;
            });
          }
        }
        updateChildVisibility();
        persistQuestions(currentScreenQuestions(), false);
        applyLogicRuntime({ preserveActiveId: currentScreenId() });
      });

      form.addEventListener('input', () => {
        persistQuestions(currentScreenQuestions(), false);
        applyLogicRuntime({ preserveActiveId: currentScreenId() });
      });

      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        applyLogicRuntime({ preserveActiveId: currentScreenId() });
        for (let i = 0; i < answerableQuestions.length; i++) {
          const question = answerableQuestions[i];
          if (isQuestionUnavailable(question.id)) continue;
          if (!validateQuestion(question)) {
            if (surveySchema.survey.attribute?.onePageOneQuestion === true) showById(question.id);
            return;
          }
          persist(question, false);
        }
        saveCache();
        const payload = assemblePayload();
        setSubmitButtonsDisabled(true);
        setSubmitStatus('正在提交，请稍候...');
        const submitResult = await submitPayload(payload);
        if (!submitResult || submitResult.ok === false) {
          setSubmitButtonsDisabled(false);
          setSubmitStatus(submitResult?.message || '提交失败，请稍后重试。');
          return;
        }
        localStorage.removeItem(cacheKey);
        runPostSubmitAction(activeFinishScreen(), payload);
      });
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }
