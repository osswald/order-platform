# rental-inquiry Specification

## Purpose
Public Mietanfrage form and email-only delivery path: Kontakt form on the marketing site, unauthenticated cloud API with validation and spam controls, no durable lead storage in the application database.

## Requirements

### Requirement: Mietanfrage form on Kontakt page
The marketing site SHALL provide a German Mietanfrage form on `/kontakt/` that collects name, organisation, email, optional phone, event timeframe or dates, and a message.

#### Scenario: Required fields shown
- **WHEN** a visitor opens `/kontakt/`
- **THEN** the form displays fields for name, organisation, email, optional phone, timeframe/dates, and message, with German labels

#### Scenario: Successful submit shows confirmation
- **WHEN** a visitor submits a valid inquiry
- **THEN** the page shows a German confirmation that the request was sent and does not require navigating to a separate thank-you URL

### Requirement: Email-only delivery
The system SHALL deliver accepted rental inquiries by email to a configured Vendiqo inbox and SHALL NOT persist inquiry payloads in the application database as leads.

#### Scenario: Accepted inquiry is emailed
- **WHEN** a valid inquiry is accepted by the public API
- **THEN** an email containing the inquiry fields is sent to the configured recipient address

#### Scenario: No lead row stored
- **WHEN** a valid inquiry is accepted
- **THEN** the system does not create a durable lead or inquiry record in the application database

### Requirement: Public inquiry API with validation
The cloud backend SHALL expose an unauthenticated public endpoint that accepts Mietanfrage submissions, validates required fields and email format, and rejects invalid payloads with client error responses.

#### Scenario: Missing required field rejected
- **WHEN** a client posts an inquiry missing a required field
- **THEN** the API responds with a 4xx status and does not send email

#### Scenario: Valid payload accepted
- **WHEN** a client posts a complete valid inquiry and mail delivery is configured
- **THEN** the API accepts the request and triggers email delivery

### Requirement: Spam and abuse controls
The inquiry path SHALL include a honeypot field that must be empty and SHALL apply per-client rate limiting on the public endpoint.

#### Scenario: Filled honeypot rejected
- **WHEN** a client posts an inquiry with a non-empty honeypot field
- **THEN** the API rejects or ignores the submission without sending a rental-inquiry email to the inbox

#### Scenario: Excessive submissions rate limited
- **WHEN** a client exceeds the configured submission rate
- **THEN** subsequent requests receive a rate-limit response

### Requirement: Privacy notice for inquiries
The Kontakt form SHALL link to Datenschutz, and Datenschutz content SHALL describe that Mietanfragen are processed to respond to rental requests and are transmitted by email.

#### Scenario: Form links to privacy policy
- **WHEN** a visitor views the Mietanfrage form
- **THEN** a link to `/datenschutz/` is visible near the form

#### Scenario: Privacy policy covers inquiries
- **WHEN** a visitor reads Datenschutz after this change
- **THEN** the policy describes processing of contact/rental inquiry data for responding to requests
