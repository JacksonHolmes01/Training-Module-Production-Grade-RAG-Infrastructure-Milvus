# Financial Sector Cybersecurity Guidance

---

## FFIEC Cybersecurity Assessment Tool (CAT)

**Source:** https://www.ffiec.gov/cyberassessmenttool.htm

The FFIEC Cybersecurity Assessment Tool helps financial institutions identify their risks
and determine their cybersecurity maturity across five domains.

### Domain 1: Cyber Risk Management and Oversight
- Board and senior management oversight of cybersecurity risk
- Cybersecurity strategy aligned with business strategy
- Policies, standards, and procedures
- Risk management function

### Domain 2: Threat Intelligence and Collaboration
- Threat intelligence program
- Monitoring and analyzing threats
- Information sharing and collaboration

### Domain 3: Cybersecurity Controls
- Preventive controls (access management, device/end-point security, secure coding)
- Detective controls (threat and vulnerability detection, anomalous activity detection)
- Corrective controls (patch management, remediation)

### Domain 4: External Dependency Management
- Connections — managing third-party and vendor access
- Relationship management — due diligence and contracts
- Third-party monitoring

### Domain 5: Cyber Incident Management and Resilience
- Incident response and resilience planning
- Detection, response, and mitigation
- Escalation and reporting

---

## PCI DSS v4.0 — Payment Card Industry Data Security Standard

**Source:** https://www.pcisecuritystandards.org
**Applies to:** Any organization that processes, stores, or transmits payment card data.

### 12 Core PCI DSS Requirements

**Build and Maintain a Secure Network and Systems**
- Req 1: Install and maintain network security controls (firewalls, network segmentation)
- Req 2: Apply secure configurations to all system components (no vendor defaults)

**Protect Account Data**
- Req 3: Protect stored account data (encryption, truncation, masking)
- Req 4: Protect cardholder data with strong cryptography during transmission over open networks

**Maintain a Vulnerability Management Program**
- Req 5: Protect all systems and networks from malicious software (anti-malware)
- Req 6: Develop and maintain secure systems and software (patch management, secure development)

**Implement Strong Access Control Measures**
- Req 7: Restrict access to system components and cardholder data by business need to know
- Req 8: Identify users and authenticate access to system components (MFA required for remote access and all admin access)
- Req 9: Restrict physical access to cardholder data

**Regularly Monitor and Test Networks**
- Req 10: Log and monitor all access to system components and cardholder data
- Req 11: Test security of systems and networks regularly (pen testing, vulnerability scanning, IDS/IPS)

**Maintain an Information Security Policy**
- Req 12: Support information security with organizational policies and programs

---

## Common Financial Account Attack Types

### Account Takeover (ATO)
**How it happens:** Attackers use stolen credentials (from phishing, data breaches, or credential stuffing) to log into financial accounts.
**Signs:** Login from unusual location/device, password change you didn't make, new payee added, suspicious transactions.
**Prevention:** Strong unique passwords + MFA + account alerts for all transactions.

### SIM Swapping
**How it happens:** Attacker convinces your mobile carrier to transfer your phone number to their SIM card, then resets passwords via SMS.
**Signs:** Suddenly losing cell service, receiving unexpected texts about account changes.
**Prevention:** Add a PIN/passcode with your carrier, use app-based MFA instead of SMS MFA, set up account alerts.

### Wire Fraud / Business Email Compromise (BEC)
**How it happens:** Attacker impersonates a trusted party (CEO, vendor, lawyer) via email to trick someone into wiring funds to attacker's account.
**Prevention:** Always verify wire transfer requests via a known phone number (not one in the email). Establish a verbal confirmation policy for all transfers.

### Check Fraud
**How it happens:** Checks are stolen from mail or altered using chemical washing.
**Prevention:** Use electronic payments where possible, use security-featured checks, monitor accounts daily, use USPS Informed Delivery.

### Zelle/Venmo/CashApp Scams
**How it happens:** Scammers impersonate banks warning of fraud, then trick victims into sending money to "safe accounts."
**Key fact:** Banks will NEVER ask you to send money via Zelle to protect yourself from fraud. Hang up and call the number on your card.
