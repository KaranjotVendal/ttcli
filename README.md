# ttcli

Minimal CLI for [TickTick](https://ticktick.com) task management.

## Install

```bash
uv tool install .
```

## Auth (one-time)

```bash
ttcli auth setup
# Opens browser → authorize → tokens saved to ~/.ttcli/auth.json
```

## Usage

```bash
ttcli project list
ttcli task list --project "Project name"
ttcli task create "Buy milk" --project "Daily"
ttcli task complete <task-id> --project "Work"
ttcli task update <task-id> --project "Work" --priority 3
ttcli task delete <task-id> --project "Work"
```

All commands support `--json` for machine-readable output.

## Commands

| Command | Description |
|---|---|
| `auth setup` | OAuth2 authorization |
| `auth status` | Check auth status |
| `task list` | List tasks in a project |
| `task get` | Get task details |
| `task create` | Create a task |
| `task update` | Update task fields |
| `task delete` | Delete a task |
| `task complete` | Mark task completed |
| `task filter` | Filter tasks by criteria |
| `project list` | List all projects |
| `project get` | Get project details |
| `project create` | Create a project |
| `project update` | Update project |
| `project delete` | Delete a project |
| `project data` | Get project with tasks and columns |

## Agent skill

This repo ships an agent skill at:

```text
skills/ttcli/SKILL.md
```

Agents can read it to learn the preferred `ttcli` workflows: auth expectations, when to use `--json`, project name resolution, safe task/project operations, and destructive-action guidelines.

To install the skill into a local agent environment, copy it into that agent's skills directory, for example:

```bash
mkdir -p ~/.agents/skills/ttcli
cp skills/ttcli/SKILL.md ~/.agents/skills/ttcli/SKILL.md
```

## Development

```bash
uv run ttcli --help
uv run pytest
```
