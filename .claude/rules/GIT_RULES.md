# Git Commit Guidelines

Never add AI attribution footers to commits:

- No `🤖 Generated with ...`
- No `Co-Authored-By: Claude ...`

When creating PRs, use the template in `.github/pull_request_template.md`.

## Branch Naming Convention

```text
[feature, bugfix, hotfix, chore]/short-description
```

## Commit Messages

Follow Conventional Commits format: `type(scope): description`

**Types:**

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature or fix)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```text
feat(auth): add OAuth2 login support
fix(payments): resolve duplicate charge issue
docs(readme): update installation instructions
refactor(api): simplify error handling logic
```
