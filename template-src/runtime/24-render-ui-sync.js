    function visibleChildWrapForInput(input) {
      return input.closest('.option')?.querySelector(dataSelector('child-wrap', input.value));
    }

    function updateChildVisibility() {
      document.querySelectorAll('.option input[data-has-child]').forEach((input) => {
        const wrap = visibleChildWrapForInput(input);
        if (wrap) wrap.classList.toggle('is-visible', input.checked && !input.closest('.option')?.classList.contains('is-hidden-by-logic'));
      });
    }

    function scoreDescForValue(scoreDesc = {}, scoreValue) {
      if (scoreDesc[scoreValue]) return scoreDesc[scoreValue];
      const numeric = Number(scoreValue);
      for (const [range, label] of Object.entries(scoreDesc)) {
        if (!range.includes('-')) continue;
        const [start, end] = range.split('-').map(Number);
        if (!Number.isNaN(start) && !Number.isNaN(end) && numeric >= start && numeric <= end) return label;
      }
      return '';
    }

    function updateScoreDisplay(button) {
      const optionId = button.dataset.scoreOptionId;
      const scoreValue = button.dataset.scoreValue;
      const screen = button.closest('[data-screen-id]');
      screen.querySelectorAll(dataSelector('score-option-id', optionId)).forEach((el) => {
        const active = el === button;
        el.classList.toggle('is-active', active);
        el.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      const candidateQuestions = questionsOnScreen(screen);
      const question = (candidateQuestions.length ? candidateQuestions : answerableQuestions).find((item) => (item.option || []).some((opt) => opt.id === optionId));
      const option = question?.option?.find((item) => item.id === optionId);
      const desc = scoreDescForValue(option?.attribute?.scoreDesc || {}, scoreValue);
      const descEl = screen.querySelector(dataSelector('score-desc-for', optionId));
      if (descEl) descEl.textContent = desc;
    }
