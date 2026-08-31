# Data Retention and Deletion Policy

Document owner: `[[Privacy/Security Owner Name]]`  
Version: `1.0`  
Effective date: `[[YYYY-MM-DD]]`  
Next review date: `[[YYYY-MM-DD]]`

## 1. Purpose

Define how `[[Company Name]]` retains and deletes customer and operational data in compliance with contractual, legal, and privacy obligations.

## 2. Data Categories

- Account and profile data
- Financial transaction data
- Authentication and security logs
- Support records
- Backups and disaster recovery copies

## 3. Retention Principles

- Retain only data required for service delivery, security, compliance, and legal obligations.
- Minimize long-term storage of sensitive data where not required.
- Apply retention periods consistently across primary systems and backups.

## 4. Retention Schedule (Template)

- Customer account data: retained while account is active.
- Transaction data: retained while account is active, then deleted or anonymized within `[[X days]]` after verified account closure unless legally required.
- Security/audit logs: retained for `[[12-24 months]]`.
- Support records: retained for `[[12-24 months]]`.
- Backup data: rolling retention `[[30-90 days]]` with automatic expiry.

## 5. Consumer Deletion Requests

- Verified user deletion requests are processed within `[[30 days]]` unless legal hold applies.
- Deletion workflow includes:
  - Primary data stores
  - Cached copies where practical
  - Linked identifiers and tokens
  - Third-party processor deletion where required
- Deletion actions are logged for audit.

## 6. Token and Secret Handling

- Sensitive tokens (such as Plaid access tokens) are stored server-side only.
- Tokens are deleted when no longer required or when account disconnect/deletion is requested.

## 7. Legal Holds and Exceptions

- If data must be preserved for legal, fraud, or regulatory reasons, deletion may be paused.
- Any hold must be documented, approved, and periodically reviewed.

## 8. Review and Enforcement

- This policy is reviewed at least annually.
- Non-compliance may result in corrective action and process changes.

