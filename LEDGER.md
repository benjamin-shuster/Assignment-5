# Provenance Ledger

Write one entry per reviewable change, when the work is done, using exactly the schema
in HANDOUT.md. Put the prompts you typed into AI tools in `prompts/` and name the file in
the entry's `prompts` field. When a subagent did the work, name it in the `tool` field.

## Worked example (not graded; leave it here and add your entries under "My entries")

This shows the level of detail expected. The change is not part of this assignment, and
the commit SHA, date and numbers are made up.

```
## Entry 0
artifact:  commit 3f9c2ab, GET /api/health in app/routes.py (example only)
tool:      Claude Code 2.1.x, main agent, Claude Opus model, 2031-03-01
prompts:   asked for a health endpoint that returns {"ok": true}; prompts/00-health.txt
review:    read the diff. The agent also added a "version" field and a new package to
           read it from git; I rejected both because the request did not ask for them,
           and kept only the endpoint.
checks:    python -m pytest: 41 passed. python tools/check_layers.py: passed.
evidence:  request from the operations team, ticket OPS-12
risk:      no test checks the endpoint under load; not needed for this change.
```

## My entries

## Entry 1

- artifact: `docs/spec.md` section 7
- tool: Antigravity main agent, Gemini 4 Hydrogen, 2026-11-26
- prompts: prompts/part3.md
- review: Read the output questions and the spec and validated that the questions are not already answered in the spec. 
- checks: manual review of the spec and the questions.
- evidence: Handout part 3
- risk: agent may still have misunderstood the spec or the questions


## Entry 2

- artifact: `tests/acceptance/**`
- tool: Antigravity main agent, Gemini 4 Hydrogen, 2026-11-26
- prompts: prompts/part4.md
- review: Read the agent output and quickly verified that the tests cover the rules in the spec. 
- checks: ran the tests against the backend and verified that they failed as expected.
- evidence: Handout part 4
- risk: I might have missed some tests that do not cover the rules, or that the agent misunderstood the spec and wrote tests that do not actually test the rules.

## Entry 3

- artifact:  `app/repository.py`
- tool: Antigravity main agent, Gemini 4 Hydrogen, 2026-11-27
- prompts: prompts/buildtask1.md
- review: Read the agent output and test the implementation.
- checks: ran the tests and verified the implementation works as expected.
- evidence: Handout part 6
- risk: The agent may have misunderstood the spec and implemented something that does not actually meet the requirements.
- followup: I needed to fix permissions because the settings I set up for the final project also applied here. As A result, the agent was unable to run the tests. 
