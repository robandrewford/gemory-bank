import sys
import json
import os
import io
import subprocess
from github import Github, Auth
from github.GithubException import UnknownObjectException, GithubException
from datetime import datetime

# --- Configuration ---
# Base path for file system access (for safety)
# This should be your project root or a specific subdirectory you allow access to.
BASE_PATH = os.path.abspath(os.environ.get("GEMINI_MCP_BASE_PATH", "."))

# GitHub Authentication
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("WARNING: GITHUB_TOKEN environment variable not set. GitHub tools will not function.", file=sys.stderr)
    github_client = None
else:
    try:
        auth = Auth.Token(GITHUB_TOKEN)
        github_client = Github(auth=auth)
        # Test authentication by getting the authenticated user
        github_client.get_user().login # This will raise an exception if token is bad
        print(f"GitHub client initialized successfully for user: {github_client.get_user().login}", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Failed to initialize GitHub client: {e}. Check GITHUB_TOKEN.", file=sys.stderr)
        github_client = None

# --- Tool Definitions (Schema for Gemini) ---
# These are the descriptions Gemini will see to decide which tool to call.
TOOL_DEFINITIONS = [
    # Existing File System Tools
    {
        "name": "read_file",
        "description": "Reads the content of a file from the file system. Use this to get context from code files, configuration, or any other document.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to the file to read."}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Writes or overwrites content to a specified file. Creates the file and parent directories if they don't exist. Use this for generating new code, updating configuration, or making documentation changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to the file to write."},
                "content": {"type": "string", "description": "The content to write to the file."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "append_to_file",
        "description": "Appends content to an existing file. Creates the file and parent directories if they don't exist. Use this to add content to the end of a file (e.g., adding a new function to a module).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to the file to append to."},
                "content": {"type": "string", "description": "The content to append."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_directory",
        "description": "Lists files and directories within a specified path. Can be recursive. Use this to explore the project structure, find relevant files, or list contents of directories.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to the directory to list."},
                "recursive": {"type": "boolean", "description": "Whether to list recursively (default: false).", "default": False}
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_directory",
        "description": "Creates a new directory. Creates parent directories if they don't exist. Use this to organize files by creating new folders.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path of the directory to create."}
            },
            "required": ["path"]
        }
    },
    # New GitHub Issues Tools
    {
        "name": "github_create_issue",
        "description": "Creates a new GitHub issue in a specified repository. Provide the full repository name (e.g., 'owner/repo-name').",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_full_name": {"type": "string", "description": "Full name of the repository (e.g., 'owner/repo-name')."},
                "title": {"type": "string", "description": "Title of the issue."},
                "body": {"type": "string", "description": "Description of the issue.", "default": ""},
                "labels": {"type": "array", "items": {"type": "string"}, "description": "List of labels to apply.", "default": []},
                "assignees": {"type": "array", "items": {"type": "string"}, "description": "List of usernames to assign.", "default": []},
                "milestone_number": {"type": "integer", "description": "Milestone number to associate with (optional).", "default": None}
            },
            "required": ["repo_full_name", "title"]
        }
    },
    {
        "name": "github_get_issue",
        "description": "Retrieves details of a GitHub issue from a specified repository. Provide the full repository name and issue number.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_full_name": {"type": "string", "description": "Full name of the repository (e.g., 'owner/repo-name')."},
                "issue_number": {"type": "integer", "description": "The issue number."}
            },
            "required": ["repo_full_name", "issue_number"]
        }
    },
    {
        "name": "github_update_issue",
        "description": "Updates an existing GitHub issue. Provide the full repository name and issue number. You can update title, body, state ('open' or 'closed'), labels (replaces all), assignees (replaces all), or milestone.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_full_name": {"type": "string", "description": "Full name of the repository (e.g., 'owner/repo-name')."},
                "issue_number": {"type": "integer", "description": "The issue number."},
                "title": {"type": "string", "description": "New title for the issue (optional).", "default": None},
                "body": {"type": "string", "description": "New body for the issue (optional).", "default": None},
                "state": {"type": "string", "enum": ["open", "closed"], "description": "State of the issue ('open' or 'closed').", "default": None},
                "labels": {"type": "array", "items": {"type": "string"}, "description": "List of labels to replace existing ones. Provide empty list to clear all labels.", "default": None},
                "assignees": {"type": "array", "items": {"type": "string"}, "description": "List of usernames to set as assignees. Provide empty list to clear all assignees.", "default": None},
                "milestone_number": {"type": "integer", "description": "New milestone number to associate with. Set to -1 to clear milestone.", "default": None}
            },
            "required": ["repo_full_name", "issue_number"]
        }
    },
    {
        "name": "github_list_issues",
        "description": "Lists GitHub issues in a specified repository, with optional filters (state, labels, assignee, milestone, sort, direction, since).",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_full_name": {"type": "string", "description": "Full name of the repository (e.g., 'owner/repo-name')."},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Filter by issue state.", "default": "open"},
                "labels": {"type": "array", "items": {"type": "string"}, "description": "Filter by labels (e.g., ['bug', 'feature']).", "default": []},
                "assignee": {"type": "string", "description": "Filter by assignee username. Use 'none' for unassigned issues.", "default": None},
                "milestone_number": {"type": "integer", "description": "Filter by milestone number.", "default": None},
                "sort": {"type": "string", "enum": ["created", "updated", "comments"], "description": "Sort order.", "default": "created"},
                "direction": {"type": "string", "enum": ["asc", "desc"], "description": "Sort direction.", "default": "desc"},
                "since": {"type": "string", "description": "Only issues updated at or after this time (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ).", "default": None}
            },
            "required": ["repo_full_name"]
        }
    },
    # GitHub Projects (V2) Tools
    {
        "name": "github_create_project_item",
        "description": "Creates a new item (issue, pull request, or draft issue) in a GitHub Project (V2). Provide the full project URL (e.g., 'https://github.com/orgs/my-org/projects/1'). If linking an existing issue/PR, provide its Node ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_url": {"type": "string", "description": "The URL of the Project (V2) e.g. 'https://github.com/orgs/my-org/projects/1' or 'https://github.com/users/my-user/projects/1'"},
                "title": {"type": "string", "description": "Title of the draft issue or issue/PR to link. Required if issue_id is not provided."},
                "body": {"type": "string", "description": "Body of the draft issue or issue/PR to link (optional).", "default": ""},
                "issue_id": {"type": "string", "description": "Node ID of an existing issue or pull request to link. If provided, title/body are ignored.", "default": None}
            },
            "required": ["project_url"] # Title is conditionally required
        }
    },
    {
        "name": "github_get_project_items",
        "description": "Retrieves items (issues, pull requests, draft issues) from a GitHub Project (V2). Provide the full project URL. Can filter by state (OPEN or CLOSED).",
        "parameters": {
            "type": "object",
            "properties": {
                "project_url": {"type": "string", "description": "The URL of the Project (V2)."},
                "state": {"type": "string", "enum": ["OPEN", "CLOSED"], "description": "Filter by item state (OPEN or CLOSED).", "default": "OPEN"}
            },
            "required": ["project_url"]
        }
    },
    {
        "name": "github_update_project_item_field",
        "description": "Updates a specific field of an item in a GitHub Project (V2). Provide project URL, item Node ID, field name, and the new value. For single-select fields, provide the exact option name or its Node ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_url": {"type": "string", "description": "The URL of the Project (V2)."},
                "item_id": {"type": "string", "description": "The Node ID of the project item."},
                "field_name": {"type": "string", "description": "The name of the field to update (e.g., 'Status', 'Priority')."},
                "new_value": {"type": "string", "description": "The new value for the field. For single-select fields, this must be the exact option name.", "default": None},
                "new_value_id": {"type": "string", "description": "The Node ID of the new value for single-select or iteration fields (optional, used if value name is ambiguous or for direct ID setting).", "default": None}
            },
            "required": ["project_url", "item_id", "field_name"]
        }
    },
    {
        "name": "github_delete_project_item",
        "description": "Deletes an item from a GitHub Project (V2). Note: This only removes the item from the project board; it DOES NOT delete the linked issue or pull request.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_url": {"type": "string", "description": "The URL of the Project (V2)."},
                "item_id": {"type": "string", "description": "The Node ID of the project item to delete."}
            },
            "required": ["project_url", "item_id"]
        }
    },
    # New uv and ruff Tools
    {
        "name": "uv_sync",
        "description": "Synchronizes Python dependencies based on pyproject.toml or requirements.txt. Runs 'uv sync'.",
        "parameters": {"type": "object", "properties": {}} # No parameters
    },
    {
        "name": "uv_add",
        "description": "Adds a new Python package to pyproject.toml and installs it. Runs 'uv add <package_name>'.",
        "parameters": {
            "type": "object",
            "properties": {
                "package_name": {"type": "string", "description": "The name of the package to add (e.g., 'requests', 'numpy==1.23.0')."}
            },
            "required": ["package_name"]
        }
    },
    {
        "name": "uv_remove",
        "description": "Removes a Python package from pyproject.toml and uninstalls it. Runs 'uv remove <package_name>'.",
        "parameters": {
            "type": "object",
            "properties": {
                "package_name": {"type": "string", "description": "The name of the package to remove."}
            },
            "required": ["package_name"]
        }
    },
    {
        "name": "ruff_check",
        "description": "Runs linting checks on Python files using Ruff. Runs 'ruff check <path>'.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to check (e.g., '.', 'src/').", "default": "."},
                "fix": {"type": "boolean", "description": "Attempt to automatically fix linting issues (runs 'ruff check --fix').", "default": False}
            },
            "required": []
        }
    },
    {
        "name": "ruff_format",
        "description": "Formats Python code using Ruff. Runs 'ruff format <path>'.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to format (e.g., '.', 'src/').", "default": "."}
            },
            "required": []
        }
    }
]

