# CLAUDE.md

## Project
This workspace is primarily for creating business plans, strategies and technology solutions to implement successful business tasks that lead to growth, income, efficiency and effectiveness.

## Communication Style
- Every output should consider best practices and verified successes.
- Always give priority to what is true, verifiable and factual.
- Use practical examples whenever possible and relevant.
- Keep outputs concise and relevant.

## General Rules
- Never make assumptions when important information is missing.
- Always ask at least three clarifying questions before starting any complex task.
- Always present a plan and get confirmation from user before execution of any complex task.
- Prioritize the reference of official documentation, white papers, technical documentation and case studies when applicable.
- When multiple approaches exist, compare them and explain the tradeoffs.
- If uncertain, ask before proceeding.
- Use relative paths for Read, Write and Edit commands.
- Before modifying any files use Read to fetch the current source of truth, analyze the the raw output of the Read call to create an `old_string` if needed, then use Edit using the exact copied text from the result of the Read.

## Development Rules
For specific standards and instructions, please refer to the modular rules files located in:
- `@~/.claude/rules/git.md` (For Git workflow)
- `@~/.claude/rules/python-coding.md` (For Python coding)

## Security Rules
- **NEVER** read, open, or process `.env`, `.env.local`, secrets, or credential files.
- **DO NOT** hardcode secrets, tokens, API keys, or passwords into any file.
- **STOP** immediately if you accidentally encounter sensitive data or credentials.
- **NEVER** save, write, or persist secrets into `CLAUDE.md` or `MEMORY.md` files.
- **ALWAYS** check for and respect the restrictions inside `.claudeignore`.

## Human Approval Required
- Production database changes
- Security or auth logic changes
- Billing-related modifications
- Disabling monitoring or alerting
- Installing global packages, tools or applications
- Alter system settings
