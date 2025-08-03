# gemory-bank
A memory-bank for Gemini CLI integrating GitHub issues and projects

```sh
pip install uv
```
```sh
touch pyproject.toml
```
```sh
uv add ruff
```
```sh
pip install PyGithub
```

# Install Gemini CLI
npm install -g @google/gemini-cli

# Then, run the CLI from anywhere:
gemini

# Create memory-bank directory and initial files
mkdir memory-bank
touch memory-bank/projectbrief.md
touch memory-bank/productContext.md
touch memory-bank/activeContext.md
touch memory-bank/systemPatterns.md
touch memory-bank/techContext.md
touch memory-bank/progress.md
touch memory-bank/projectIntelligence.md
touch memory-bank/roadmap.md
touch memory-bank/tasks.md

# GitHub Personal Access Token (PAT) Setup
**Your MCP server needs permission to interact with GitHub.**

Generate a PAT:

Go to your GitHub profile Settings.

Navigate to Developer settings -> Personal access tokens -> Tokens (classic).

Click Generate new token.

Provide a descriptive Note (e.g., "Gemini MCP GitHub Integration").

Select the following scopes (permissions):

repo (full control of private repositories)

workflow (if you plan to interact with GitHub Actions workflows)

read:org (if dealing with organization-level projects/issues)

project (for managing Projects (V2) – crucial for project boards)

Click Generate token and copy the displayed token immediately! You will not be able to see it again.

Run this in the terminal:
```sh
export GITHUB_TOKEN="YOUR_GENERATED_PAT_HERE"
```

## Update gemini cli settings
~/.gemini/settings.json

```json
{
  "mcpServers": {
    "dev_ops": {
      "command": "python",
      "args": [
        "scripts/dev_ops_mcp_server.py"
      ],
      "env": {
        "GEMINI_MCP_BASE_PATH": "./"
      }
    }
  },
  "defaultTools": [
    "dev_ops"
  ]
}
```

## Terminal windows

### Open 2 terminal windows
Terminal 1:
export GITHUB_TOKEN="YOUR_GENERATED_PAT_HERE"
python scripts/dev_ops_mcp_server.py

Terminal 2:
python scripts/gemini_orchestrator.py

Example:
[PLAN Mode] Your task for Gemini: My project is a Python Flask API for a task management system. The first task is to set up the basic Flask app structure. Create an issue for this in my GitHub repo 'your-github-username/your-repo-name' with the title 'Initial Flask App Setup' and assign it to me.

Example 2:
[ACT Mode] Your task for Gemini: I need to add the 'requests' library to the project. Please add it using uv and then run ruff check on the entire project to ensure code quality.

Example 3:
[PLAN Mode] Your task for Gemini: update memory bank based on the current status of my GitHub Project at https://github.com/users/robandrewford/projects/1.