# --- File System Operations (Implementations) ---
def get_safe_path(requested_path):
    absolute_path = os.path.abspath(os.path.join(BASE_PATH, requested_path))
    if not absolute_path.startswith(BASE_PATH):
        raise ValueError(f"Access denied: Path '{requested_path}' is outside the allowed base directory.")
    return absolute_path

def _read_file(path: str) -> str:
    safe_path = get_safe_path(path)
    if not os.path.isfile(safe_path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(safe_path, 'r', encoding='utf-8') as f:
        return f.read()

def _write_file(path: str, content: str) -> str:
    safe_path = get_safe_path(path)
    os.makedirs(os.path.dirname(safe_path), exist_ok=True)
    with open(safe_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"File '{path}' written successfully."

def _append_to_file(path: str, content: str) -> str:
    safe_path = get_safe_path(path)
    os.makedirs(os.path.dirname(safe_path), exist_ok=True)
    with open(safe_path, 'a', encoding='utf-8') as f:
        f.write(content)
    return f"Content appended to file '{path}' successfully."

def _list_directory(path: str, recursive: bool = False) -> str:
    safe_path = get_safe_path(path)
    if not os.path.isdir(safe_path):
        raise NotADirectoryError(f"Directory not found: {path}")
    output = io.StringIO()
    if recursive:
        for root, dirs, files in os.walk(safe_path):
            level = root.replace(safe_path, '').count(os.sep)
            indent = ' ' * 4 * (level)
            output.write(f"{indent}{os.path.basename(root)}/\n")
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                output.write(f"{sub_indent}{f}\n")
    else:
        for entry in os.listdir(safe_path):
            full_path = os.path.join(safe_path, entry)
            if os.path.isdir(full_path):
                output.write(f"{entry}/\n")
            else:
                output.write(f"{entry}\n")
    return output.getvalue().strip()

def _create_directory(path: str) -> str:
    safe_path = get_safe_path(path)
    os.makedirs(safe_path, exist_ok=True)
    return f"Directory '{path}' created successfully."

# --- GitHub Tool Implementations ---
def _get_repo(repo_full_name):
    if not github_client:
        raise Exception("GitHub client not initialized. GITHUB_TOKEN is missing or invalid.")
    try:
        return github_client.get_repo(repo_full_name)
    except UnknownObjectException:
        raise ValueError(f"Repository '{repo_full_name}' not found or access denied. Check repo name and token permissions.")
    except GithubException as e:
        raise Exception(f"GitHub API error getting repo: {e.status} - {e.data.get('message', 'No message')}")

def _github_create_issue(repo_full_name: str, title: str, body: str = "", labels: list = [], assignees: list = [], milestone_number: int = None) -> str:
    repo = _get_repo(repo_full_name)
    milestone = None
    if milestone_number:
        try:
            milestone = repo.get_milestone(milestone_number)
        except UnknownObjectException:
            raise ValueError(f"Milestone number {milestone_number} not found in repository '{repo_full_name}'.")

    try:
        issue = repo.create_issue(
            title=title,
            body=body,
            labels=labels,
            assignees=assignees if assignees else Github.NO_ASSIGNEES,
            milestone=milestone
        )
        return json.dumps({
            "success": True,
            "message": f"Issue '{issue.title}' created successfully.",
            "issue_number": issue.number,
            "issue_url": issue.html_url
        })
    except GithubException as e:
        raise Exception(f"GitHub API error creating issue: {e.status} - {e.data.get('message', 'No message')}")

def _github_get_issue(repo_full_name: str, issue_number: int) -> str:
    repo = _get_repo(repo_full_name)
    try:
        issue = repo.get_issue(issue_number)
        return json.dumps({
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "state": issue.state,
            "url": issue.html_url,
            "labels": [label.name for label in issue.labels],
            "assignees": [assignee.login for assignee in issue.assignees],
            "milestone": issue.milestone.title if issue.milestone else None,
            "created_at": issue.created_at.isoformat(),
            "updated_at": issue.updated_at.isoformat(),
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None
        })
    except UnknownObjectException:
        raise ValueError(f"Issue #{issue_number} not found in repository '{repo_full_name}'.")
    except GithubException as e:
        raise Exception(f"GitHub API error getting issue: {e.status} - {e.data.get('message', 'No message')}")

def _github_update_issue(repo_full_name: str, issue_number: int, title: str = None, body: str = None, state: str = None, labels: list = None, assignees: list = None, milestone_number: int = None) -> str:
    repo = _get_repo(repo_full_name)
    try:
        issue = repo.get_issue(issue_number)
        
        update_params = {}
        if title is not None: update_params['title'] = title
        if body is not None: update_params['body'] = body
        if state is not None: update_params['state'] = state
        
        if labels is not None: 
            issue.set_labels(*labels) 
        
        if assignees is not None:
            current_assignees = [a.login for a in issue.assignees]
            to_add = [a for a in assignees if a not in current_assignees]
            to_remove = [a for a in current_assignees if a not in assignees]
            
            if to_add: issue.add_to_assignees(*to_add)
            if to_remove: issue.remove_from_assignees(*to_remove)
            
            if not assignees and current_assignees:
                issue.remove_from_assignees(*current_assignees)

        if milestone_number is not None:
            milestone = None
            if milestone_number != -1: 
                try:
                    milestone = repo.get_milestone(milestone_number)
                except UnknownObjectException:
                    raise ValueError(f"Milestone number {milestone_number} not found in repository '{repo_full_name}'.")
            update_params['milestone'] = milestone
        
        if update_params:
            issue.edit(**update_params)
        
        return json.dumps({
            "success": True,
            "message": f"Issue #{issue_number} updated successfully.",
            "issue_url": issue.html_url
        })
    except UnknownObjectException:
        raise ValueError(f"Issue #{issue_number} not found in repository '{repo_full_name}'.")
    except GithubException as e:
        raise Exception(f"GitHub API error updating issue: {e.status} - {e.data.get('message', 'No message')}")

def _github_list_issues(repo_full_name: str, state: str = "open", labels: list = [], assignee: str = None, milestone_number: int = None, sort: str = "created", direction: str = "desc", since: str = None) -> str:
    repo = _get_repo(repo_full_name)
    issues_list = []
    
    params = {
        "state": state,
        "labels": labels,
        "assignee": assignee if assignee != "none" else Github.NO_ASSIGNEES,
        "sort": sort,
        "direction": direction
    }
    if milestone_number is not None:
        try:
            params["milestone"] = repo.get_milestone(milestone_number)
        except UnknownObjectException:
            raise ValueError(f"Milestone number {milestone_number} not found in repository '{repo_full_name}'.")
    if since:
        try:
            params["since"] = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Invalid 'since' date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SSZ).")

    try:
        for issue in repo.get_issues(**params):
            issues_list.append({
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "url": issue.html_url,
                "labels": [label.name for label in issue.labels],
                "assignees": [assignee.login for assignee in issue.assignees],
                "milestone": issue.milestone.title if issue.milestone else None,
                "created_at": issue.created_at.isoformat(),
                "updated_at": issue.updated_at.isoformat()
            })
        return json.dumps(issues_list, indent=2)
    except UnknownObjectException:
        raise ValueError(f"Repository '{repo_full_name}' not found or access denied.")
    except GithubException as e:
        raise Exception(f"GitHub API error listing issues: {e.status} - {e.data.get('message', 'No message')}")

def _get_project_id_from_url(project_url: str):
    parts = project_url.strip('/').split('/')
    if "users" in parts:
        user_or_org_type = "user"
        owner_login = parts[parts.index("users") + 1]
        project_number = int(parts[parts.index("projects") + 1])
    elif "orgs" in parts:
        user_or_org_type = "organization"
        owner_login = parts[parts.index("orgs") + 1]
        project_number = int(parts[parts.index("projects") + 1])
    else:
        raise ValueError(f"Invalid GitHub Project URL format: {project_url}. Must be for a user or organization project (e.g., 'https://github.com/orgs/my-org/projects/1').")
    return user_or_org_type, owner_login, project_number

def _graphql_query(query, variables=None):
    if not github_client:
        raise Exception("GitHub client not initialized. GITHUB_TOKEN is missing or invalid.")
    try:
        return github_client.post_graphql(query, variables)
    except GithubException as e:
        errors = e.data.get('errors', [])
        error_messages = [err.get('message', 'Unknown error') for err in errors]
        raise Exception(f"GitHub GraphQL API error: {e.status} - {'; '.join(error_messages)}")

def _get_project_node_id(project_url: str):
    owner_type, owner_login, project_number = _get_project_id_from_url(project_url)
    
    query_template = """
        query($login: String!, $number: Int!) {
            %s(login: $login) {
                projectV2(number: $number) {
                    id
                }
            }
        }
    """
    query = query_template % owner_type
    variables = {"login": owner_login, "number": project_number}
    data = _graphql_query(query, variables)
    
    project_id = data.get(owner_type, {}).get('projectV2', {}).get('id')
    
    if not project_id:
        raise ValueError(f"Could not find project Node ID for {project_url}. Check URL, project number, and token permissions (requires 'project' scope).")
    return project_id

def _get_project_field_id_and_options(project_node_id: str, field_name: str):
    query = """
        query($project_id: ID!) {
            node(id: $project_id) {
                ... on ProjectV2 {
                    fields(first: 100) {
                        nodes {
                            ... on ProjectV2Field {
                                id
                                name
                            }
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                                options {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    variables = {"project_id": project_node_id}
    data = _graphql_query(query, variables)
    
    fields = data['node']['fields']['nodes']
    
    target_field = None
    for field in fields:
        if field['name'].lower() == field_name.lower():
            target_field = field
            break
    
    if not target_field:
        raise ValueError(f"Field '{field_name}' not found in project '{project_node_id}'.")
    
    field_id = target_field['id']
    options = {option['name'].lower(): option['id'] for option in target_field.get('options', [])}
    
    return field_id, options

def _github_create_project_item(project_url: str, title: str = None, body: str = "", issue_id: str = None) -> str:
    project_node_id = _get_project_node_id(project_url)
    
    if issue_id:
        mutation = """
            mutation($projectId: ID!, $contentId: ID!) {
                addProjectV2Item(input: {projectId: $projectId, contentId: $contentId}) {
                    item {
                        id
                    }
                }
            }
        """
        if not issue_id.startswith("I_") and not issue_id.startswith("PR_"):
             raise ValueError(f"Invalid issue_id '{issue_id}'. It must be a Node ID (e.g., 'I_kwDOB000...').")
        variables = {"projectId": project_node_id, "contentId": issue_id}
        message = "Linked existing issue/PR to project."
    else:
        if not title:
            raise ValueError("Title is required for creating a new draft issue.")
        mutation = """
            mutation($projectId: ID!, $title: String!, $body: String!) {
                addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
                    projectV2Item {
                        id
                    }
                }
            }
        """
        variables = {"projectId": project_node_id, "title": title, "body": body}
        message = "Created new draft issue in project."
    
    data = _graphql_query(mutation, variables)
    item_id = data.get('addProjectV2Item', {}).get('item', {}).get('id') or \
              data.get('addProjectV2DraftIssue', {}).get('projectV2Item', {}).get('id')

    if not item_id:
        raise Exception("Failed to create/link project item. Check input and permissions.")

    return json.dumps({"success": True, "message": message, "item_id": item_id})

def _github_get_project_items(project_url: str, state: str = "OPEN") -> str:
    project_node_id = _get_project_node_id(project_url)
    
    query = """
        query($projectId: ID!, $first: Int!, $after: String) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: $first, after: $after) {
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                        nodes {
                            id
                            type
                            fieldValues(first: 10) {
                                nodes {
                                    ... on ProjectV2ItemFieldTextValue { field { name } text }
                                    ... on ProjectV2ItemFieldDateValue { field { name } date }
                                    ... on ProjectV2ItemFieldSingleSelectValue { field { name } name }
                                }
                            }
                            content {
                                ... on Issue { number title body state url labels(first: 5) { nodes { name } } assignees(first: 5) { nodes { login } } milestone { title } createdAt updatedAt closedAt }
                                ... on PullRequest { number title url state createdAt updatedAt closedAt mergedAt }
                            }
                        }
                    }
                }
            }
        }
    """
    
    items = []
    has_next_page = True
    end_cursor = None
    
    while has_next_page:
        variables = {"projectId": project_node_id, "first": 50, "after": end_cursor}
        data = _graphql_query(query, variables)
        project_data = data['node']['items']
        
        for item_node in project_data['nodes']:
            item_info = {
                "id": item_node['id'],
                "type": item_node['type'],
                "fields": {}
            }
            
            if item_node.get('fieldValues') and item_node['fieldValues'].get('nodes'):
                for fv in item_node['fieldValues']['nodes']:
                    field_name = fv['field']['name']
                    if 'text' in fv: item_info['fields'][field_name] = fv['text']
                    elif 'date' in fv: item_info['fields'][field_name] = fv['date']
                    elif 'name' in fv: item_info['fields'][field_name] = fv['name']
            
            if item_node['content']:
                content = item_node['content']
                item_info.update({
                    "content_number": content.get('number'),
                    "content_title": content.get('title'),
                    "content_state": content.get('state'),
                    "content_url": content.get('url'),
                    "content_body": content.get('body'),
                    "content_labels": [l['name'] for l in content.get('labels', {}).get('nodes', [])] if content.get('labels') else [],
                    "content_assignees": [a['login'] for a in content.get('assignees', {}).get('nodes', [])] if content.get('assignees') else [],
                    "content_milestone": content.get('milestone', {}).get('title') if content.get('milestone') else None,
                    "content_created_at": content.get('createdAt'),
                    "content_updated_at": content.get('updatedAt'),
                    "content_closed_at": content.get('closedAt'),
                    "content_merged_at": content.get('mergedAt')
                })
            
            should_add = False
            if state == "ALL":
                should_add = True
            elif item_node['type'] == "DRAFT_ISSUE" and state == "OPEN":
                should_add = True
            elif item_node['content'] and item_node['content'].get('state') == state:
                should_add = True
            
            if should_add:
                items.append(item_info)

        has_next_page = project_data['pageInfo']['hasNextPage']
        end_cursor = project_data['pageInfo']['endCursor']
        
    return json.dumps(items, indent=2)

def _github_update_project_item_field(project_url: str, item_id: str, field_name: str, new_value: str = None, new_value_id: str = None) -> str:
    project_node_id = _get_project_node_id(project_url)
    field_id, options = _get_project_field_id_and_options(project_node_id, field_name)
    
    input_value = {}
    if new_value_id:
        input_value = {"singleSelectOptionId": new_value_id}
    elif new_value is not None:
        if options:
            option_id = options.get(new_value.lower())
            if not option_id:
                raise ValueError(f"Option '{new_value}' not found for single-select field '{field_name}'. Available options: {list(options.keys())}")
            input_value = {"singleSelectOptionId": option_id}
        else:
            input_value = {"text": new_value} 
    else:
        raise ValueError("Either 'new_value' or 'new_value_id' must be provided for field update.")

    mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
            updateProjectV2ItemFieldValue(input: {
                projectId: $projectId,
                itemId: $itemId,
                fieldId: $fieldId,
                value: $value
            }) {
                projectV2Item {
                    id
                }
            }
        }
    """
    variables = {
        "projectId": project_node_id,
        "itemId": item_id,
        "fieldId": field_id,
        "value": input_value
    }
    
    _graphql_query(mutation, variables)
    return json.dumps({"success": True, "message": f"Field '{field_name}' updated for item '{item_id}' in project."})

