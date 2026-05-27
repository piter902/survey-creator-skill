    function renderScoreQuestion(question) {
      return `<div class="score-list">${(question.option || []).map((opt) => {
        const descMap = opt.attribute?.scoreDesc || {};
        const values = scoreValues(opt);
        const safeOptionId = escapeAttr(opt.id);
        return `<div class="score-item score-card" data-score-option="${safeOptionId}" data-option-field="${safeOptionId}"><div class="field-label">${renderRich(opt.title)}</div>${renderMedia(opt.attribute?.media || [], 'option')}<div class="score-scale">${values.map((value) => {
          const display = formatScoreValue(value);
          return `<button class="score-pill score-pill--card" type="button" aria-pressed="false" aria-label="评分 ${escapeAttr(display)}" data-score-option-id="${safeOptionId}" data-score-value="${escapeAttr(display)}"><span class="score-pill-value">${escapeAttr(display)}</span><span class="score-pill-hint">分</span></button>`;
        }).join('')}</div><div class="score-desc" data-score-desc-for="${safeOptionId}"></div></div>`;
      }).join('')}</div><div class="error" role="alert" data-error>请完成当前评分题。</div>`;
    }


    function npsValues(option) {
      const scope = Array.isArray(option?.attribute?.scope) && option.attribute.scope.length === 2 ? option.attribute.scope : [0, 10];
      const min = Number(scope[0]);
      const max = Number(scope[1]);
      const values = [];
      for (let cur = min; cur <= max; cur += 1) values.push(cur);
      return values;
    }

    function renderNpsQuestion(question) {
      const opt = (question.option || [])[0] || { id: `${question.id}_nps`, attribute: { scope: [0, 10] } };
      const values = npsValues(opt);
      const safeOptionId = escapeAttr(opt.id);
      return `<div class="score-list nps-list"><div class="score-item nps-item score-card" data-nps-option="${safeOptionId}" data-option-field="${safeOptionId}">${renderMedia(opt.attribute?.media || [], 'option')}<div class="score-scale nps-scale">${values.map((value) => {
        const display = formatScoreValue(value);
        return `<button class="score-pill nps-pill score-pill--card" type="button" aria-pressed="false" aria-label="NPS ${escapeAttr(display)} 分" data-score-option-id="${safeOptionId}" data-score-value="${escapeAttr(display)}"><span class="score-pill-value">${escapeAttr(display)}</span><span class="score-pill-hint">分</span></button>`;
      }).join('')}</div><div class="score-desc" data-score-desc-for="${safeOptionId}"></div></div></div><div class="error" role="alert" data-error>请选择一个 NPS 分值。</div>`;
    }


    function renderOption(question, option) {
      const children = option.child || [];
      const safeQuestionId = escapeAttr(question.id);
      const safeOptionId = escapeAttr(option.id);
      const childHtml = children.length
        ? `<div class="child-list" data-child-wrap="${safeOptionId}">${children.map((child) => `<div class="field"><div class="field-label">${renderRich(child.title)}</div>${createInputControl(child.attribute?.dataType || 'text', child.attribute || {}, `${question.id}__${option.id}__${child.id}`, '', child.id)}<div class="error" role="alert" data-child-error="${escapeAttr(child.id)}">请完善该补充内容。</div></div>`).join('')}</div>`
        : '';
      const exclusive = option.attribute?.exclusive === true;
      const mutual = option.attribute?.['mutual-exclusion'] === true;
      const hasMedia = Array.isArray(option.attribute?.media) && option.attribute.media.length > 0;
      return `<div class="option ${hasMedia ? 'option--media' : 'option--plain'}" data-option-id="${safeOptionId}" data-exclusive="${exclusive}" data-mutual-exclusion="${mutual}"><label class="option-card"><input type="${question.type === 'radio' ? 'radio' : 'checkbox'}" name="${safeQuestionId}" value="${safeOptionId}" data-option-id="${safeOptionId}" ${children.length ? 'data-has-child="true"' : ''} /><span class="option-card-indicator" aria-hidden="true"></span><div class="option-card-body"><div class="option-copy">${renderRich(option.title)}</div>${hasMedia ? renderMedia(option.attribute?.media || [], 'option') : ''}</div><span class="option-card-arrow" aria-hidden="true">›</span></label>${childHtml}</div>`;
    }

    function renderQuestion(question) {
      const options = question.option ? shuffleIfNeeded(question.option, question.attribute?.random === true) : [];
      const content = question.type === 'input'
        ? `<div class="fields">${question.option.map((opt) => `<div class="field" data-option-field="${escapeAttr(opt.id)}"><div class="field-label">${renderRich(opt.title)}</div>${createInputControl(opt.attribute?.dataType || 'text', opt.attribute || {}, question.id, opt.id, '')}</div>`).join('')}<div class="error" role="alert" data-error>请按输入题规则完成填写。</div></div>`
        : question.type === 'score'
        ? renderScoreQuestion(question)
        : question.type === 'nps'
        ? renderNpsQuestion(question)
        : `<div class="options">${options.map((opt) => renderOption(question, opt)).join('')}</div><div class="error" role="alert" data-error>请完成当前题目。</div>`;
      const allowBack = surveySchema.survey.attribute?.allowBack === true;
      return screenShell(question.id, question.type, `<div class="question-stage-meta" style="grid-column:1 / -1;"><div class="question-index">第 ${String(questionNumber(question.id)).padStart(2, '0')} 题</div>${question.attribute?.required ? '<div class="chip-row"><span class="chip warn">必填</span></div>' : ''}</div><div class="question-main" style="grid-column:1 / -1;">${renderRich(question.title)}${renderRich(question.description)}</div><div class="question-content" style="grid-column:1 / -1;">${renderMedia(question.attribute?.media || [], 'question')}${content}</div><div class="actions" style="grid-column:1 / -1;">${allowBack ? '<button class="btn secondary" type="button" data-prev>上一页</button>' : '<span></span>'}<div class="actions-right"><button class="btn" type="button" data-next>下一页</button></div></div>`);
    }


    function renderQuestionBlock(question) {
      const options = question.option ? shuffleIfNeeded(question.option, question.attribute?.random === true) : [];
      const content = question.type === 'input'
        ? `<div class="fields">${question.option.map((opt) => `<div class="field" data-option-field="${escapeAttr(opt.id)}"><div class="field-label">${renderRich(opt.title)}</div>${createInputControl(opt.attribute?.dataType || 'text', opt.attribute || {}, question.id, opt.id, '')}</div>`).join('')}<div class="error" role="alert" data-error>请按输入题规则完成填写。</div></div>`
        : question.type === 'score'
        ? renderScoreQuestion(question)
        : question.type === 'nps'
        ? renderNpsQuestion(question)
        : `<div class="options">${options.map((opt) => renderOption(question, opt)).join('')}</div><div class="error" role="alert" data-error>请完成当前题目。</div>`;
      return `<section class="field" data-screen-id="${escapeAttr(question.id)}" data-schema-type="${escapeAttr(question.type)}"><div class="question-stage-meta"><div class="question-index">第 ${String(questionNumber(question.id)).padStart(2, '0')} 题</div>${question.attribute?.required ? '<div class="chip-row"><span class="chip warn">必填</span></div>' : ''}</div><div class="question-main">${renderRich(question.title)}${renderRich(question.description)}</div><div class="question-content">${renderMedia(question.attribute?.media || [], 'question')}${content}</div></section>`;
    }
