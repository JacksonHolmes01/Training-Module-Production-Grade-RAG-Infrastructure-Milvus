# Consumer Cybersecurity Incident Response Guide

Practical guidance for individuals facing common cybersecurity incidents.

---

## SCENARIO: My Online Bank Account Was Hacked

### Immediate Steps (Do These Now)
1. **Call your bank immediately** — Use the number on the back of your card or official website, NOT a number from a suspicious email. Report the compromise and ask them to freeze/lock your account.
2. **Change your password right now** — Use a strong, unique password you haven't used elsewhere. Do this from a device you trust (not the one that may be compromised).
3. **Enable Multi-Factor Authentication (MFA)** — If not already enabled, turn it on immediately (use an authenticator app, not SMS if possible).
4. **Review all recent transactions** — Look for any unauthorized transactions and report every one to your bank.
5. **Check for new payees or transfers** — Attackers often add themselves as a payee or set up recurring transfers.
6. **Change your email account password too** — Attackers often compromise email first to take over financial accounts via password reset.

### What Your Bank Will Do
- Freeze fraudulent transactions
- Issue you a new account number or card
- Investigate unauthorized transactions
- Likely reimburse fraudulent charges (most banks have zero liability policies)

### Next Steps (Within 24-48 Hours)
- **File a report with the FTC:** IdentityTheft.gov
- **Check your credit report:** AnnualCreditReport.com (all three bureaus — Experian, Equifax, TransUnion)
- **Consider a credit freeze:** Contact each bureau to freeze your credit to prevent new accounts being opened.
- **Check other financial accounts** — Change passwords on any other accounts using the same email/password combination.
- **Report to the FBI IC3:** ic3.gov if you lost money

### Helpful Resources
- FTC Identity Theft: IdentityTheft.gov
- FBI Internet Crime Complaint Center: ic3.gov
- Consumer Financial Protection Bureau: consumerfinance.gov
- AnnualCreditReport.com for free credit reports

---

## SCENARIO: I Received a Phishing Email

### How to Identify a Phishing Email
- Urgent language ("Your account will be closed in 24 hours!")
- Generic greetings ("Dear Customer" instead of your name)
- Mismatched or suspicious sender email address
- Links that don't match the displayed text (hover to check)
- Requests for personal information, passwords, or payment
- Unexpected attachments
- Poor grammar and spelling (though sophisticated attacks are well-written)

### What to Do
1. **Do NOT click any links** or open any attachments.
2. **Do NOT reply** to the email.
3. **Report it:**
   - Forward to your email provider's spam/phishing reporting address
   - Forward phishing emails to: reportphishing@apwg.org
   - If it impersonates a company, report to that company's security team
   - Report to the FTC: ReportFraud.ftc.gov
4. **Delete the email.**
5. **If you already clicked a link** — see the "I Clicked a Phishing Link" scenario below.

### If the Phishing Email Claimed to Be From Your Bank
- Do not use any contact information in the email.
- Go directly to your bank's official website (type it yourself) or call the number on your card.
- Report the phishing attempt to your bank's fraud team.

---

## SCENARIO: I Clicked a Phishing Link / Entered My Password on a Fake Site

### Immediate Steps
1. **Change the password immediately** for the account that was targeted.
2. **Change the password on any other accounts using the same password** — password reuse is the #1 way one breach leads to many.
3. **Enable MFA** on the compromised account and all important accounts.
4. **Check if your email was compromised** — If the phishing targeted your email, change the password and check for:
   - Forwarding rules (attackers set these to silently receive all your email)
   - Connected/authorized apps
   - Changes to recovery email/phone
5. **Run a malware scan** on the device you clicked from.
6. **Check haveibeenpwned.com** to see if your email appears in known data breaches.

### If the Site Captured Financial Information
- Contact your bank or card issuer immediately to report potential fraud.
- Request a new card number.
- Monitor your accounts closely.

---

## SCENARIO: My Password Was Leaked in a Data Breach

### How to Find Out If You Were Breached
- Check haveibeenpwned.com (enter your email address)
- Enable breach alerts — haveibeenpwned.com offers free email notifications
- Check if the company that was breached notified you (they are legally required to in most states)

### What to Do
1. **Change the password** on the breached service immediately.
2. **Change the same password everywhere else you used it** — This is critical. Use a password manager to find all accounts using that password.
3. **Enable MFA** on the breached account.
4. **Be alert for phishing** — Attackers buy breached credentials and use them to craft targeted phishing attacks.
5. **Monitor your financial accounts** — If financial credentials were involved.
6. **Consider a credit freeze** if the breach included sensitive personal information (SSN, DOB, address).

### Best Practices Going Forward
- Use a password manager (Bitwarden, 1Password, LastPass) to generate and store unique passwords for every site.
- Never reuse passwords.
- Enable MFA everywhere possible.
- Use an email alias service to limit exposure of your real email.

---

## SCENARIO: My Computer May Have Malware / Ransomware

### Signs Your Computer May Be Infected
- Unusually slow performance
- Pop-up ads appearing constantly
- Your browser homepage changed without your permission
- Files are encrypted or have strange extensions (ransomware)
- Antivirus is disabled or won't start
- Unusual network activity
- Programs you didn't install appearing
- Ransom note appearing on screen

