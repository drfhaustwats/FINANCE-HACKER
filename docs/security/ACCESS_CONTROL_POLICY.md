# Access Control Policy

Document owner: `[[Security Owner Name]]`  
Version: `1.0`  
Effective date: `[[YYYY-MM-DD]]`  
Next review date: `[[YYYY-MM-DD]]`

## 1. Purpose

Define controls for granting, managing, reviewing, and revoking access to systems and data.

## 2. Principles

- Least privilege
- Need-to-know access
- Separation of duties where practical
- Strong authentication for privileged access

## 3. Identity Management

- Every user must have a unique account.
- Shared credentials are prohibited for production access.
- Service accounts must be documented with owner, purpose, and rotation schedule.

## 4. Authentication Requirements

- MFA is required for:
  - Source code hosting and CI/CD administration
  - Cloud infrastructure administration
  - Database and secret management consoles
  - Any administrative dashboard containing customer financial data
- Passwords must meet minimum complexity and length requirements in managed identity providers.

## 5. Authorization Requirements

- Access requests must be approved by an authorized manager or system owner.
- Role-based access is preferred over direct user-level permissions.
- Privileged roles are restricted to approved personnel and reviewed quarterly.

## 6. Provisioning

- New access requires a documented business justification.
- Access must be limited to required environment(s): dev, staging, production.
- Access grants must be logged.

## 7. Deprovisioning

- Access must be revoked on termination the same day.
- Access must be adjusted within one business day for role changes.
- Unused or stale privileged accounts must be removed.

## 8. Access Reviews

- Quarterly review of privileged access to production systems.
- Semi-annual review of all active user accounts.
- Review evidence includes reviewer, date, and actions taken.

## 9. Third-Party Access

- Vendor access requires contract and security review.
- Vendor access is time-bounded and scoped.
- Vendor sessions must use MFA and be disabled when no longer required.

## 10. Logging and Audit

- Authentication events and privileged actions should be logged where supported.
- Audit logs are retained according to retention policy.

## 11. Exceptions

Exceptions require written approval from the Security Owner with compensating controls and expiration date.

