# Skybrush Log Analyzer

Command line application for analyzing ArduPilot logs using [Skybrush Log Analyzer](https://logs.skybrush.io).

Agent skill included for AI assistance.

## Install

**Option A (recommended): install as a tool**

```bash
uv tool install skybrush-log-analyzer
```

If `uv` warns that its tool binary directory (e.g. `~/.local/bin`) is not on your `PATH`, follow its suggestion so `skybrush-log-analyzer` can be invoked directly.

**Option B: run without installing**

Skip installation and prefix every CLI command with `uvx skybrush-log-analyzer`.

## How to use

The commands below assume Option A.

1. Create a Skybrush API key at [https://account.skybrush.io/developer](https://account.skybrush.io/developer)
2. Log in with your API key: `skybrush-log-analyzer login`
3. Navigate to the directory containing your log files and analyze a log file: `skybrush-log-analyzer analyze <path-to-log-file>`

Run `skybrush-log-analyzer --help` to see all commands.

## Agent skill

The project comes with an agent skill that helps agents use the included CLI to help you with log analysis.

You can install the skill with the following command:

```bash
skybrush-log-analyzer add-skill
```

Or, without installing the CLI:

```bash
uvx skybrush-log-analyzer add-skill
```

Good to know:

- By default, the skill will be installed globally to `.agents/skills` in your home directory.
- If you use Claude Code, add the `--claude` option to the command, which changes the install path to `.claude/skills`.
- To install the skill in the current working directory, use the `--local` option.

Depending on your agent harness, you may need to restart or reload the harness so it recognizes the newly installed skill.

Assuming you logged in and navigated to your log files as described above, all you need to do is start a new agent session, check whether the `skybrush-log-analysis` skill appears in the list of loaded skills, and prompt the agent to analyze a log file or list available log analysis tests.

## Upgrade

When using `uv tool`, upgrade the CLI and re-install the bundled agent skill so that it matches the new version:

```bash
uv tool upgrade skybrush-log-analyzer
skybrush-log-analyzer add-skill --force
```

When using `uvx`, the CLI always runs the latest revision, but the installed skill does not follow automatically. Refresh it periodically to avoid inconsistency between the skill and the CLI:

```bash
uvx skybrush-log-analyzer add-skill --force
```

## Troubleshooting

### [Windows] Character encoding issues

Set `PYTHONIOENCODING=utf-8` before commands to avoid Windows codepage errors (e.g. `UnicodeEncodeError` on `µ`), or set the `PYTHONUTF8=1` environment variable permanently.
