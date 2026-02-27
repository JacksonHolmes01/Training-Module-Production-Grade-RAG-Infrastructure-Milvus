# NIST SP 800-53 Rev 5 — Selected Controls for Container and API Security

Source: NIST Special Publication 800-53 Revision 5
Framework: NIST
Tags: nist, compliance, access-control, audit, risk

---

## AC — Access Control

### AC-2 — Account Management
Organisations must manage accounts throughout their lifecycle: creation, modification, disabling, and removal. This includes service accounts used by applications and containers.

For container workloads:
- Use dedicated service accounts per service (not shared root credentials).
- Rotate credentials on a defined schedule.
- Disable accounts immediately upon role change or departure.

### AC-3 — Access Enforcement
The information system enforces approved authorisations for logical access to information. Every API endpoint must enforce authorisation before providing access to a resource.

In practice: implement authorisation checks server-side. Client-side authorization (hiding buttons in a UI) is not a security control.

### AC-6 — Least Privilege
Grant only the minimum access required. For containers: drop all Linux capabilities and add back only what is strictly needed. For APIs: implement role-based access control where each role has only the permissions it requires.

### AC-17 — Remote Access
Remote access sessions must be managed and encrypted. All API traffic should be TLS-encrypted. Plain HTTP is not acceptable for production deployments.

---

## AU — Audit and Accountability

### AU-2 — Audit Events
Define which events are auditable. For APIs: authentication successes and failures, authorisation failures, data access events, and configuration changes are all auditable events.

### AU-3 — Content of Audit Records
Each audit record must contain: date and time, source, type of event, subject identity, and outcome. Log structured JSON rather than free-form text to make automated analysis possible.

### AU-9 — Protection of Audit Information
Audit logs must be protected from modification and unauthorised access. Do not allow applications to write directly to the audit log store they would be audited against. Ship logs to a separate system.

---

## CM — Configuration Management

### CM-6 — Configuration Settings
Establish and document configuration settings for all system components. For Docker containers: document and enforce which ports are exposed, which volumes are mounted, and which capabilities are granted.

### CM-7 — Least Functionality
Configure the system to provide only essential capabilities. Disable unused services, protocols, and ports. Containers should run a single process where possible.

### CM-8 — Information System Component Inventory
Maintain an inventory of all system components. For container-based systems: maintain an inventory of images, tags, and deployed versions. Understand which images are running in production at any given time.

---

## IA — Identification and Authentication

### IA-2 — Identification and Authentication (Organisational Users)
Uniquely identify and authenticate organisational users. API keys should be unique per user or client application. Shared keys make attribution and revocation impossible.

### IA-5 — Authenticator Management
Manage credentials throughout their lifecycle. API keys and secrets must be:
- Generated with sufficient entropy (≥128 bits recommended).
- Stored securely (not in source code, not in plain text in logs).
- Rotated on a defined schedule or immediately upon suspected compromise.
- Revocable without service interruption.

---

## RA — Risk Assessment

### RA-5 — Vulnerability Scanning
Scan for vulnerabilities in all deployed components. For container-based systems: scan Docker images for known CVEs using tools like Trivy, Grype, or Docker Scout. Integrate scanning into CI/CD pipelines.

---

## SC — System and Communications Protection

### SC-5 — Denial-of-Service Protection
Protect against DoS attacks. Implement rate limiting at the API gateway. Set resource limits on containers. Monitor for anomalous traffic patterns.

### SC-8 — Transmission Confidentiality and Integrity
Protect information transmitted over networks. All external API communication must use TLS 1.2 or higher. Internal service-to-service communication inside a trusted network may use plain HTTP, but only if access to that network is strictly controlled.

### SC-28 — Protection of Information at Rest
Sensitive data must be encrypted at rest. For vector databases: secrets in `.env` files must not be stored unencrypted in source control. Use secrets management tools in production.

---

## SI — System and Information Integrity

### SI-2 — Flaw Remediation
Identify, report, and correct software flaws. Establish a process for ingesting CVE notifications for all dependencies. Pin dependency versions and update them on a defined schedule.

### SI-10 — Information Input Validation
Validate all input received from sources outside the security boundary. For APIs: validate input type, length, format, and range. Reject malformed input with a 400 response before processing.