def _github_delete_project_item(project_url: str, item_id: str) -> str:
    project_node_id = _get_project_node_id(project_url)

    mutation = """
        mutation($projectId: ID!, $itemId: ID!) {
            deleteProjectV2Item(input: {projectId: $projectId, itemId: $itemId}) {
                deletedItemId
            }
        }
    """
    variables = {"projectId": project_node_id, "itemId": item_id}
    data = _graphql_query(mutation, variables)
    deleted_id = data.get('deleteProjectV2Item', {}).get('deletedItemId')
    if not deleted_id:
        raise Exception("Failed to delete project item. Check input and permissions.")
    return json.dumps({"success": True, "message": f"Project item '{item_id}' deleted from project."})

# --- New uv and ruff Tool Implementations ---

def _run_shell_command(command_parts: list, cwd: str = None) -> str:
    """Helper to run a shell command and capture its output."""
    try:
        # Ensure the command is run from the BASE_PATH or a safe sub-path
        actual_cwd = get_safe_path(cwd if cwd else ".")
        
        process = subprocess.run(
            command_parts,
            cwd=actual_cwd,
            capture_output=True,
            text=True,
            check=True, # Raise CalledProcessError for non-zero exit codes
            shell=False # Prefer shell=False for security and clarity
        )
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: Command failed with exit code {e.returncode}.\nSTDOUT: {e.stdout.strip()}\nSTDERR: {e.stderr.strip()}"
    except FileNotFoundError:
        return f"ERROR: Command '{command_parts[0]}' not found. Make sure it's installed and in your PATH."
    except Exception as e:
        return f"ERROR: An unexpected error occurred: {str(e)}"

