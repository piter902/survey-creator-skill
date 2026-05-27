# Child input rules

## Scope
This document explains child inputs attached to selection options.

Typical location:
- `radio.option[].child[]`
- `checkbox.option[].child[]`

## Core meaning
If an option contains `child`, selecting that option should insert follow-up fill-in field(s) after the option.

## Cardinality
- `child` may contain one item
- `child` may contain multiple items

So the renderer must not assume there is only one child field.

## Child field model
A child node is still an input-like node.
So when a child includes its own `attribute`, that attribute should be interpreted using the same input-oriented configuration semantics already defined by the provided schema materials.

This means child attributes may include the same kinds of behavior you already provided for input-style fields, such as:
- required
- placeholder
- maxLength
- minLength
- dataType
- and other input-related constraints present in the supplied configuration

## `dataType` rule
Each child input should be rendered according to its own `attribute.dataType` when present.

Allowed values:
- `email`
- `tel`
- `number`
- `text`
- `date`
- `time`
- `dateTime`
- `dateRange`
- `timeRange`
- `dateTimeRange`

Default guidance:
- `text` → text input or textarea depending on prompt intent / length expectation
- `email` → email input
- `tel` → telephone input
- `number` → numeric input
- `date` → date input
- `time` → time input
- `dateTime` → datetime-local input
- `dateRange` → two coordinated date inputs or a range-style date UI
- `timeRange` → two coordinated time inputs or a range-style time UI
- `dateTimeRange` → two coordinated datetime-local inputs or a range-style datetime UI
- unknown or omitted → fall back to text input

If multiple child items exist, render them in order.

## Rendering rule
- render child inputs only when the related option is selected
- if the option has multiple child items, render all of them in order
- if a child has its own `attribute`, use it to drive rendering and validation
- preserve every child id for submission payload assembly

## Submission rule
When the respondent selects an option with child input:
- serialize child answers as a list, not a single scalar assumption
- include child data only for child fields that should actually be serialized
- respect child-level attribute constraints before allowing final submit
- for scalar-like child data types (`text`, `email`, `tel`, `number`, `date`, `time`, `dateTime`), serialize `value` as a string
- for range-like child data types (`dateRange`, `timeRange`, `dateTimeRange`), serialize `value` as:

{
  "start": "...",
  "end": "..."
}
