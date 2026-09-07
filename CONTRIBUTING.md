# Contributing

Octocarte is maintained as an independent project derived from Octo-Fiesta.
Preserve upstream history, copyright notices and license terms. Keep ALACarte
extensions separate from Octocarte and retain their AGPL-3.0-only attribution.
The initial provider scope and validation limits are documented in README.md.

## Changes

- Branch from `dev` for one concrete change. Use descriptive names such as
  `feature/alacarte-service-auth` or `fix/stream-range-handling`.
- Commit coherent changes with messages that describe the resulting behavior.
- Open a pull request against `dev`. Explain the problem, implementation,
  relevant tests and deployment impact. Use a draft while required work remains.
- Run the required CI checks and review the complete diff before merging.
  Preserve meaningful milestone commits with a merge commit. Do not claim an
  independent review when none occurred. Auto-merge is not part of this workflow.
- Authentication, streaming and storage changes need focused regression tests
  and an isolated integration check. Documentation changes need link and content
  review. Record manual results separately from automated test coverage.

These are project conventions. They are not a claim that GitHub branch
protection or required approvals have been configured on the private repository.

## Validated builds

`mvp-validated-2026-09-07` identifies the Wavio-validated baseline. Do not move or
replace validation/release tags. Develop candidates in separate checkouts and
use distinct image tags. Do not replace a running validated image as a side
effect of testing a candidate.

An eventual public release should use Octocarte's own version sequence and
release notes. Retained upstream tags identify upstream history, not Octocarte
releases. A source merge, an image build and deployment are separate operations.
Document the exact image versions and rollback procedure for each deployment.

## Secrets and operational data

Keep credentials in local secret files. Do not include tokens, authentication
query parameters, signed stream URLs, or private configuration in issues, logs,
test output or commits. Test with generated, disposable credentials. Never use
ALACarte's master secret as an Octocarte integration credential.

Before public release, review full Git history and release artifacts for
credentials and installation-specific data; verify attribution and redistribution
requirements for included components; and reproduce installation from the
published instructions. Passing the MVP does not establish long-term stability.
