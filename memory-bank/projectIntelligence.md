# Project Intelligence for [Your Project Name]

This file captures unique patterns, preferences, and challenges specific to this project.

## Learned Patterns:
- User authentication logic is complex and requires careful state management.
- Database operations are often bottlenecked by inefficient queries; prioritize ORM optimization.
- Project tasks often involve both API changes and database schema updates.

## User Preferences:
- User prefers clear, concise explanations for proposed actions.
- User values automated code quality checks (linting, formatting).
- User wants GitHub issues/projects to be kept up-to-date with memory bank.

## Known Issues/Challenges:
- Occasional `uv` cache corruption requires `uv clean` (rare).
- GitHub API rate limits can be hit during large sync operations; need to optimize calls.
- Project V2 GraphQL queries can be tricky; always double-check field names and IDs.

## Tool Usage Patterns:
- **File System:** Prefer `write_file` for creating new files or replacing entire file content. Use `append_to_file` for adding small snippets (e.g., new function to existing file).
- **GitHub Issues:**
    - When creating a new feature, first create a `roadmap.md` entry, then `tasks.md` entries, then `github_create_issue` for each task.
    - When an issue is resolved, use `github_update_issue` to set `state='closed'`.
- **GitHub Projects:**
    - Use `github_create_project_item` to add tasks from `tasks.md` to the project board.
    - Use `github_update_project_item_field` to move cards between status columns (e.g., "Todo" -> "In Progress" -> "Done").
    - Always obtain `item_id` via `github_get_project_items` before updating or deleting project items.
- **uv:** Use `uv sync` after any `git pull` that might change dependencies. Use `uv add` for new packages, `uv remove` for old ones.
- **Ruff:** Always run `ruff_check(path='.')` before proposing a commit. If errors are found, suggest `ruff_check(path='.', fix=True)` or manual correction. Run `ruff_format(path='.')` for consistent style.

## GitHub Repository Details:
- **Default Repository for Issues:** `your-github-username/your-repo-name` (Replace with actual)
- **Default Project URL:** `https://github.com/users/your-github-username/projects/1` (Replace with actual)
- **Common Labels:** `bug`, `feature`, `enhancement`, `documentation`, `high-priority`, `low-priority`
- **Common Assignees:** `your-github-username`, `team-member-1`, `team-member-2`
