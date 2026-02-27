# OWASP API Security Top 10 — 2023

Source: OWASP API Security Project
Framework: OWASP
Tags: owasp, api, security, web

---

## API1:2023 — Broken Object Level Authorization (BOLA)

APIs tend to expose endpoints that handle object identifiers, creating a wide attack surface. Object level access controls should be considered in every function that accesses a data source using input from the user.

**Example:** A user is authenticated as user A and calls `GET /users/B/profile`. The API returns user B's profile without checking whether the caller is authorized to access it.

**Prevention:**
- Implement object-level authorization checks for every API endpoint that accesses a resource using a client-supplied ID.
- Use random, non-sequential IDs (UUIDs) for object identifiers.
- Write automated tests to validate authorization logic.

---

## API2:2023 — Broken Authentication

Authentication mechanisms are implemented incorrectly, allowing attackers to compromise authentication tokens or exploit implementation flaws to assume other users' identities.

**Example:** An API accepts weak passwords, does not implement rate limiting on login attempts, or stores tokens in insecure locations.

**Prevention:**
- Use strong, industry-standard authentication (OAuth 2.0, OpenID Connect).
- Implement brute-force protection and account lockout policies.
- Use short-lived access tokens and implement secure token refresh.
- Validate all token fields: issuer, audience, expiry.

---

## API3:2023 — Broken Object Property Level Authorization

APIs expose more object properties than required. Combined with insufficient access controls, attackers can read or write properties they should not be able to access.

**Example:** `GET /users/me` returns `{id, name, email, role, password_hash, internal_flags}`. The caller should only see `{id, name, email}`.

**Prevention:**
- Return only the properties the caller needs. Never expose internal fields.
- Avoid mass assignment: validate and whitelist which fields can be updated.
- Use serialization schemas that explicitly define exposed fields.

---

## API4:2023 — Unrestricted Resource Consumption

API requests consume resources: CPU, memory, disk, bandwidth, downstream service calls. Attackers exploit this to perform Denial of Service attacks or incur unexpected costs.

**Example:** An API endpoint accepts a `limit` parameter with no maximum. An attacker sends `limit=10000000`, causing the server to attempt to load millions of records.

**Prevention:**
- Enforce maximum values for all pagination parameters.
- Implement rate limiting at the API gateway layer.
- Set timeouts on all downstream service calls.
- Monitor for anomalous request patterns and alert on spikes.

---

## API5:2023 — Broken Function Level Authorization

Complex access control policies with different roles and groups tend to lead to authorization flaws. Administrative functions are particularly at risk.

**Example:** A regular user can call `DELETE /admin/users/{id}` because the endpoint exists and the API does not check whether the caller has admin privileges.

**Prevention:**
- Deny all access by default; explicitly grant permissions per role.
- Review all administrative and privileged API functions regularly.
- Do not rely on obscurity (e.g., not documenting admin endpoints) as a security control.

---

## API6:2023 — Unrestricted Access to Sensitive Business Flows

APIs expose business flows (e.g., buying tickets, creating accounts, posting reviews) that can be abused when used at scale or in sequence.

**Example:** An automated script buys all available concert tickets by calling the purchase API thousands of times, then resells them.

**Prevention:**
- Identify high-value business flows and apply stricter controls (CAPTCHA, device fingerprinting, rate limiting per user or IP).
- Detect and block abnormal usage patterns.

---

## API7:2023 — Server Side Request Forgery (SSRF)

SSRF vulnerabilities occur when an API fetches a remote resource based on a user-supplied URL without validating it.

**Example:** An API accepts a URL parameter (`?callback=http://...`) and makes an HTTP request to it. An attacker passes `http://169.254.169.254/latest/meta-data/` (AWS metadata service).

**Prevention:**
- Validate and sanitize all user-supplied URLs.
- Use an allowlist of permitted domains or IP ranges.
- Disable URL redirection follow for user-supplied URLs.
- Reject private, loopback, and link-local addresses.

---

## API8:2023 — Security Misconfiguration

APIs are commonly misconfigured: verbose error messages, unnecessary HTTP methods enabled, missing security headers, unpatched services.

**Example:** An API returns a full stack trace (including file paths and framework version) when an unhandled exception occurs, helping attackers fingerprint the stack.

**Prevention:**
- Return generic error messages in production; log details server-side.
- Disable unused HTTP methods on all endpoints.
- Set security headers: `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`.
- Run regular vulnerability scans and patch dependencies promptly.

---

## API9:2023 — Improper Inventory Management

Organisations often lose track of the APIs they have deployed: outdated API versions, undocumented shadow APIs, debug endpoints left in production.

**Example:** A legacy v1 API endpoint is still accessible even though v2 has been deployed. The v1 endpoint does not have the same input validation as v2 and is exploited.

**Prevention:**
- Maintain an up-to-date API inventory.
- Retire old API versions promptly and return 410 Gone for removed endpoints.
- Use API gateways to enforce which endpoints are exposed externally.

---

## API10:2023 — Unsafe Consumption of APIs

Developers trust third-party APIs without adequate validation of the data they return, leading to injection or deserialization attacks.

**Example:** An application trusts that a third-party geocoding API only returns safe data. When the third-party is compromised, it starts returning malicious HTML that the application injects into pages.

**Prevention:**
- Treat data from external APIs as untrusted input.
- Validate and sanitize all data received from third-party APIs.
- Evaluate the security posture of third-party API providers.
- Use TLS for all third-party API communications.
