    const richMediaImg = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNzIwIiBoZWlnaHQ9IjQwMCIgdmlld0JveD0iMCAwIDcyMCA0MDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjcyMCIgaGVpZ2h0PSI0MDAiIHJ4PSIzMiIgZmlsbD0idXJsKCNnKSIvPjxjaXJjbGUgY3g9IjEyNSIgY3k9IjExNSIgcj0iNjAiIGZpbGw9IndoaXRlIiBmaWxsLW9wYWNpdHk9Ii4xNSIvPjxwYXRoIGQ9Ik02MCAzMjBDMTQ1IDI1NSAyNTUgMjI1IDM2MCAyNDVDNDU1IDI2MyA1NTIgMzQwIDY2MCAyNzVWNDAwSDYwVjMyMFoiIGZpbGw9IndoaXRlIiBmaWxsLW9wYWNpdHk9Ii4xMiIvPjxkZWZzPjxsaW5lYXJHcmFkaWVudCBpZD0iZyIgeDE9IjAiIHkxPSIwIiB4Mj0iNzIwIiB5Mj0iNDAwIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHN0b3Agc3RvcC1jb2xvcj0iIzVCN0NGRiIvPjxzdG9wIG9mZnNldD0iMSIgc3RvcC1jb2xvcj0iIzI1QzJBMCIvPjwvbGluZWFyR3JhZGllbnQ+PC9kZWZzPjwvc3ZnPg==';

    const surveySchema = {
      survey: {
        type: 'survey',
        id: 'survey-310000000000000001',
        title: '<h1>问卷填写示例</h1>',
        description: '<p>感谢你参与本次调研，整份问卷预计耗时 2~3 分钟。你的回答仅用于产品优化与体验改进。</p>',
        attribute: {
          onePageOneQuestion: true,
          allowBack: true,
          media: [
            { type: 'image', url: richMediaImg }
          ]
        }
      },
      questions: [
        {
          type: 'radio',
          id: 'radio-123456',
          title: '<h2>你通常会使用哪类问卷？<span class="required">*</span></h2>',
          description: '<p>请选择最符合你当前场景的一项。</p>',
          attribute: { required: true, random: true, media: [] },
          option: [
            { title: '<p><strong>用户满意度调研</strong></p>', id: 'radio-123457', attribute: { random: false, media: [] } },
            { title: '<p><strong>活动报名</strong></p>', id: 'radio-123458', attribute: { media: [] } },
            {
              title: '<p><strong>其他，请说明</strong></p>',
              id: 'radio-123459',
              attribute: { media: [] },
              child: [
                {
                  type: 'input',
                  id: 'input-123460',
                  title: '<p>补充说明</p>',
                  attribute: { dataType: 'text', required: true, placeholder: '请输入你的问卷场景', minLength: 2, maxLength: 120 }
                }
              ]
            }
          ]
        },
        {
          type: 'checkbox',
          id: 'checkbox-123461',
          title: '<h2>你最关注哪些填写体验？<span class="required">*</span></h2>',
          description: '<p>可多选，我们会据此优化问卷体验。</p>',
          attribute: { required: true, random: true, media: [] },
          option: [
            { title: '<p>富文本标题/描述</p>', id: 'checkbox-123462', attribute: { random: false } },
            { title: '<p>一页一题</p>', id: 'checkbox-123463', attribute: {} },
            { title: '<p>本地缓存</p>', id: 'checkbox-123464', attribute: {} },
            { title: '<p>仅生成单页整表单</p>', id: 'checkbox-123465', attribute: { 'mutual-exclusion': true } },
            { title: '<p>仅生成分页问卷</p>', id: 'checkbox-123466', attribute: { 'mutual-exclusion': true } },
            { title: '<p>以上都不需要</p>', id: 'checkbox-123467', attribute: { exclusive: true } }
          ]
        },
        {
          type: 'input',
          id: 'input-123468',
          title: '<h2>补充说明</h2>',
          description: '<p>如果你愿意，可以补充你的联系方式与更多建议。</p>',
          attribute: { required: false, media: [] },
          option: [
            {
              title: '<p>联系人邮箱</p>',
              id: 'input-123469',
              attribute: { dataType: 'email', required: false, placeholder: 'name@example.com', minLength: 0, maxLength: 120 }
            },
            {
              title: '<p>预计调研时间范围</p>',
              id: 'input-123470',
              attribute: { dataType: 'dateRange', required: false, placeholder: '', minLength: 0, maxLength: 40 }
            },
            {
              title: '<p>风格说明</p>',
              id: 'input-123471',
              attribute: { dataType: 'text', required: false, placeholder: '例如：AI Native、黑色高级感、轻盈 toC', minLength: 0, maxLength: 240 }
            }
          ]
        }
      ],
      finish: [
        {
          type: 'finish',
          id: 'finish-123472',
          title: '<h2>提交前请确认信息无误</h2>',
          description: '<p>提交后我们会记录你的答案，用于后续分析与体验优化。</p>',
          media: []
        }
      ]
    };

    const surveyStylePack = "consumer-minimal";

    const form = document.getElementById('surveyForm');
    const progressBar = document.getElementById('progressBar');
    const stepCounter = document.getElementById('stepCounter');
    const progressCaption = document.getElementById('progressCaption');
    const surveyId = surveySchema.survey.id;
    const pageLoadStartedAt = Date.now();
    const cacheKey = `survey_step_cache_${surveyId}`;
    const logicRules = Array.isArray(surveySchema.logic) ? surveySchema.logic : [];
    const finishScreens = (() => {
      const rawFinish = Array.isArray(surveySchema.finish)
        ? surveySchema.finish
        : surveySchema.finish && typeof surveySchema.finish === 'object'
        ? [surveySchema.finish]
        : [];
      const normalized = rawFinish
        .filter((item) => item && typeof item === 'object')
        .map((item, index) => ({
          ...item,
          type: 'finish',
          id: item.id || `finish-${String(index + 1).padStart(6, '0')}`,
          media: Array.isArray(item.media) ? item.media : []
        }));
      if (!normalized.length) {
        normalized.push({
          type: 'finish',
          id: 'finish-999999',
          title: '<h2>提交完成</h2>',
          description: '<p>感谢你的填写。</p>',
          media: []
        });
      }
      return normalized;
    })();
    surveySchema.finish = finishScreens;
    const defaultFinishScreen = finishScreens[0];
    const finishScreenIds = new Set(finishScreens.map((item) => item.id).filter(Boolean));
    const rawQuestions = Array.isArray(surveySchema.questions) ? surveySchema.questions : [];
    const answerableQuestions = rawQuestions.filter((question) => question?.type !== 'Pagination');
    document.body.dataset.stylePack = surveyStylePack || 'consumer-minimal';
    const hasManualPagination = rawQuestions.some((question) => question?.type === 'Pagination');
    const manualPages = buildManualPagesFromSeparators(rawQuestions);
    const questionOrder = new Map(answerableQuestions.map((question, index) => [question.id, index]));
    const questionToScreenId = new Map();
    const logicShowQuestionTargets = new Set(logicRules.filter((rule) => rule?.action?.type === 'show_question' && rule?.action?.targetQuestionId).map((rule) => rule.action.targetQuestionId));
    const logicShowOptionTargets = new Set(logicRules.filter((rule) => rule?.action?.type === 'show_option' && rule?.action?.targetQuestionId && rule?.action?.targetOptionId).map((rule) => `${rule.action.targetQuestionId}::${rule.action.targetOptionId}`));
    let logicState = { hiddenQuestions: new Set(), hiddenOptions: new Set(), skippedQuestions: new Set(), jumpTargets: new Map(), autoSelects: [] };
    let current = 0;
    let cache = loadCache();

    function emptyCache() {
      return {
        surveyId,
        updatedAt: new Date().toISOString(),
        answers: {},
        meta: {
          lastScreenId: surveySchema.survey.id
        }
      };
    }

    function normalizeCache(raw) {
      const fallback = emptyCache();
      if (!raw || typeof raw !== 'object') return fallback;
      const answers = raw.answers && typeof raw.answers === 'object' && !Array.isArray(raw.answers) ? raw.answers : {};
      const meta = raw.meta && typeof raw.meta === 'object' && !Array.isArray(raw.meta) ? raw.meta : {};
      return {
        surveyId,
        updatedAt: typeof raw.updatedAt === 'string' && raw.updatedAt ? raw.updatedAt : fallback.updatedAt,
        answers,
        meta: {
          lastScreenId: typeof meta.lastScreenId === 'string' && meta.lastScreenId ? meta.lastScreenId : fallback.meta.lastScreenId
        }
      };
    }

    function loadCache() {
      try {
        return normalizeCache(JSON.parse(localStorage.getItem(cacheKey)));
      } catch {
        return emptyCache();
      }
    }

    function saveCache() {
      const activeScreenId = document.querySelector('.screen.is-active')?.dataset?.screenId;
      if (!cache.meta || typeof cache.meta !== 'object' || Array.isArray(cache.meta)) cache.meta = { lastScreenId: surveySchema.survey.id };
      if (activeScreenId) cache.meta.lastScreenId = activeScreenId;
      cache.updatedAt = new Date().toISOString();
      localStorage.setItem(cacheKey, JSON.stringify(cache));
    }

    function buildManualPagesFromSeparators(questions) {
      const pages = [];
      let group = [];
      questions.forEach((question) => {
        if (!question || question.type === 'Pagination') {
          if (group.length) pages.push(group);
          group = [];
          return;
        }
        group.push(question);
      });
      if (group.length) pages.push(group);
      if (!pages.length && answerableQuestions.length) pages.push([...answerableQuestions]);
      return pages;
    }
