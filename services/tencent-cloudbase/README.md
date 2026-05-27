# Tencent CloudBase Service

This directory is the runtime service layer for the survey suite.

It is **not** a skill.

## Purpose

Provide real online runtime capabilities for Tencent deployment:

- survey answer submission endpoint
- survey metadata registration endpoint
- answer persistence in CloudBase document database

## Current service direction

- provider: Tencent
- runtime: CloudBase Functions
- storage: CloudBase document database
- answer persistence model: store the submitted survey payload as a whole JSON document

## First-phase data model

Recommended collections:

- `surveys`
- `answers`

`answers` should store the entire validated payload JSON without flattening it into relational rows.

This keeps the first version simple and aligned with the survey payload contract.
