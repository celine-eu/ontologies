# `.harness/` — staged agent harness for `ontologies`

**Nothing outside this directory has been modified.** These files are written as if they
were already at the repository root, so promotion is a move rather than a rewrite.

This file is the only one that mentions `.harness/`. It does not survive promotion.

## What is here

| Staged | Promotes to | What it is |
|---|---|---|
| `AGENTS.md` | `AGENTS.md` | the root guide — navigation and constraints. **Written for you to fill in** |
| `.agents/README.md` | `.agents/README.md` | the knowledge contract. Normative, and mostly ready to use |
| `.agents/harness.toml` | `.agents/harness.toml` | what this repository declares about itself to the checker |
| `.agents/playbooks/testing.md` | `.agents/playbooks/` | the first playbook, as a shape to copy |
| `docs/decisions/index.md` | `docs/decisions/` | where a technical decision goes, and what is not one |

Anything marked `<TODO: …>` is yours. The checker ignores those markers, so a half-filled
guide will pass structural checks while still being useless — read them, do not rely on a
green report to find them.

## Before you promote

1. **Snapshot anything you are about to move.** If your existing agent notes are
   gitignored, git is not a safety net for them and a move is unrecoverable.
2. **Read the publishing boundary.** If the repository is public and the notes you are
   about to commit were written in private, they have never been reviewed against it.
3. **Do not import a second traceability stack.** If this repository already answers
   "is this requirement met?" with a tool of its own, say so in `.agents/harness.toml`
   under `[traceability]` and keep that tool. The checker will report those requirements
   as `DELEGATED`, naming it.

## Promotion

```bash
mv .harness/AGENTS.md AGENTS.md          # merge by hand if one already exists
mkdir -p .agents docs
cp -r .harness/.agents/. .agents/
cp -r .harness/docs/. docs/
rm -rf .harness
```

Then add `.agents/work/` to `.gitignore` — the rest of `.agents/` is committed — and run:

```bash
python -m harness .
```

## After you promote

The structure is the cheap part. What makes it worth having is filling it from what the
repository already knows: rationale in CI comments and build files, procedures buried in
guides, invariants in code comments. The checker cannot find those for you.
