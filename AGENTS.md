# AGENTS.md

## OSS safety before GitHub changes

No GitHub mutation is implied by an implementation request. Before any future
push, issue, pull request, release, or other GitHub mutation, verify all of:

- the working path is the canonical checkout
  `~/Projects/personal/helix-orca-calibration` (personal/OSS repositories may
  canonically live beneath `~/Projects/personal/`);
- `git config user.name` is `bigstupid007`;
- `git config user.email` is `monkey.nfm@gmail.com`;
- the origin uses the `github-oss` SSH host;
- `gh-oss auth status` shows `bigstupid007` as the active account using the
  isolated `GH_CONFIG_DIR=$HOME/.config/gh-bigstupid007` profile.

Use `gh-oss` for this repository's Issues, pull requests, Actions, releases,
and other GitHub control-plane operations. Keep the normal `gh` profile and
the default `github.com` SSH behavior on `cdemichael`; do not switch, remove,
or rewrite that business identity while working on this repository.

Stop and report a mismatch instead of changing identity or remote settings
without explicit instruction.
