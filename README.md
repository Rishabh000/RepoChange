# RepoChange

An agentic "second brain" for a code repository. It organizes messy files,
records every action, tracks changes through Git, and builds a searchable
semantic index — all behind a human-approval gate that respects protected paths.

The tool lives in `repo-brain/` and manages this repository (`RepoChange`).

```
Organizer agent  →  Auditor agent  →  Memory agent
   (plan moves)      (log + git commit)   (summarize + embed)
        ↑                  ↑                    ↑
   Filesystem MCP      Git MCP             Memory MCP (ChromaDB)
```

## Architecture

- **Agents never touch the filesystem directly.** Every mutation goes
  `Agent → Filesystem MCP → move_file()`. Same for git and memory.
- **MCP servers** (`repo-brain/mcp/`): `filesystem_server.py`, `git_server.py`,
  `memory_server.py`. Each is a real FastMCP server (`python mcp/<file>.py`
  serves over stdio) and also exposes plain functions the agents import.
- **Memory** (`repo-brain/memory/vector_store.py`): ChromaDB persistent client +
  sentence-transformers embeddings (`all-MiniLM-L6-v2`), so search runs offline.
- **Agents** (`repo-brain/agents/`): `organizer.py`, `auditor.py`,
  `memory_agent.py`, `coordinator.py`. The coordinator builds a google-adk
  `SequentialAgent` (organizer → auditor → memory) and drives the pipeline.
- **CLI** (`repo-brain/cli/main.py`): Typer app, launched via `./repo-brain`.

## Setup

```bash
cd repo-brain
/opt/anaconda3/bin/python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Usage

Run from the `repo-brain/` directory:

```bash
./repo-brain scan                 # show current layout
./repo-brain organize --dry-run   # propose a plan, change nothing
./repo-brain organize             # propose → "Approve? (y/n)" → apply + commit
./repo-brain organize --auto      # apply without prompting (cron)
./repo-brain search "authentication strategy"
./repo-brain audit                # audit log + git history
./repo-brain rollback             # undo repo-brain's last commit (files kept)
./repo-brain index                # rebuild memory only
```

By default it operates on the parent repository, **RepoChange** (the real git
repo this tool lives in). Point it at any other repository with
`REPO_BRAIN_TARGET=/path/to/repo ./repo-brain scan`.

## Running inside the repository it manages

repo-brain lives *inside* RepoChange, so it must not reorganize or index itself.
The `IGNORE` policy in `config.py` excludes `repo-brain/`, `.venv/`, `README.md`,
`.gitignore`, and caches. The root `.gitignore` keeps the virtualenv, ChromaDB,
and logs out of the managed repo's git history. The result: the organizer only
touches genuine content files (`auth_notes.md`, `script.py`, `users.json`, ...),
and git commits stay clean.

## Security model

- **Dry-run + approval**: nothing moves until you approve the plan.
- **Protected paths** (`config.PROTECTED`): `.env`, `.git`, `secrets`,
  `credentials` are never moved — enforced at the Filesystem MCP boundary.
- **Ignored paths** (`config.IGNORE`): the tool's own files (`repo-brain/`,
  `.venv`, `README.md`, ...) are never moved or indexed.
- **Path confinement**: operations cannot escape the target repo.
- **Audit trail**: every action is appended to `logs/audit.jsonl` and committed.
- **Reversible**: `./repo-brain rollback` undoes the last commit, keeping files.

## Gemini (required)

repo-brain uses Gemini for file classification and summaries. Set
`GOOGLE_API_KEY` (or `GEMINI_API_KEY`) in the environment or in a `.env` file at
the repo root. The model defaults to `gemini-3.1-flash-lite`; override it with
`REPO_BRAIN_MODEL`. Commands that need the model (`organize`, `index`) fail with
a clear message if no key is configured.

## Automation

`repo-brain/cron/nightly.sh` runs the pipeline unattended. Install with
`crontab -e`:

```
0 2 * * * /Users/risha/source/RepoChange/repo-brain/cron/nightly.sh >> /tmp/repo-brain.log 2>&1
```
