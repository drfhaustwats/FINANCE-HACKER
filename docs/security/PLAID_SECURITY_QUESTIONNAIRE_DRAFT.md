# Plaid Security Questionnaire Draft Answers

Use this only after confirming controls are implemented. Replace placeholders before submission.

## 1) Security contact information

`[[Full Name]]`, `[[Title]]`, `[[Email]]`  
Monitored group email: `[[security@company.com]]`

## 2) Documented policy and operational program

Recommended selection: `Yes`

Supporting statement:

`[[Company Name]]` maintains documented security policies and operational procedures to identify, mitigate, and monitor information security risks. Policies cover governance, access control, incident response, vulnerability management, and data retention/deletion. Controls are reviewed at least annually and after material system changes.

Attach:

- `INFORMATION_SECURITY_POLICY.md`
- `SECURITY_OPERATIONS_PROCEDURE.md`

## 3) Access controls for production assets and sensitive data

Recommended selections (only if true):

- Least privilege / role-based access control
- Unique user accounts (no shared credentials)
- MFA for privileged/admin access
- Access logging and periodic access reviews
- Timely deprovisioning for role changes/termination

Attach:

- `ACCESS_CONTROL_POLICY.md`

## 4) Consumer MFA before Plaid Link

Selection guidance:

- Choose `Yes` only if your user authentication flow enforces MFA before account linking.
- If not yet enforced, choose `No` and provide target implementation date.

Suggested `No` remediation statement (if needed):

Consumer MFA is in progress and is scheduled for implementation by `[[YYYY-MM-DD]]` before production launch to general users.

## 5) MFA for critical systems storing/processing financial data

Recommended selection: `Yes`

Supporting statement:

MFA is required for administrative access to production infrastructure, source control, CI/CD, and data systems that process consumer financial data.

## 6) Encryption in transit (TLS 1.2+)

Recommended selection: `Yes`

Supporting statement:

All client-to-server and service-to-service communications carrying sensitive data use TLS 1.2 or better.

## 7) Encryption at rest

Recommended selection: `Yes`

Supporting statement:

Consumer data is encrypted at rest in production databases and storage services using managed encryption controls.

## 8) Vulnerability management

Recommended selections (only if true):

- Automated dependency scanning
- Endpoint vulnerability/patch management
- Infrastructure vulnerability scanning
- Defined remediation timelines by severity

Attach:

- `VULNERABILITY_MANAGEMENT_POLICY.md`

## 9) Privacy policy

Recommended selection: `Yes`

Link: `[[https://your-domain.com/privacy]]`

Attach optional:

- `../legal/PRIVACY_POLICY_TEMPLATE.md` (if no published URL yet)

## 10) Consumer consent for data collection/processing/storage

Recommended selection: `Yes`

Supporting statement:

Users are presented with consent disclosures before connecting accounts and before ongoing processing and storage of their financial data.

## 11) Data retention and deletion policy

Recommended selection: `Yes`

Supporting statement:

`[[Company Name]]` maintains and enforces a documented retention and deletion policy, including account deletion handling and periodic policy review to align with applicable privacy requirements.

Attach:

- `DATA_RETENTION_DELETION_POLICY.md`

