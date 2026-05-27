# Rich text rules

## Scope
The following fields support rich text:
- `survey.title`
- `survey.description`
- `question.title`
- `question.description`
- `option.title`
- `finish.title`
- `finish.description`

## Rich text support rule
Support only **display-oriented safe HTML elements**.

This means the renderer should assume HTML-rich content may appear, but it must be sanitized through a whitelist instead of being injected as arbitrary raw HTML.

Recommended allowed tags include:
- paragraphs
- headings
- strong / bold text
- emphasis / italic text
- links
- ordered and unordered lists
- line breaks
- inline spans
- block containers

Example whitelist:
- `div`
- `p`
- `span`
- `strong`
- `b`
- `em`
- `i`
- `u`
- `br`
- `ul`
- `ol`
- `li`
- `blockquote`
- `code`
- `pre`
- `h1`
- `h2`
- `h3`
- `h4`
- `h5`
- `h6`
- `a`

Disallowed examples:
- `script`
- `style`
- `iframe`
- `form`
- `input`
- `button`
- `textarea`
- `select`
- `video`
- `audio`
- `img`
- any inline event handler such as `onclick`

## Rendering rule
- Render these fields as HTML-capable rich text.
- Always sanitize rich text with a whitelist before rendering.
- Do not flatten them to escaped plain text unless the user explicitly asks for plain-text rendering.
- Preserve the author's structure and hierarchy when placing content into the page.
- For links, keep only safe attributes such as `href`, `target`, and `rel`, and reject dangerous protocols like `javascript:`.

## Validation implication
When validating schema semantics:
- treat rich-text fields as `string` values carrying HTML-capable content
- do not assume they must be plain labels only
- do not allow arbitrary embedded interactive or executable HTML inside rich-text fields
