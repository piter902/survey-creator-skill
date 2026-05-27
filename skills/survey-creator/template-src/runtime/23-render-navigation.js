    function screens() {
      return Array.from(document.querySelectorAll('.screen'));
    }

    function questionsOnScreen(screen) {
      if (!screen) return [];
      if (screen.dataset.schemaType === 'page') {
        return Array.from(screen.querySelectorAll('.field[data-screen-id]')).map((field) => questionById(field.dataset.screenId)).filter(Boolean);
      }
      if (['survey', 'finish', 'survey-all'].includes(screen.dataset.schemaType)) return [];
      const question = questionById(screen.dataset.screenId);
      return question ? [question] : [];
    }

    function rebuildQuestionScreenMap() {
      questionToScreenId.clear();
      screens().forEach((screen) => {
        const screenId = screen.dataset.screenId;
        const schemaType = screen.dataset.schemaType;
        if (schemaType === 'page') {
          screen.querySelectorAll('.field[data-screen-id]').forEach((field) => {
            if (field.dataset.screenId) questionToScreenId.set(field.dataset.screenId, screenId);
          });
          return;
        }
        if (!['survey', 'finish', 'survey-all'].includes(schemaType)) {
          questionToScreenId.set(screenId, screenId);
        }
      });
    }

    function visibleScreens() {
      return screens().filter((screen) => !screen.classList.contains('is-hidden-by-logic') && screen.dataset.logicHidden !== 'true');
    }

    function show(index, save = true) {
      const list = visibleScreens();
      if (!list.length) return;
      current = Math.max(0, Math.min(index, list.length - 1));
      const active = list[current];
      const activeType = active?.dataset?.schemaType;
      screens().forEach((screen) => screen.classList.toggle('is-active', screen === active));
      progressBar.style.width = `${list.length <= 1 ? 100 : (current / (list.length - 1)) * 100}%`;
      stepCounter.textContent = `${current + 1} / ${list.length}`;
      if (progressCaption) {
        if (activeType === 'survey') progressCaption.textContent = '当前正在开始填写';
        else if (activeType === 'finish') progressCaption.textContent = '最后一步，确认并提交';
        else progressCaption.textContent = `还有 ${Math.max(list.length - current - 1, 0)} 步完成`;
      }
      if (save) saveCache();
    }

    function resolveScreenId(screenOrQuestionId) {
      if (!screenOrQuestionId) return null;
      if (screens().some((screen) => screen.dataset.screenId === screenOrQuestionId)) return screenOrQuestionId;
      return questionToScreenId.get(screenOrQuestionId) || null;
    }

    function showById(screenId, save = true) {
      const resolvedId = resolveScreenId(screenId) || screenId;
      const list = visibleScreens();
      const index = list.findIndex((screen) => screen.dataset.screenId === resolvedId);
      show(index >= 0 ? index : 0, save);
    }
