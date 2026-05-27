    function renderSurvey() {
      const s = surveySchema.survey;
      return screenShell(s.id, 'survey', `<section class="survey-hero"><div class="survey-hero-copy"><div class="survey-kicker">问卷邀请</div>${renderRich(s.title)}${renderRich(s.description)}<div class="trust-meta-list"><div class="trust-meta-item"><strong>填写体验</strong><span>单步作答，过程轻量清晰。</span></div><div class="trust-meta-item"><strong>信息说明</strong><span>你的反馈仅用于服务优化与体验改进。</span></div></div><div class="survey-reason-list"><div class="survey-reason-item">预计耗时较短，可随时完成</div><div class="survey-reason-item">问题聚焦，填写过程更轻松</div><div class="survey-reason-item">提交后将直接完成，不会重复打扰</div></div></div>${renderHeroVisual(s.attribute.media || [], 'survey')}</section><div class="actions" style="grid-column:1 / -1;"><span></span><div class="actions-right"><button class="btn" type="button" data-next>开始填写</button></div></div>`, true);
    }


    function renderManualPage(group, pageIndex) {
      const allowBack = surveySchema.survey.attribute?.allowBack === true;
      const blocks = group.map((question) => renderQuestionBlock(question)).join('');
      return screenShell(`page_${String(pageIndex + 1).padStart(2, '0')}`, 'page', `${blocks}<div class="actions" style="grid-column:1 / -1;">${allowBack ? '<button class="btn secondary" type="button" data-prev>上一页</button>' : '<span></span>'}<div class="actions-right"><button class="btn" type="button" data-next>下一页</button></div></div>`);
    }

    function renderFinish(f) {
      const allowBack = surveySchema.survey.attribute?.allowBack === true;
      return screenShell(f.id, 'finish', `<section class="finish-state"><div class="finish-kicker">反馈确认</div><div class="finish-badge">✓ 即将完成提交</div>${renderHeroVisual(f.media || [], 'finish')}<div class="finish-copy">${renderRich(f.title)}${renderRich(f.description)}</div><div class="finish-note">${escapeHtml(finishSubmitNote(f))}</div><div class="finish-submit-status" data-submit-status aria-live="polite"></div></section><div class="actions" style="grid-column:1 / -1;">${allowBack ? '<button class="btn secondary" type="button" data-prev>上一页</button>' : '<span></span>'}<div class="actions-right"><button class="btn" type="submit">${escapeHtml(finishSubmitButtonLabel(f))}</button></div></div>`, true);
    }

    function screenShell(id, type, inner, dark = false) {
      return `<section class="screen" data-screen-id="${escapeAttr(id)}" data-schema-type="${escapeAttr(type)}"><article class="card ${dark ? 'dark' : ''}"><div class="card-body ${type === 'survey' ? 'hero-grid' : type === 'finish' ? 'finish-grid' : ''}">${inner}</div></article></section>`;
    }


    function render() {
      const onePageOneQuestion = surveySchema.survey.attribute?.onePageOneQuestion === true;
      const defaultFinish = defaultFinishScreen;
      const renderedFinishes = finishScreens.map((finish) => renderFinish(finish));
      if (hasManualPagination && !onePageOneQuestion) {
        form.innerHTML = [renderSurvey(), ...manualPages.map((group, index) => renderManualPage(group, index)), ...renderedFinishes].join('');
      } else if (onePageOneQuestion) {
        form.innerHTML = [renderSurvey(), ...answerableQuestions.map(renderQuestion), ...renderedFinishes].join('');
      } else {
        form.innerHTML = screenShell('all_in_one', 'survey-all', `<div style="grid-column:1 / -1;">${renderRich(surveySchema.survey.title)}${renderRich(surveySchema.survey.description)}</div>${answerableQuestions.map((q) => renderQuestionBlock(q)).join('')}<div style="grid-column:1 / -1;">${renderRich(defaultFinish.title)}${renderRich(defaultFinish.description)}<div class="finish-note">${escapeHtml(finishSubmitNote(defaultFinish))}</div><div class="finish-submit-status" data-submit-status aria-live="polite"></div></div><div class="actions" style="grid-column:1 / -1;"><span></span><div class="actions-right"><button class="btn" type="submit">${escapeHtml(finishSubmitButtonLabel(defaultFinish))}</button></div></div>`);
      }
      rebuildQuestionScreenMap();
      bindEvents();
      hydrateAll();
      const resumePending = hasResumeCandidate();
      const initialScreenId = surveySchema.survey.id;
      applyLogicRuntime({ preserveActiveId: initialScreenId, save: false });
      if (!document.querySelector('.screen.is-active')) showById(initialScreenId, false);
      if (resumePending) openResumePrompt();
    }
