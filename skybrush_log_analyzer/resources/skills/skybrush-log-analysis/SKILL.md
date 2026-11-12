---
name: skybrush-log-analysis
description: Uses the Skybrush Log Analyzer to analyze ArduPilot logs. Use it to run deterministic log analysis, or check available log analysis tools and tests.
---

# Overview

Skybrush Log Analyzer is a Q&A style ArduPilot log analyzer with test algorithms covering many categories (motor, gps, battery etc.), answering questions about a single log file with human-readable output.

Invoke the CLI as `skybrush-log-analyzer <COMMAND>`. If `skybrush-log-analyzer` is not available, fall back to: `uvx skybrush-log-analyzer <COMMAND>`.

On Windows set `PYTHONIOENCODING=utf-8` (or `PYTHONUTF8=1`) before invoking the CLI.

When authentication fails:

1. Check the output of `skybrush-log-analyzer auth-status`, then stop and tell the user the reason. Do not try to fix it by reading env files or environment variables!
2. If the user is not authenticated, instruct them to run `skybrush-log-analyzer account` command to open a browser where the user can log in to their Skybrush account to create an API key. When the user has the API key, they must run `skybrush-log-analyzer login` to authenticate the CLI app.

If you encounter an issue during the analysis process, stop and notify the user!

Do not attempt any extra, manual analysis unless directly requested by the user.

Avoid rabbit-holes!

## Commands

- `--help`: Show help
- `version`: Get version info
- `auth-status`: Show the current authentication status
- `account`: Open the Skybrush Account page in a web browser, for example to create an API key for `login`
- `login`: Authenticate the CLI application using an API key; login is system-wide by default, the `--local` flag restricts it to the current working directory
- `tests`: List available log tests (`tests` lists the default tests; `tests extra` the extra, verbose ones; `tests all` both groups)
- `analyze PATH/TO/LOG.bin`: Analyze a log file (runs all tests by default) - uploads the log, runs the analysis, and prints a compact summary of the default test results (messages of passing tests are omitted; add `--detailed` to include them). Extra, verbose tests are run and results are stored too, but only shown via `get-analysis-extras`.
- `analyze PATH/TO/LOG.bin -t TEST_NAME`: Run only the given tests, `-t` / `--test` can be repeated: `-t TEST_A -t TEST_B`; unknown test names are rejected before the upload
- `get-analysis PATH/TO/LOG.bin`: Fetch previously stored analysis results for the given log file (same compact summary as `analyze`, default test results only); `-t TEST_NAME` (repeatable) keeps only the given tests, `--detailed` includes the messages of passing tests
- `get-analysis-extras PATH/TO/LOG.bin`: Fetch the extra, verbose test results for the given log file (e.g. full parameter value listing) that are excluded from the default output; supports `-t` and `--detailed` like `get-analysis`
- `suggest -t "TITLE" -c CATEGORY "FEEDBACK TEXT"`: Submit valuable feedback about the analysis service to the Skybrush team; `-t` / `--title` is a short summary (1-100 characters) and `-c` / `--category` is one of `test_case`, `feature`, `improvement`, `bug`, `other`
- `suggestions`: List previously submitted feedback; `--unreleased` limits the list to feedback that has not been released yet
- `web`: Open the Skybrush Log Analyzer web UI in a web browser; `web PATH/TO/LOG.bin` opens the analysis of the given file if the analysis exists

## Standard results vs. extras

- `get-analysis` and `get-analysis-extras` are complementary: the former returns the default test results, the latter the extra, verbose ones.
- Both commands report when the log file has not been analyzed yet - run `analyze`.
- Both commands reject `-t` test names outside their group: the test either does not exist or belongs to the other group - check the `tests` listing and use the matching command.
- Empty `test_results` in either output means the selected tests (all tests of the group by default) have not been run for the given log file yet - run `analyze` to produce them.
- If a test the user asked about is missing from the standard output, check the extras.

## Analysis process

STEP 1: Look for existing analysis results using the `get-analysis` command

- Yes: Notify the user about existing results, ask if fresh log analysis should be triggered, and proceed accordingly.
- No: Move on to next step.

STEP 2: Did the user ask to test or analyze a specific component or topic?

- Yes: Query available tests using the `tests` command. Propose test list to user. The most cost-effective solution is often to run all tests once, and later query and filter existing results.
- No: Move on to next step with no test name filtering.

STEP 3: Analyze the log file using the `analyze` command

STEP 4: Interpret and summarize the relevant results to the user, and inform the user that detailed test results can be checked in the online version of Skybrush Log Analyzer with `skybrush-log-analyzer web PATH/TO/LOG.bin`.

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

Before submitting, check the already submitted feedback with the `suggestions --unreleased` command and do not resubmit feedback that is already covered.

Submit at most one suggestion per distinct issue.

You may submit feedback autonomously. If you are unsure whether something is worth submitting, ask the user first. The feedback API is rate limited.
