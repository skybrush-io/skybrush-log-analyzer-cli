---
name: skybrush-log-analysis
description: Uses the Skybrush Log Analyzer to analyze ArduPilot logs. Use it to run deterministic log analysis, or check available log analysis tools and tests.
---

# Overview

Skybrush Log Analyzer is a Q&A style ArduPilot log analyzer with test algorithms covering many categories (motor, gps, battery etc.), answering questions about a single log file with human-readable output.

Invoke the CLI as `skybrush-log-analyzer <COMMAND>`. If `skybrush-log-analyzer` is not available, fall back to: `uvx skybrush-log-analyzer <COMMAND>`.

On Windows set `PYTHONIOENCODING=utf-8` (or `PYTHONUTF8=1`) before invoking the CLI.

If authentication fails, stop and tell the user! Do not try to fix it by reading env files or environment variables!

If you encounter an issue during the analysis process, stop and notify the user!

Do not attempt any extra, manual analysis unless directly requested by the user.

Avoid rabbit-holes!

## Commands

- `--help`: Show help
- `version`: Get version info
- `tests`: List available log tests (`tests` lists the default tests; `tests extra` the extra, verbose ones; `tests all` both groups)
- `analyze PATH/TO/LOG.bin`: Analyze a log file (runs all tests by default) - uploads the log, runs the analysis, and prints a compact summary of the default test results (omitting passing tests). Extra, verbose tests are run and results are stored too, but only shown via `get-analysis-extras`.
- `analyze PATH/TO/LOG.bin -t TEST_NAME`: Run only the given tests, `-t` / `--test` can be repeated:`-t TEST_A -t TEST_B`
- `get-analysis PATH/TO/LOG.bin`: Fetch previously stored analysis results for the given log file (same compact summary as `analyze`, default test results only); add `--raw` for the untrimmed API response
- `get-analysis-extras PATH/TO/LOG.bin`: Fetch the extra, verbose test results for the given log file (e.g. full parameter value listing) that are excluded from the default output; add `--raw` for the untrimmed API response
- `suggest -t "TITLE" -c CATEGORY "FEEDBACK TEXT"`: Submit valuable feedback about the analysis service to the Skybrush team; `-t` / `--title` is a short summary (1-100 characters) and `-c` / `--category` is one of `test_case`, `feature`, `improvement`, `bug`, `other`
- `auth-status`: Show the current authentication status

## Standard results vs. extras

- `get-analysis` and `get-analysis-extras` are complementary: the former returns the default test results, the latter the extra, verbose ones.
- Empty `test_results` in either output means no tests from that group have been run for the given log file yet - run `analyze` to produce them.
- If a test the user asked about is missing from the standard output, check the extras.

## Analysis process

STEP 1: Look for existing analysis results using the `get-analysis` command

- Yes: Notify the user about existing results, ask if fresh log analysis should be triggered, and proceed accordingly.
- No: Move on to next step.

STEP 2: Did the user ask to test or analyze a specific component or topic?

- Yes: Query available tests using the `tests` command. Propose test list to user. The most cost-effective solution is often to run all tests once, and later query and filter existing results.
- No: Move on to next step with no test name filtering.

STEP 3: Analyze the log file using the `analyze` command

STEP 4: Interpret and summarize the relevant results to the user

## Submitting feedback

Submit feedback with the `suggest` command when you notice any of the following:

- A test result contradicts what the log actually shows (suspected bug) — category `bug`.
- No available test covers something you or the user needed, or an existing test would need a change to cover it — category `test_case`.
- The results are correct but confusing, incomplete, or hard to work with — category `improvement`, or `feature` if it requires a new capability.
- The user's reaction suggests that feedback or test suite changes would be useful (e.g. they question a result, seem dissatisfied with it, or pinpoint a key detail that would have helped the analysis) — category `other` unless it clearly matches one of the above.

Regarding the feedback message:

- Make it technical and self-contained
- Make it concise, but detailed enough for the reader to fully understand the details and the context
- Reference affected or related test names and log messages where relevant
- End the message with a line identifying yourself, in this format: `By: <model> (<harness>)`

Never include secrets in the feedback!

Submit as soon as the issue is understood well enough for meaningful feedback; do not let it interrupt or delay the analysis for the user.

Submit at most one suggestion per distinct issue.

You may submit feedback autonomously. If you are unsure whether something is worth submitting, ask the user first. The feedback API is rate limited.
