---
inclusion: always
---

# Testing & Internationalization Rules

## Python Code Execution

**NEVER** use execution via `python -c ` pattern in the session. This causes PTY host exceptions and terminal disconnections that block task execution.

Instead:
- Write code to a `.py` file and execute it
- Use pytest for testing
- Use the Python REPL interactively if needed

## Internationalization (i18n)

The system must support bilingual (Chinese/English) interfaces:

| Requirement | Implementation |
|-------------|----------------|
| UI text | Externalize all user-facing strings |
| Error messages | Provide translations for both languages |
| API responses | Support `Accept-Language` header |
| Configuration | Language preference stored per user |

### Language Consistency Rules

- Maintain consistent terminology across the codebase
- Use language keys/constants instead of hardcoded strings
- Document any language-specific business logic
- Test both language variants when modifying UI text
