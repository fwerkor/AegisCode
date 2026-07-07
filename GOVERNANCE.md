# Project Governance

AegisCode is maintained with a lightweight maintainer-led model.

## Maintainers

Maintainers are responsible for:

- Reviewing and merging pull requests.
- Keeping CI, release, packaging, and documentation usable.
- Protecting governance-sensitive code paths.
- Handling security reports and responsible disclosure.
- Publishing releases and release notes.

## Decision process

Most decisions are made through pull request review. A change may be merged when it is technically sound, tested, documented when needed, and aligned with the project direction.

Maintainers may reject changes that:

- Weaken guardrails, approval semantics, workspace boundaries, or credential handling.
- Add large dependencies without clear value.
- Increase maintenance cost without a stable use case.
- Break packaging, installers, CI, or release workflows.
- Are not reproducible or reviewable.

## Release policy

Releases are tagged from `main`. Pre-releases may be used while the project is still stabilizing.

Release candidates should satisfy:

- Test suite passes.
- Packaging validation passes.
- Release version metadata is consistent.
- Release artifacts are generated through CI.
- Security-sensitive changes have regression tests.

## Compatibility

AegisCode may make breaking changes before a stable 1.0 release. Breaking changes should be documented in release notes and migration guidance when practical.
