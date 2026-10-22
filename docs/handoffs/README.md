# Handoff Standard

> **Internal engineering record.** Handoffs are dated working notes between
> operators and agents, not current operating truth. For the live network, read
> [Network Status](../status/network-status.md).

Use handoffs to transfer active context between operators and agents. Keep each
handoff concise, plain-English, and grounded in repository references.

## Publishing a handoff

Do not edit `mkdocs.yml` for a new handoff. After adding the file, regenerate
the newest-first [handoff index](index.md) and commit it with the handoff:

```bash
scripts/docs-handoffs-index           # rewrites docs/handoffs/index.md
scripts/docs-handoffs-index --check   # exits 1 if the index is stale
```

The docs site shows `index.md` as the Handoffs page. MkDocs does not publish
this README, because a directory's `README.md` and `index.md` would map to the
same page, so link to the standard by its GitHub URL from published pages.

## Filename

`YYYY-MM-DD___operator__simple_title.md`

- Use the UTC handoff date.
- Use a lowercase operator identifier.
- Use a short lowercase `snake_case` title.

## Required format

```markdown
# Simple title

- **Operator:** Name (`operator_id`)
- **Date:** YYYY-MM-DD UTC

## BLUF

One short paragraph stating what was worked on, the current result, and the
primary document references.

## Current state

Concise facts about completed and active work, with code or evidence links.

## Next decision or action

The decision to make or the next bounded action, including any constraints.

## References

- Documents, code, tests, and evidence needed by the next reader.
```

Do not paste logs, speculate about unverified behavior, or describe shadow and
simulation evidence as live authority. For deployment claims, link
[Current State](../status/chain-state-current.md) and distinguish all of the
following explicitly:

- last observed fleet state and capture time;
- deployed binary and source lineage;
- current repository branch and HEAD;
- merged but undeployed work;
- whether a live probe was performed in the session.

A passing offline packet verifier is not a fresh fleet probe. Dated handoffs are
historical snapshots and must link forward when a later event supersedes their
operational state.