### Immediate Steps
1. **Disconnect from the internet** (unplug ethernet cable and/or disable WiFi) — this prevents the malware from communicating with attackers or spreading.
2. **Do not shut down if ransomware** — Some encryption can be stopped if caught mid-process; memory forensics may also help.
3. **Do not pay ransomware demands** — It does not guarantee your files will be decrypted.
4. **Run a reputable antivirus/antimalware scan** — Use Malwarebytes, Windows Defender, or similar.
5. **For ransomware — check NoMoreRansom.org** — Free decryption tools exist for many ransomware strains.
6. **Restore from backup** — If you have clean backups, restore from them after cleaning the system.
7. **Report ransomware** to CISA (report.cisa.gov) and FBI (ic3.gov).

### After Cleanup
- Change passwords for all accounts accessed from the infected device.
- Enable MFA on all accounts.
- Update all software.
- Ensure you have backups going forward (follow 3-2-1 rule: 3 copies, 2 different media, 1 offsite).

---

## SCENARIO: My Social Security Number Was Stolen / Identity Theft

### Immediate Steps
1. **Place a fraud alert** with one of the three credit bureaus (they notify the others automatically):
   - Equifax: 1-800-525-6285
   - Experian: 1-888-397-3742
   - TransUnion: 1-800-680-7289
2. **Place a credit freeze** (stronger than fraud alert) with all three bureaus — prevents new credit being opened in your name.
3. **Get free credit reports** at AnnualCreditReport.com — review for accounts you didn't open.
4. **File an identity theft report** at IdentityTheft.gov — creates an official FTC report and personal recovery plan.
5. **File a police report** — Required by some creditors when disputing fraudulent accounts.
6. **Report to Social Security Administration** if your SSN was misused: ssa.gov/fraud

### Ongoing Monitoring
- Monitor your credit reports regularly.
- Set up free credit monitoring (many banks offer this).
- Keep copies of all reports and correspondence.
- Check your IRS account (irs.gov) for unauthorized tax filings.
- Check your Social Security earnings record for unauthorized use.

---

## SCENARIO: My Email Account Was Hacked

### Immediate Steps
1. **Recover access** using your provider's account recovery process.
2. **Change your password** immediately to something strong and unique.
3. **Enable MFA** — This is the single most important thing you can do.
4. **Check and remove unauthorized:**
   - Forwarding rules (attackers use these to silently monitor your email)
   - Connected apps and services
   - Recovery phone numbers and email addresses (attackers change these for lockout)
   - Active sessions (sign out all other sessions)
5. **Check what the attacker may have accessed** — review sent folder for emails sent in your name.
6. **Alert your contacts** — The attacker may have sent phishing emails to your contacts pretending to be you.
7. **Change passwords on accounts using this email** — especially financial accounts and other critical services.

---

## SCENARIO: My Phone Was Stolen

### Immediate Steps
1. **Remotely lock or wipe the device:**
   - iPhone: icloud.com/find (Find My)
   - Android: android.com/find (Find My Device)
2. **Call your carrier** to suspend service on the stolen number.
3. **Change passwords** on critical accounts accessible from the phone (email, banking, etc.).
4. **Revoke trusted device status** for the phone in your account settings.
5. **Alert your bank** in case the attacker attempts to use banking apps or SMS codes.
6. **File a police report** — Required for insurance claims.
7. **Report to FCC** if needed: consumercomplaints.fcc.gov

### If MFA Was SMS-Based
- Attackers with your phone number can intercept SMS codes.
- Switch to app-based MFA (Google Authenticator, Authy) as soon as possible.
- Notify your carrier about potential SIM swap fraud.

---

## SCENARIO: I Think I'm Being Scammed (Tech Support Scam, Romance Scam, etc.)

### Warning Signs of Common Scams
- **Tech support scam:** Pop-up saying your computer is infected, asking you to call a number or install software. Microsoft and Apple will NEVER call you unsolicited.
- **Romance scam:** Online relationship where the person always has an excuse not to meet and eventually asks for money.
- **Gift card scam:** Anyone asking you to pay with gift cards is scamming you — no legitimate business or government agency accepts gift cards as payment.
- **IRS/Government scam:** The IRS contacts you by mail first, never by threatening phone call demanding immediate payment.
- **Lottery/Prize scam:** You can't win a lottery you didn't enter. Legitimate prizes don't require upfront fees.

### What to Do
1. **Stop all communication** with the suspected scammer.
2. **Do not send money** — If you already have, contact your bank or wire transfer service immediately to attempt to recall the transfer.
3. **Report it:**
   - FTC: ReportFraud.ftc.gov
   - FBI IC3: ic3.gov
   - If investment fraud: SEC at sec.gov/tcr
4. **Do not try to get your money back yourself** — "Recovery scammers" target previous scam victims.

---

## General Cybersecurity Best Practices for Individuals

### Password Security
- Use a password manager (Bitwarden is free and open source)
- Every account gets a unique, randomly generated password
- Minimum 16 characters where possible

### Multi-Factor Authentication (MFA)
- Enable MFA on every account that supports it
- Priority: email, banking, social media, work accounts
- Use an authenticator app (not SMS) where possible
- Store backup codes securely offline

### Device Security
- Keep operating system and apps updated — updates patch security vulnerabilities
- Use full-disk encryption (FileVault on Mac, BitLocker on Windows)
- Use a VPN on public WiFi
- Lock your device with a PIN/biometric

### Online Safety
- Only shop on sites with HTTPS (padlock in browser)
- Don't click links in unsolicited emails — go directly to the website
- Verify requests for sensitive information by calling the organization directly
- Check haveibeenpwned.com periodically for your email addresses

### Data Backup
- Follow the 3-2-1 backup rule: 3 copies, 2 different media, 1 offsite/cloud
- Test your backups by actually restoring from them periodically
