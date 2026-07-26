## ADDED Requirements

### Requirement: Dependabot covers every npm lockfile directory
`.github/dependabot.yml` MUST include a `package-ecosystem: npm` entry for each directory in the repository that contains a committed `package-lock.json`, including the repository root (`/`) and `/website`, in addition to the existing frontend directories. Each such entry MUST use a `groups:` block with `patterns: ["*"]` consistent with other ecosystem directories.

#### Scenario: Root and website are watched
- **WHEN** Dependabot runs its weekly npm update check
- **THEN** it evaluates dependency updates for `/` and `/website` as well as `/cloud/frontend` and `/pi/frontend`
- **AND** updates within each directory are opened as one grouped pull request for that directory

### Requirement: Open Dependabot security alerts are remediable
When GitHub reports an open Dependabot security alert for a package in a watched manifest, maintainers MUST remediate by landing a patched version in the corresponding lockfile (via parent bump, `npm update`, or `overrides` when the parent cannot reach a patched range) in a CI-verified PR, unless a documented dismiss rationale applies under the triage requirement below.

#### Scenario: High alert with available patch is fixed in lockfile
- **WHEN** an open High Dependabot alert lists a `first_patched_version` for a package present in a committed lockfile
- **THEN** a pull request updates that lockfile so the installed version is at or above the patched version
- **AND** the repository’s applicable lint/test checks for the touched workspace pass

### Requirement: Security-alert triage prefers fix over dismiss
Maintainers MUST attempt a lockfile or dependency remediation for Dependabot security alerts that have a published patched version before dismissing. Dismissal (or “won’t fix”) is allowed ONLY when remediation is impossible or exploitability is clearly outside the product threat model, and MUST include a written rationale on the alert (same bar as existing Code scanning won’t-fix dismissals for edge credential storage).

#### Scenario: Dismiss only with written rationale
- **WHEN** a Dependabot or Code scanning alert is dismissed without a dependency/workflow change
- **THEN** the dismissal includes a human-readable comment explaining why the finding is not remediable or not applicable
- **AND** the reason is one of GitHub’s supported dismissal reasons

### Requirement: Dependabot PR close lifecycle is explicit
When closing a Dependabot pull request without merging it, maintainers MUST leave a comment that states one of: (a) superseded by a named combined PR number, (b) ignored via `@dependabot ignore …` (or an equivalent `ignore:` rule in `dependabot.yml`) with the peer/compat reason, or (c) no longer needed because `main` already satisfies the target version. Closing without such a comment is not allowed for Dependabot-authored PRs.

#### Scenario: Supersede into a combined PR
- **WHEN** maintainers combine several Dependabot updates into one PR
- **THEN** each superseded Dependabot PR receives a comment naming the survivor PR before it is closed

#### Scenario: Ignore an incompatible major
- **WHEN** a Dependabot PR proposes a major that breaks peer ranges (for example TypeScript 7 vs current typescript-eslint)
- **THEN** the PR is closed with an ignore instruction or config `ignore:` rule and a short comment naming the peer conflict
- **AND** the ignore does not silently strand security alerts on unwatched directories
