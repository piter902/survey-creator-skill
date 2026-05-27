    function shuffleIfNeeded(items, shouldRandom) {
      const list = [...items];
      if (!shouldRandom || list.length <= 1) return list;
      const fixed = [];
      const movable = [];
      list.forEach((item, index) => {
        if (item.attribute?.random === false) fixed.push({ index, item });
        else movable.push(item);
      });
      for (let i = movable.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [movable[i], movable[j]] = [movable[j], movable[i]];
      }
      const next = new Array(list.length);
      fixed.forEach(({ index, item }) => { next[index] = item; });
      let cursor = 0;
      for (let i = 0; i < next.length; i++) if (!next[i]) next[i] = movable[cursor++];
      return next;
    }

    function sanitizeRichText(html) {
      const input = typeof html === 'string' ? html : '';
      const parser = new DOMParser();
      const doc = parser.parseFromString(`<div>${input}</div>`, 'text/html');
      const root = doc.body.firstElementChild;
      const allowedTags = new Set(['DIV', 'P', 'SPAN', 'STRONG', 'B', 'EM', 'I', 'U', 'BR', 'UL', 'OL', 'LI', 'BLOCKQUOTE', 'CODE', 'PRE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'A']);
      const allowedAttrs = { A: new Set(['href', 'target', 'rel']) };
      const isSafeHref = (value) => /^(https?:|mailto:|tel:|#|\/)/i.test(value);

      function clean(node) {
        const children = Array.from(node.childNodes);
        for (const child of children) {
          if (child.nodeType === Node.TEXT_NODE) continue;
          if (child.nodeType !== Node.ELEMENT_NODE) {
            child.remove();
            continue;
          }
          const tag = child.tagName.toUpperCase();
          if (!allowedTags.has(tag)) {
            const fragment = doc.createDocumentFragment();
            while (child.firstChild) fragment.appendChild(child.firstChild);
            child.replaceWith(fragment);
            clean(node);
            continue;
          }
          Array.from(child.attributes).forEach((attr) => {
            const attrName = attr.name.toLowerCase();
            const allowSet = allowedAttrs[tag] || new Set();
            if (!allowSet.has(attr.name) && !allowSet.has(attrName)) child.removeAttribute(attr.name);
          });
          if (tag === 'A') {
            const href = child.getAttribute('href') || '';
            if (!isSafeHref(href)) child.removeAttribute('href');
            if (child.getAttribute('target') === '_blank') child.setAttribute('rel', 'noopener noreferrer');
          }
          clean(child);
        }
      }

      clean(root);
      return root.innerHTML;
    }

    function renderRich(html) {
      return `<div class="rich">${sanitizeRichText(html || '')}</div>`;
    }

    function escapeAttr(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }

    function cssEscape(value) {
      const input = String(value ?? '');
      if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') return CSS.escape(input);
      return input.replace(/[\0-\x1F\x7F]|^-?\d|^-$|[^\w-]/g, (token) => {
        if (token === '\0') return '\uFFFD';
        return `\\${token.codePointAt(0).toString(16)} `;
      });
    }

    function selectorAttr(attrName, value) {
      return `[${attrName}="${cssEscape(value)}"]`;
    }

    function dataSelector(name, value) {
      return selectorAttr(`data-${name}`, value);
    }

    function safeJsonAttr(value) {
      return escapeAttr(JSON.stringify(value || {}));
    }

    function isDataUrl(value) {
      return typeof value === 'string' && value.startsWith('data:');
    }

    function isSafeMediaUrl(value) {
      return typeof value === 'string' && /^(https?:\/\/|data:(image|audio|video)\/)/i.test(value);
    }

    function isSafeRedirectUrl(value) {
      return typeof value === 'string' && /^(https?:\/\/|\/|\.\/|\.\.\/|#)/i.test(value.trim());
    }

    function normalizePostSubmitAction(postSubmit) {
      if (!postSubmit || typeof postSubmit !== 'object') return null;
      if (postSubmit.type !== 'redirect' || !isSafeRedirectUrl(postSubmit.url || '')) return null;
      const mode = postSubmit.mode === 'delay' ? 'delay' : 'immediate';
      const delayValue = Number(postSubmit.delayMs);
      const delayMs = mode === 'delay' && Number.isFinite(delayValue) && delayValue >= 0 ? delayValue : 3000;
      const openIn = postSubmit.openIn === 'blank' ? 'blank' : 'self';
      return {
        type: 'redirect',
        url: String(postSubmit.url).trim(),
        mode,
        delayMs,
        openIn
      };
    }

    function finishSubmitButtonLabel(finish) {
      const action = normalizePostSubmitAction(finish?.postSubmit);
      if (!action) return '确认并提交';
      return action.mode === 'delay' ? '提交并进入下一步' : '提交并前往';
    }

    function finishSubmitNote(finish) {
      const action = normalizePostSubmitAction(finish?.postSubmit);
      if (!action) return '提交后将立即完成本次问卷，页面不会再要求额外填写内容。';
      if (action.mode === 'delay') {
        const seconds = Math.max(1, Math.ceil(action.delayMs / 1000));
        return `提交成功后将展示结束提示，并在 ${seconds} 秒后跳转至下一步。`;
      }
      return '提交成功后将立即跳转至下一步页面。';
    }

    function formatResumeTime(isoString) {
      if (!isoString) return '';
      const value = new Date(isoString);
      if (Number.isNaN(value.getTime())) return '';
      try {
        return new Intl.DateTimeFormat('zh-CN', {
          month: 'numeric',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        }).format(value);
      } catch {
        return value.toLocaleString();
      }
    }

    function mediaTitle(type) {
      const map = {
        image: '图片素材',
        audio: '音频素材',
        video: '视频素材',
      };
      return map[type] || '媒体素材';
    }

    function renderMediaLink(url, text = '查看原始资源') {
      if (!url || isDataUrl(url) || !isSafeMediaUrl(url)) return '';
      return `<a class="media-link" href="${escapeAttr(url)}" target="_blank" rel="noopener noreferrer">${escapeAttr(text)}</a>`;
    }

    function renderMediaSourceAttr(url, attrName = 'src') {
      return isSafeMediaUrl(url) ? ` ${attrName}="${escapeAttr(url)}"` : '';
    }

    function renderMediaItem(m, context = 'question') {
      const label = `<small>${mediaTitle(m.type)}</small>`;
      const variantClass = context ? `media-card--${escapeAttr(context)}` : '';
      if (!isSafeMediaUrl(m?.url)) {
        return `<div class="media-card ${variantClass}">${label}<div class="media-fallback">资源地址不安全或格式不合法，已跳过内嵌预览。</div></div>`;
      }
      if (m.type === 'image') {
        return `<div class="media-card ${variantClass}">${label}<div class="media-frame media-frame--image"><img${renderMediaSourceAttr(m.url)} alt="问卷图片资源" /></div>${renderMediaLink(m.url, '打开原图')}</div>`;
      }
      if (m.type === 'audio') {
        return `<div class="media-card ${variantClass}">${label}<div class="media-frame media-frame--audio"><audio controls preload="metadata"${renderMediaSourceAttr(m.url)}></audio></div><div class="media-fallback">可直接播放音频内容。</div>${renderMediaLink(m.url)}</div>`;
      }
      if (m.type === 'video') {
        return `<div class="media-card ${variantClass}">${label}<div class="media-frame media-frame--video"><video controls preload="metadata" playsinline${renderMediaSourceAttr(m.url)}></video></div><div class="media-fallback">可直接播放视频内容。</div>${renderMediaLink(m.url)}</div>`;
      }
      return `<div class="media-card ${variantClass}">${label}<div class="media-fallback">当前资源类型暂不支持内嵌预览，请打开原始资源查看。</div>${renderMediaLink(m.url)}</div>`;
    }

    function renderMedia(media = [], context = 'question') {
      if (!media.length) return '';
      const containerClass = context === 'survey'
        ? 'hero-media-wrap'
        : context === 'finish'
        ? 'finish-media-wrap'
        : context === 'option'
        ? 'option-media-wrap'
        : 'question-media-wrap';
      return `<div class="${containerClass}"><div class="media-stack media-stack--${context}">${media.map((m) => renderMediaItem(m, context)).join('')}</div></div>`;
    }

    function renderHeroVisual(media = [], context = 'survey') {
      if (Array.isArray(media) && media.length) return renderMedia(media, context);
      return '';
    }

    function createInputControl(dataType, attrs, name = '', dataOptionId = '', dataChildId = '') {
      const placeholder = escapeAttr(attrs?.placeholder || '');
      const maxLength = escapeAttr(attrs?.maxLength ?? '');
      const safeName = escapeAttr(name);
      const safeOptionId = escapeAttr(dataOptionId);
      const safeChildId = escapeAttr(dataChildId);
      const dt = dataType || 'text';
      if (dt === 'text' && Number(attrs?.maxLength || 0) > 100) {
        return `<textarea class="textarea" ${safeName ? `name="${safeName}"` : ''} ${safeOptionId ? `data-option-id="${safeOptionId}"` : ''} ${safeChildId ? `data-child-id="${safeChildId}"` : ''} data-input-attribute='${safeJsonAttr(attrs)}' placeholder="${placeholder}" maxlength="${maxLength}"></textarea>`;
      }
      if (dt === 'dateRange' || dt === 'timeRange' || dt === 'dateTimeRange') {
        const type = dt === 'dateRange' ? 'date' : dt === 'timeRange' ? 'time' : 'datetime-local';
        const startName = name ? escapeAttr(`${name}__start`) : '';
        const endName = name ? escapeAttr(`${name}__end`) : '';
        return `<div class="field-row" data-range-type="${escapeAttr(dt)}" ${safeOptionId ? `data-option-id="${safeOptionId}"` : ''} ${safeChildId ? `data-child-id="${safeChildId}"` : ''} data-input-attribute='${safeJsonAttr(attrs)}'><input class="input" type="${type}" ${startName ? `name="${startName}"` : ''} data-range-role="start" /><input class="input" type="${type}" ${endName ? `name="${endName}"` : ''} data-range-role="end" /></div>`;
      }
      const typeMap = { text: 'text', email: 'email', tel: 'tel', number: 'number', date: 'date', time: 'time', dateTime: 'datetime-local' };
      const htmlType = typeMap[dt] || 'text';
      return `<input class="input" type="${htmlType}" ${safeName ? `name="${safeName}"` : ''} ${safeOptionId ? `data-option-id="${safeOptionId}"` : ''} ${safeChildId ? `data-child-id="${safeChildId}"` : ''} data-input-attribute='${safeJsonAttr(attrs)}' placeholder="${placeholder}" maxlength="${maxLength}" />`;
    }

    function scoreValues(option) {
      const attr = option.attribute || {};
      const scope = Array.isArray(attr.scope) && attr.scope.length === 2 ? attr.scope : [1, 5];
      const step = attr.step === 0.5 ? 0.5 : 1;
      const values = [];
      let cur = Number(scope[0]);
      const max = Number(scope[1]);
      while (cur <= max + 1e-9) {
        values.push(Number(cur.toFixed(1)));
        cur += step;
      }
      return values;
    }

    function formatScoreValue(value) {
      return Number(value) % 1 === 0 ? String(Number(value).toFixed(0)) : String(Number(value).toFixed(1));
    }
