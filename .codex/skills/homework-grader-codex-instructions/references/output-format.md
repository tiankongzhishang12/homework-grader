# Output Format

Use concise Chinese output unless the user asks otherwise.

## For Implementation Tasks

Include:

- changed files;
- what changed;
- backend/frontend/database/Python impact;
- verification commands and results;
- unresolved risks or conflicts.

## For Documentation Tasks

Include:

-新增文件清单；
- 每个 document or Skill 的用途；
- 是否检查了 code source of truth；
- 是否发现文档与代码冲突；
- 后续建议。

## For Reviews

Lead with findings:

- severity;
- file and line when available;
- impact;
- suggested fix.

If no issues are found, say so clearly and mention remaining test gaps.

## For Blockers

State:

- what blocked completion;
- what was already checked;
- exact next action needed from the user;
- any safe partial result.