def _uv_sync() -> str:
    return _run_shell_command(["uv", "sync"])

def _uv_add(package_name: str) -> str:
    return _run_shell_command(["uv", "add", package_name])

def _uv_remove(package_name: str) -> str:
    return _run_shell_command(["uv", "remove", package_name])

def _ruff_check(path: str = ".", fix: bool = False) -> str:
    command = ["ruff", "check", path]
    if fix:
        command.append("--fix")
    return _run_shell_command(command)

def _ruff_format(path: str = ".") -> str:
    return _run_shell_command(["ruff", "format", path])

# --- MCP Server Logic ---

def send_response(response_data):
    """Sends a JSON response back to the client."""
    sys.stdout.write(json.dumps(response_data) + "\n")
    sys.stdout.flush()

def handle_request(request):
    """Handles an incoming MCP request."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "mcp_ping":
        send_response({"jsonrpc": "2.0", "result": "pong", "id": request_id})
    elif method == "mcp_queryTools":
        send_response({"jsonrpc": "2.0", "result": {"tools": TOOL_DEFINITIONS}, "id": request_id})
    elif method == "mcp_callTool":
        tool_name = params.get("toolName")
        tool_args = params.get("toolArgs", {})
        
        result = None
        error = None
        
        try:
            # File system tools
            if tool_name == "read_file":
                result = _read_file(**tool_args)
            elif tool_name == "write_file":
                result = _write_file(**tool_args)
            elif tool_name == "append_to_file":
                result = _append_to_file(**tool_args)
            elif tool_name == "list_directory":
                result = _list_directory(**tool_args)
            elif tool_name == "create_directory":
                result = _create_directory(**tool_args)
            # GitHub tools
            elif tool_name == "github_create_issue":
                result = _github_create_issue(**tool_args)
            elif tool_name == "github_get_issue":
                result = _github_get_issue(**tool_args)
            elif tool_name == "github_update_issue":
                result = _github_update_issue(**tool_args)
            elif tool_name == "github_list_issues":
                result = _github_list_issues(**tool_args)
            elif tool_name == "github_create_project_item":
                if not tool_args.get("issue_id") and not tool_args.get("title"):
                    raise ValueError("Either 'title' or 'issue_id' must be provided for github_create_project_item.")
                result = _github_create_project_item(**tool_args)
            elif tool_name == "github_get_project_items":
                result = _github_get_project_items(**tool_args)
            elif tool_name == "github_update_project_item_field":
                result = _github_update_project_item_field(**tool_args)
            elif tool_name == "github_delete_project_item":
                result = _github_delete_project_item(**tool_args)
            # uv and ruff tools
            elif tool_name == "uv_sync":
                result = _uv_sync()
            elif tool_name == "uv_add":
                result = _uv_add(**tool_args)
            elif tool_name == "uv_remove":
                result = _uv_remove(**tool_args)
            elif tool_name == "ruff_check":
                result = _ruff_check(**tool_args)
            elif tool_name == "ruff_format":
                result = _ruff_format(**tool_args)
            else:
                error = {"code": -32601, "message": f"Tool not found: {tool_name}"}
        except Exception as e:
            error = {"code": -32000, "message": f"Tool execution failed for {tool_name}: {type(e).__name__}: {str(e)}"}
            print(f"Server Error: {error['message']}", file=sys.stderr) 
            
        if error:
            send_response({"jsonrpc": "2.0", "error": error, "id": request_id})
        else:
            send_response({"jsonrpc": "2.0", "result": {"toolResult": result}, "id": request_id})
    else:
        send_response({"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": request_id})

def main():
    print("DevOps MCP Server started. Waiting for requests...", file=sys.stderr)
    print(f"Base path for file operations: {BASE_PATH}", file=sys.stderr)
    if not GITHUB_TOKEN:
        print("GitHub tools are disabled due to missing GITHUB_TOKEN environment variable.", file=sys.stderr)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break # EOF, client closed connection
            
            request = json.loads(line)
            handle_request(request)
        except json.JSONDecodeError:
            print("Invalid JSON received.", file=sys.stderr)
            send_response({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})
        except Exception as e:
            print(f"Unhandled server error: {e}", file=sys.stderr)
            send_response({"jsonrpc": "2.0", "error": {"code": -32000, "message": "Internal server error"}, "id": None})

if __name__ == "__main__":
    main()