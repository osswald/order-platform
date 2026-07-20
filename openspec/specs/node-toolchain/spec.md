# node-toolchain Specification

## Purpose
Define the supported Node.js major for frontend CI, Docker builds, TypeScript declarations, and locale-sensitive Pi money-format tests.

## Requirements
### Requirement: Frontend toolchain uses Node 24 LTS
CI jobs that install Node for cloud frontend, pi frontend, lint, or OpenAPI type generation, and Docker images that build or serve those frontends (including the website production build), MUST use Node major version **24** (Active LTS). TypeScript `@types/node` for cloud and pi frontends MUST be on the Node 24 line so declared APIs match the runtime. Developer documentation MUST state Node 24 as the supported major.

#### Scenario: CI installs Node 24
- **WHEN** a pull request runs frontend tests, ESLint for a frontend, or OpenAPI frontend type generation
- **THEN** the workflow configures Node version `24`

#### Scenario: Frontend images are Node 24-based
- **WHEN** cloud frontend, pi frontend, or website production images are built from repository Dockerfiles
- **THEN** the Node base image major is `24` (for example `node:24-alpine`)

#### Scenario: Typings match the runtime major
- **WHEN** cloud or pi frontend dependencies are inspected
- **THEN** `@types/node` resolves to a 24.x declaration package (not 20.x or 26.x)

### Requirement: Locale-sensitive money tests tolerate ICU apostrophe variants
Pi frontend tests that assert Swiss-style numeric grouping MUST NOT fail solely because the ICU group separator is a typographic apostrophe (`U+2019`) instead of ASCII apostrophe (`U+0027`). They MUST still require apostrophe-style thousands grouping and a decimal point for fractional amounts.

#### Scenario: formatAmount under Node 24 ICU
- **WHEN** `formatAmount` is tested for a value that needs thousands grouping (for example `123456` cents → `1234.56`)
- **THEN** the assertion accepts either ASCII or typographic apostrophe as the group separator and still expects `.` as the decimal separator
