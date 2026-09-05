I'm building VoxFlow, an AI voice agent for supply-chain/logistics ops.
Repo: github.com/jeevesh2515/voxflow-voice-agent — Next.js in web/,
FastAPI in apps/api/.

I have a phased SaaS-readiness roadmap in Markdown files. I'll hand you one
phase file at a time, in separate sessions. Ground rules for every phase,
no exceptions:

1. Read the attached phase file in full before writing any code.
2. Follow the working steps in the order given. Don't skip ahead, don't
   combine work from a different phase, don't touch anything listed under
   that file's "Explicitly out of scope" section.
3. If a step references a file, table, function, or endpoint that doesn't
   actually exist in this repo, STOP immediately and tell me the
   discrepancy. Do not invent a plausible-sounding substitute and continue
   as if it worked.
4. Definition of Done checkboxes must be verified, not assumed. Run the
   actual test, command, or manual check each item describes and show me
   the real output. Don't check a box because the code "should" work.
5. The existing test suite (582 tests) and eval harness
   (`scripts/run_evals.py --strict`, 30 scenarios) must stay green after
   every phase. Run them at the end and report the actual output, not a
   summary claim.
6. When every Definition of Done item is verified, STOP. Give me a summary
   of what was done and what was verified. Do not proceed into any other
   phase on your own, even if you've seen other phase files in this
   conversation before.
7. Universal Pre-Push Ponytail Law: Before staging, committing, or pushing
   code to GitHub, invoke `/ponytail-review` or inspect the diff and
   aggressively prune dead code, premature abstractions, speculative
   features, reinvented standard library functions, and verbose boilerplate.
   Re-run tests to confirm zero regression. Never commit bloated code.

Confirm you understand these rules before I attach the first phase file.
