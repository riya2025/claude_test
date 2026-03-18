"""
GitHub PR Agent - Creates GitHub pull requests using Claude Agent SDK.

This agent follows the workflow from Skills.md:
1. Check current git state
2. Analyze changes
3. Draft PR with proper format
4. Create PR using gh CLI
5. Return PR URL
"""

import subprocess
import json
import os
import re
from typing import Optional


def run_command(cmd: str, capture_output: bool = True) -> str:
    """Run a shell command and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True
    )
    if result.returncode != 0 and capture_output:
        print(f"Warning: Command '{cmd}' returned non-zero: {result.stderr}")
    return result.stdout.strip() if capture_output else ""


def get_git_status() -> dict:
    """Get current git status."""
    untracked = run_command("git status --porcelain")
    diff = run_command("git diff")
    staged = run_command("git diff --cached")
    return {
        "untracked": untracked,
        "diff": diff,
        "staged": staged
    }


def get_recent_commits(count: int = 5) -> str:
    """Get recent commit messages for style reference."""
    return run_command(f"git log --oneline -{count}")


def analyze_changes(git_status: dict) -> dict:
    """Analyze what files changed and why."""
    untracked_files = []
    modified_files = []

    if git_status["untracked"]:
        for line in git_status["untracked"].split("\n"):
            if line.strip():
                # Parse git status porcelain format
                status = line[:2]
                filepath = line[3:].strip()
                if status.strip() == "??":  # Untracked
                    untracked_files.append(filepath)
                else:
                    modified_files.append(filepath)

    if git_status["diff"] or git_status["staged"]:
        # Extract file names from diff
        diff_output = git_status["diff"] + "\n" + git_status["staged"]
        for line in diff_output.split("\n"):
            if line.startswith("diff --git"):
                match = re.search(r"diff --git a/(.+) b/(.+)", line)
                if match:
                    modified_files.append(match.group(2))

    # Determine change type
    change_type = "feature"  # default
    combined = " ".join(modified_files + untracked_files).lower()
    if "fix" in combined or "bug" in combined:
        change_type = "bug fix"
    elif "refactor" in combined:
        change_type = "refactor"
    elif "readme" in combined or "doc" in combined:
        change_type = "docs"

    return {
        "untracked_files": list(set(untracked_files)),
        "modified_files": list(set(modified_files)),
        "change_type": change_type
    }


def get_branch_name() -> str:
    """Get current branch name."""
    return run_command("git rev-parse --abbrev-ref HEAD")


def draft_pr_title(analysis: dict) -> str:
    """Draft PR title based on analysis."""
    files = analysis.get("modified_files", []) + analysis.get("untracked_files", [])

    if not files:
        return "Update codebase"

    # Simple title based on first file and change type
    primary_file = os.path.basename(files[0])
    change_type = analysis.get("change_type", "update")

    # Convert to title case
    base_name = os.path.splitext(primary_file)[0].replace("_", " ").replace("-", " ")
    base_name = " ".join(word.capitalize() for word in base_name.split())

    title_map = {
        "feature": f"Add {base_name}",
        "bug fix": f"Fix {base_name}",
        "refactor": f"Refactor {base_name}",
        "docs": f"Update {base_name} documentation"
    }

    title = title_map.get(change_type, f"Update {base_name}")

    # Ensure under 70 characters
    if len(title) > 70:
        title = title[:67] + "..."

    return title


def draft_pr_body(analysis: dict) -> str:
    """Draft PR body with proper format."""
    files = analysis.get("modified_files", []) + analysis.get("untracked_files", [])
    change_type = analysis.get("change_type", "update")

    body = f"""## Summary
- {change_type.title()}: {', '.join(files[:3])}
{"- Additional files modified" if len(files) > 3 else ""}

## Test plan
- [ ] Test the changes locally
- [ ] Verify all modified files work as expected
- [ ] Check for any breaking changes

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""
    return body


def ensure_branch_pushed(branch_name: str) -> bool:
    """Ensure branch is pushed to remote."""
    # Check if remote exists
    remote = run_command("git remote get-url origin")
    if not remote:
        print("No remote configured. Skipping push.")
        return False

    # Check if branch exists on remote
    branches = run_command("git branch -r")
    remote_branch = f"origin/{branch_name}"

    if remote_branch not in branches:
        print(f"Pushing new branch '{branch_name}' to origin...")
        result = run_command(f"git push -u origin {branch_name}")
        if result:
            print(f"Successfully pushed branch {branch_name}")
            return True
        return False

    # Push anyway to ensure up to date
    run_command(f"git push origin {branch_name}")
    return True


def create_pull_request(title: str, body: str) -> Optional[str]:
    """Create GitHub PR using gh CLI."""
    # Check if gh is authenticated
    auth_check = run_command("gh auth status")
    if not auth_check or "Logged in" not in auth_check:
        print("Error: Not authenticated with GitHub CLI.")
        print("Run 'gh auth login' first.")
        return None

    # Create PR
    cmd = f'gh pr create --title "{title}" --body "{body}"'
    result = run_command(cmd)

    # Extract PR URL from output
    if result and "http" in result:
        return result

    # Alternative: get PR URL from recent PR
    pr_url = run_command("gh pr view --json url -q '.url'")
    return pr_url if pr_url else result


def run_pr_agent():
    """Main agent to create GitHub PR."""
    print("=" * 50)
    print("GitHub PR Agent")
    print("=" * 50)

    # Step 1: Check current state
    print("\n[1/5] Checking git status...")
    git_status = get_git_status()
    if not git_status["untracked"] and not git_status["diff"] and not git_status["staged"]:
        print("No changes detected. Nothing to commit.")
        return None

    print("[2/5] Getting recent commit history...")
    recent_commits = get_recent_commits()
    print(f"Recent commits:\n{recent_commits}")

    # Step 2: Analyze changes
    print("\n[3/5] Analyzing changes...")
    analysis = analyze_changes(git_status)
    print(f"Modified files: {analysis['modified_files']}")
    print(f"Untracked files: {analysis['untracked_files']}")
    print(f"Change type: {analysis['change_type']}")

    # Step 3: Draft PR
    title = draft_pr_title(analysis)
    body = draft_pr_body(analysis)
    print(f"\nDrafted title: {title}")
    print(f"Drafted body:\n{body}")

    # Step 4: Push branch and create PR
    branch_name = get_branch_name()
    print(f"\n[4/5] Current branch: {branch_name}")

    if branch_name == "main" or branch_name == "master":
        print("Warning: You're on main/master branch. Creating PR anyway.")

    ensure_branch_pushed(branch_name)

    print("\n[5/5] Creating pull request...")
    pr_url = create_pull_request(title, body)

    if pr_url:
        print(f"\n{'=' * 50}")
        print(f"PR created successfully!")
        print(f"URL: {pr_url}")
        print(f"{'=' * 50}")
        return pr_url
    else:
        print("\nFailed to create PR. Check gh authentication.")
        return None


if __name__ == "__main__":
    run_pr_agent()