---
name: create-pr
description: Creates a GitHub pull request with proper format. Use when user asks to create, open, or submit a PR.
disable-model-invocation: true
---

When the user asks to create a pull request:

1. **Check current state first:**
   - Run `git status` to see untracked files
   - Run `git diff` to see staged and unstaged changes
   - Run `git log` to see recent commit messages for style

2. **Analyze the changes:**
   - Summarize what files were changed and why
   - Identify if this is a new feature, bug fix, refactor, or docs
   - Keep the PR title under 70 characters

3. **Draft the PR:**
   - Title: Focus on the "what" not "how" (e.g., "Add user authentication" not "Added auth middleware")
   - Body format:
     ```markdown
     ## Summary
     - 1-3 bullet points on what changed

     ## Test plan
     - [ ] Bulleted checklist of how to test

     🤖 Generated with [Claude Code](https://claude.com/claude-code)
     ```

4. **Create the PR using `gh pr create`:**
   - Push the branch first if needed: `git push -u origin <branch-name>`
   - Use `--title` and `--body` flags with the drafted content

5. **Return the PR URL** so the user can view it.

Important: Never skip hooks or use --no-verify. Always create NEW commits rather than amending.