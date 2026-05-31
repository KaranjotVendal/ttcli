---
name: ttcli
description: TickTick CLI for managing projects and tasks from the terminal, optimized for agent use with JSON output. Use when the user asks to view, create, update, complete, delete, or organize TickTick tasks/projects, or mentions ttcli/TickTick.
---

# TickTick CLI

Use `ttcli` to manage TickTick projects and tasks from the terminal.

## 1. Auth first

Check auth before using TickTick:

```bash
ttcli auth status
```

Tokens live in `~/.ttcli/auth.json` and refresh automatically after setup.

If auth fails, stop and ask the user to run:

```bash
ttcli auth setup
```

Do not run `auth setup` unless the user is present. It opens a browser for OAuth.

## 2. Use JSON for agent reads

Use `--json` whenever reading state that an agent will reason about:

```bash
ttcli project list --json
ttcli task list --project "Project Name" --json
```

Human output hides IDs where possible. Use `--json` when task/project IDs are needed for follow-up commands.

## 3. Project names

For task commands, prefer project names over IDs:

```bash
ttcli task list --project "EU Trip" --json
```

`--project` accepts exact project names, project IDs, or unique substring matches. Exact names win over substring matches. If matching is ambiguous, run `ttcli project list` or `ttcli project list --json`, then retry with the exact project name.

## 4. Task workflows

List tasks and get task IDs:

```bash
ttcli task list --project "Papers" --json
```

Create a task:

```bash
ttcli task create "Review paper notes" --project "Papers" --priority 3
```

Update, complete, or delete after identifying the task ID:

```bash
ttcli task update <task-id> --project "Papers" --title "New title" --priority 5
ttcli task complete <task-id> --project "Papers"
ttcli task delete <task-id> --project "Papers"
```

Confirm with the user before `task delete`.

## 5. Project workflows

List projects:

```bash
ttcli project list
ttcli project list --json
```

Use `--json` to get project IDs for project-level commands:

```bash
ttcli project get <project-id>
ttcli project data <project-id>
ttcli project update <project-id> --name "New Name"
ttcli project delete <project-id>
```

Confirm with the user before `project delete`.

## 6. Values

Priority: `0` none, `1` low, `3` medium, `5` high.

Status in JSON: `0` open/todo, `2` completed.
