# Incident Response Plan

Document owner: `[[Security Owner Name]]`  
Version: `1.0`  
Effective date: `[[YYYY-MM-DD]]`  
Next review date: `[[YYYY-MM-DD]]`

## 1. Purpose

Provide a repeatable process to detect, contain, investigate, eradicate, and recover from security incidents.

## 2. Incident Severity Levels

- `SEV-1` Critical: Confirmed compromise, unauthorized data access, or major service impact.
- `SEV-2` High: Credible security event with potential data exposure or material operational risk.
- `SEV-3` Medium: Suspicious activity with limited scope or no confirmed impact.
- `SEV-4` Low: Minor issue, policy violation, or informational event.

## 3. Response Team

- Incident Commander: `[[Name/Role]]`
- Security Lead: `[[Name/Role]]`
- Engineering Lead: `[[Name/Role]]`
- Communications Lead: `[[Name/Role]]`
- Legal/Privacy Contact: `[[Name/Role]]`

Primary contact email: `[[security@company.com]]`

## 4. Response Lifecycle

### 4.1 Detection and Triage

- Receive alert or report.
- Open incident record with timestamp, source, and initial scope.
- Assign severity and incident owner.

### 4.2 Containment

- Revoke exposed credentials and rotate secrets.
- Isolate affected systems or accounts.
- Block malicious traffic or sessions.

### 4.3 Investigation

- Collect relevant logs, indicators, and timeline.
- Determine root cause, affected assets, and data scope.
- Preserve evidence for legal/compliance review.

### 4.4 Eradication and Recovery

- Remove malicious artifacts and close attack paths.
- Patch vulnerabilities and deploy remediations.
- Validate system integrity before restoring normal operations.

### 4.5 Post-Incident Activities

- Complete postmortem within `[[5]]` business days for SEV-1/SEV-2.
- Define corrective actions with owners and due dates.
- Update policies, runbooks, and monitoring as needed.

## 5. Notification and Escalation

- Internal stakeholders notified immediately for SEV-1/SEV-2 incidents.
- External notifications are handled according to legal and contractual obligations.
- If third-party providers are impacted, notify according to contract terms.

## 6. Communication Requirements

- Use approved channels only.
- Avoid sharing sensitive details in public channels.
- Maintain a chronological incident log.

## 7. Testing and Readiness

- Conduct at least one tabletop security incident exercise annually.
- Review response metrics and improve runbooks after each exercise.

## 8. Records Retention

- Incident records, timelines, and postmortems are retained per retention policy.

