import os
import subprocess
import json
import re
from datetime import datetime, timedelta # For 'since' parameter in GitHub tools

# --- Configuration ---
MEMORY_BANK_DIR = "memory-bank"
CORE_MEMORY_FILES = [
    "projectbrief.md",
    "productContext.md",
    "activeContext.md",
    "systemPatterns.md",
    "techContext.md",
    "progress.md",
    "projectIntelligence.md",
    "roadmap.md", # New
    "tasks.md",   # New
]

# State management for Plan/Act mode
current_mode = "PLAN" # Start in Plan mode

# --- Helper Functions ---

def read_file_content(filepath):
    """Reads content of a single file."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def get_all_memory_bank_content():
    """Reads all core memory bank files and returns their combined content."""
    full_context_blocks = []
    for filename in CORE_MEMORY_FILES:
        filepath = os.path.join(MEMORY_BANK_DIR, filename)
        content = read_file_content(filepath)
        if content is not None:
            full_context_blocks.append(f"## Memory Bank File: {filename}\n```markdown\n{content.strip()}\n```\n")
        else:
            full_context_blocks.append(f"## Memory Bank File: {filename}\n```markdown\n(File not found - please create)\n```\n")
    return "\n---\n".join(full_context_blocks)

def call_gemini(prompt_text):
    """Calls the Gemini CLI with the given prompt and returns the output."""
    print("\n[DEBUG] Sending prompt to Gemini (first 500 chars):", prompt_text[:500], file=sys.stderr)
    command = ["gemini", "pro", "-p", prompt_text]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=600) # Increased timeout to 10 min
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Gemini CLI failed: {e}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        return f"ERROR: Gemini CLI failed: {e.stderr}"
    except FileNotFoundError:
        print("ERROR: 'gemini' command not found. Make sure Gemini CLI is installed and in your PATH.", file=sys.stderr)
        return "ERROR: Gemini CLI not found."
    except subprocess.TimeoutExpired:
        print("ERROR: Gemini CLI call timed out.", file=sys.stderr)
        return "ERROR: Gemini CLI call timed out."

def process_gemini_response_with_tools(gemini_output):
    """
    Displays Gemini's response. With MCP, Gemini handles tool calls internally.
    This function primarily cleans up the output if Gemini includes tool call syntax
    in its final response (though it ideally shouldn't if the tool call was successful).
    """
    print("\n--- Gemini's Response to your Task ---")
    # In a fully integrated MCP setup, Gemini's final output should be natural language
    # that incorporates the results of tool calls.
    # We don't expect raw tool call JSON here, but if it appears, it's usually an error
    # or Gemini explicitly showing its internal thought process.
    
    # Simple cleanup for any stray tool call patterns if Gemini echoes them
    clean_output = re.sub(r"```json\s*\{.*?\"toolName\":\s*\".*?\".*?\}\s*```", "", gemini_output, flags=re.DOTALL)
    clean_output = re.sub(r"call:\w+\(.*?\)", "", clean_output) # Remove simple 'call:tool()' patterns

    print(clean_output.strip())


# --- Main Logic ---

def main():
    global current_mode 

    # Ensure memory-bank directory exists and initial files are present
    os.makedirs(MEMORY_BANK_DIR, exist_ok=True)
    for filename in CORE_MEMORY_FILES:
        filepath = os.path.join(MEMORY_BANK_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                # Provide a basic template for new files
                if filename == "projectIntelligence.md":
                    f.write(f"# Project Intelligence for {os.path.basename(os.getcwd())}\n\n"
                            f"This file captures unique patterns, preferences, and challenges specific to this project.\n\n"
                            f"## Learned Patterns:\n\n"
                            f"## User Preferences:\n\n"
                            f"## Known Issues/Challenges:\n\n"
                            f"## Tool Usage Patterns:\n\n")
                elif filename == "roadmap.md":
                    f.write(f"# Project Roadmap\n\n## High-Level Milestones:\n\n- [ ] Milestone 1: Initial Setup\n- [ ] Milestone 2: Core Feature Development\n\n")
                elif filename == "tasks.md":
                    f.write(f"# Project Tasks\n\n## Current Sprint Tasks:\n\n- [ ] Task 1: Implement basic user auth\n\n")
                else:
                    f.write(f"# {filename.replace('.md', '').replace('Context', ' Context').replace('brief', ' Brief').replace('Patterns', ' Patterns').replace('progress', 'Progress').title()}\n\n")
    
    print(f"\n--- Gemini Orchestrator (Current Mode: {current_mode}) ---")
    print("Type 'plan' to switch to Plan Mode.")
    print("Type 'act' to switch to Act Mode.")
    print("Type 'exit' to quit.")

    print("\nIMPORTANT: Ensure your 'scripts/dev_ops_mcp_server.py' is running in a separate terminal.")
    print(f"To start: `python {os.path.join('scripts', 'dev_ops_mcp_server.py')}`")
    print("Also, ensure your GITHUB_TOKEN environment variable is set in the terminal where you run the MCP server.")


    while True:
        user_query = input(f"\n[{current_mode} Mode] Your task for Gemini: ")

        if user_query.lower() == 'exit':
            break
        elif user_query.lower() == 'plan':
            current_mode = "PLAN"
            print("Switched to Plan Mode.")
            continue
        elif user_query.lower() == 'act':
            current_mode = "ACT"
            print("Switched to Act Mode. Gemini may now propose and execute file system and GitHub operations.")
            continue

        gemini_mode_instruction = f"CURRENT_MODE: {current_mode}\n\n"

        # Read all memory bank files
        memory_bank_context = get_all_memory_bank_content()

        full_gemini_prompt = (
            f"{gemini_mode_instruction}"
            f"You are an expert software engineer assistant following a strict protocol as defined in the `GEMINI.md` file."
            f"You have access to file system, GitHub, uv, and ruff tools via an MCP server. Use these tools to perform operations as needed.\n"
            f"Your current project memory bank is provided below. Use this context to inform all your responses and actions.\n"
            f"Adhere strictly to the Plan Mode and Act Mode workflows.\n"
            f"When you need to interact with the file system or GitHub, call the appropriate tool.\n"
            f"When updating memory bank files, directly call `write_file` or `append_to_file`.\n"
            f"When managing Python dependencies, call `uv_sync`, `uv_add`, or `uv_remove`.\n"
            f"When checking or formatting Python code, call `ruff_check` or `ruff_format`.\n\n"
            f"--- MEMORY BANK START ---\n"
            f"{memory_bank_context}\n"
            f"--- MEMORY BANK END ---\n\n"
            f"--- USER REQUEST ---\n"
            f"{user_query}\n"
            f"--- END USER REQUEST ---\n"
        )

        gemini_output = call_gemini(full_gemini_prompt)
        
        # The orchestrator just displays Gemini's final response.
        # The MCP server handles the actual tool calls in between.
        process_gemini_response_with_tools(gemini_output)

if __name__ == "__main__":
    main()
