# toC survey UI rules

This file defines the default visual and structural rules for **consumer-facing survey filling pages**.

Use these rules when the user wants:
- a toC questionnaire page
- a lightweight filling experience
- a WeChat / Xiaohongshu / Meituan / consumer landing-page style survey
- a survey page that feels like a real product form rather than an AI demo page

---

## 1. Core principle

The page should feel:
- light
- trustworthy
- low-cognitive-load
- mobile-friendly
- fast to complete

The page should **not** feel like:
- an AI showcase
- a landing page hero section
- a visual experiment with strong gradients and floating effects
- a design-dribbble-style concept shot

---

## 2. Default layout model

Prefer a **single main survey container**.

Recommended structure:

1. page background
2. centered main survey card or mobile-first container
3. compact header area
4. question list / question step area
5. bottom action area

Avoid:
- nested cards inside cards unless truly needed
- multiple decorative meta panels in the header
- large split-layout hero sections
- heavy side-by-side visual compositions

---

## 3. Header rules

The header should usually contain only:
- survey title
- short description
- optional estimated duration / question count / privacy hint

Good header content:
- what this survey is for
- how long it takes
- whether answers are anonymous

Avoid putting these in the visible user-facing header:
- technical explanations
- schema/payload/contract wording
- “AI generated” explanations
- long blocks about how the page works internally

---

## 4. Visual style rules

### Default tone
Use a restrained consumer product style.

### Prefer
- light neutral background
- white or near-white content surface
- subtle border
- subtle or no shadow
- medium radius
- strong text contrast
- one clear primary accent color

### Avoid
- large gradients across the whole page
- glow effects
- glassmorphism
- oversized shadows
- oversized radii
- multiple competing accent colors

### Recommended values
- page background: `#f5f6f8` to `#f7f8fa`
- card background: `#ffffff`
- text primary: `#1f2329`
- text secondary: `#646a73`
- border: `#e5e6eb`
- radius: `12px` to `16px`
- input/button radius: `10px` to `12px`

---

## 5. Question presentation rules

Each question should be rendered in a stable, standard form structure:
- question index (optional)
- title
- short helper description (optional)
- answer area
- inline validation hint (only when needed)

Question cards should feel like product form sections, not showcase cards.

Avoid:
- extremely decorative question blocks
- heavy hover animations
- large floating option tiles unless the user explicitly asks for them

---

## 6. Option style rules

### radio / checkbox
Prefer:
- standard form-row style
- light border
- subtle selected state
- clear checked indicator

Avoid:
- oversized selection cards
- strong gradients per option
- visual styles that overpower the question title

### child inputs
- appear directly below the selected option
- remain visually attached to the option
- use simple indentation / divider spacing
- do not turn child inputs into separate hero-style modules

---

## 7. Input style rules

Inputs should feel like real toC forms:
- stable width
- standard border
- clear placeholder
- calm focus state
- simple error state

Avoid:
- high-contrast neon focus glow
- overly decorative input chrome
- deep nested framed blocks around every input

---

## 8. Score / NPS rules

These controls should be:
- easy to understand at first glance
- compact
- consistent with the rest of the form

Prefer:
- evenly sized score pills / buttons
- light selected state
- optional short textual labels

Avoid:
- making score controls look like KPI dashboards
- overdesigned badges or segmented showcases

---

## 9. Navigation and actions

Primary action area should be clear and stable.

### For multi-question pages
- place actions at the bottom of the main card
- keep the primary submit/next button visually dominant

### For one-question-per-step mode
- fixed or sticky bottom action area is acceptable
- back/next should remain predictable and lightweight

Avoid:
- too many CTA buttons
- multiple competing primary actions
- decorative button treatments that make the form feel like marketing UI

---

## 10. Generic toC skins

The renderer may apply a generic toC skin when explicitly requested.

### `consumer-minimal`
- neutral, clean, default toC style

### `consumer-polished`
- stronger hierarchy
- more refined spacing and emphasis
- slightly more premium product feel

### `consumer-trust`
- reassuring, product-safe tone
- clearer structure
- good for satisfaction and post-purchase forms

### `consumer-editorial`
- more expressive content rhythm
- softer lifestyle/product feel
- still completion-safe

### `consumer-utility`
- compact, direct, efficient
- lower decoration
- stronger scan readability

Rule:
- skin should change tokens and small visual details
- skin should **not** replace the stable survey structure

---

## 11. Mobile-first rule

Default assumption for toC surveys:
- mobile is the primary viewport

So the layout should:
- work cleanly around 375–430px widths
- avoid unnecessary horizontal composition
- keep text readable without dense blocks
- keep actions reachable near the thumb zone when possible

Desktop support should remain good, but desktop should not become the primary visual model for toC surveys.

---

## 12. Content-density rule

If the user asks for a consumer-facing survey, prefer:
- fewer visible explanatory blocks
- shorter descriptions
- stronger focus on answering

When in doubt:
- reduce decoration
- reduce explanation
- reduce number of top-level cards
- preserve only what helps completion

---

## 13. Default recommendation

If the user says only “make it more toC” and does not specify a channel:
- use `consumer-minimal`
- single survey card
- compact header
- simple option rows
- subtle borders
- mobile-first spacing
- one clear primary button
