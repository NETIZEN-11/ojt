# Security Checklist

## Pre-Deployment Checklist

### Infrastructure
- [ ] TLS 1.3 enforced on all external endpoints
- [ ] mTLS enabled for internal service communication
- [ ] Network policies applied (default deny)
- [ ] WAF configured with OWASP CRS
- [ ] DDoS protection enabled
- [ ] Private endpoints for databases/cache
- [ ] Security groups restrict to minimum ports

### Secrets Management
- [ ] No secrets in code, config, or Docker images
- [ ] All secrets in Vault/Secrets Manager
- [ ] JWT keys: RSA 2048+, RS256, rotated quarterly
- [ ] Database passwords: 32+ chars, rotated monthly
- [ ] API keys: Provider-specific, least privilege
- [ ] Encryption keys: KMS-managed, auto-rotated
- [ ] No default credentials in any environment

### Authentication & Authorization
- [ ] JWT: RS256, 30min access, 7d refresh, rotating
- [ ] MFA enforced for admin accounts
- [ ] RBAC: 6 roles, least privilege principle
- [ ] Session management: Secure, HttpOnly, SameSite
- [ ] Password policy: 12+ chars, bcrypt, breach check
- [ ] Account lockout: 5 failed attempts, 15min lockout
- [ ] OAuth/OIDC: PKCE, state parameter, validated redirect

### Data Protection
- [ ] Encryption at rest: AES-256 (DB, Redis, S3)
- [ ] Encryption in transit: TLS 1.3 everywhere
- [ ] PII detection: Enabled, auto-redaction
- [ ] Data classification: Applied to all tables/columns
- [ ] Retention policies: Configured and enforced
- [ ] Backup encryption: Separate keys, tested restores
- [ ] Key management: HSM/KMS, separate from app

### Application Security
- [ ] Input validation: Pydantic v2 strict schemas
- [ ] Output encoding: JSON only, no template injection
- [ ] SQL injection: ORM only, no raw queries
- [ ] XSS: Content-Type headers, CSP, sanitization
- [ ] CSRF: SameSite cookies, CSRF tokens for forms
- [ ] SSRF: URL allowlist, private IP blocking, DNS rebinding protection
- [ ] File upload: Type validation, size limits, scanning
- [ ] Rate limiting: Per-endpoint, per-user, global
- [ ] CORS: Explicit allowlist, no wildcards
- [ ] Security headers: HSTS, X-Frame-Options, X-Content-Type-Options

### Dependencies
- [ ] Python: pip-audit, bandit, safety in CI
- [ ] Node.js: npm audit, Snyk in CI
- [ ] Containers: Trivy/Docker scan in CI
- [ ] SBOM: Generated for each release
- [ ] Pinning: Exact versions, no "latest"
- [ ] Updates: Automated PRs for security patches

### Monitoring & Logging
- [ ] Structured logging: JSON, correlation IDs
- [ ] No secrets/PII in logs (verified)
- [ ] Audit logs: Immutable, 7yr retention
- [ ] Metrics: Latency, errors, queue depth, cost
- [ ] Alerts: Error rate, latency, queue, cost, security events
- [ ] Distributed tracing: OpenTelemetry, 10% sampling
- [ ] Log aggregation: Centralized, searchable
- [ ] Log retention: 90 days hot, 7yr cold

### Incident Response
- [ ] Runbook: Documented, accessible, tested
- [ ] Playbooks: Data breach, privilege escalation, DoS
- [ ] Contacts: On-call rotation, escalation paths
- [ ] Communications: Slack, email, status page
- [ ] Evidence preservation: Chain of custody
- [ ] Post-incident: RCA, action items, follow-up

### Compliance
- [ ] SOC 2: Controls mapped, evidence collected
- [ ] GDPR: DPIA, data subject rights, breach notification
- [ ] ISO 27001: ISMS, risk register, treatment plan
- [ ] NIST CSF: Identify, Protect, Detect, Respond, Recover
- [ ] Penetration test: Annual, third-party
- [ ] Vulnerability scan: Weekly automated, monthly manual

## CI/CD Security

### Pipeline
- [ ] Branch protection: Required reviews, status checks
- [ ] Signed commits: GPG verification
- [ ] Dependency scan: Every PR, scheduled daily
- [ ] Secret scan: Every commit, pre-commit hook
- [ ] SAST: CodeQL/SonarQube on every PR
- [ ] Container scan: Base image + app layers
- [ ] DAST: Staging environment, scheduled
- [ ] Policy enforcement: OPA/Gatekeeper

### Build
- [ ] Reproducible builds: Fixed base images, pinned deps
- [ ] Minimal images: Distroless/Alpine, non-root
- [ ] Multi-stage: Build → Test → Runtime
- [ ] Image signing: Cosign/Notary, verified on deploy
- [ ] Provenance: SLSA Level 2+

### Deploy
- [ ] Immutable deployments: No in-place updates
- [ ] Canary/Blue-green: Automated rollout
- [ ] Health checks: Liveness, readiness, startup
- [ ] Rollback: Automated on metric degradation
- [ ] Approval gates: Manual for production
- [ ] Audit trail: Deployments logged with author/commit

## Operational Security

### Access Control
- [ ] Bastion host/SSM for SSH access
- [ ] Just-in-time access for production
- [ ] Break-glass procedure for emergencies
- [ ] Regular access reviews (quarterly)
- [ ] Service accounts: Minimum permissions
- [ ] No shared credentials

### Vulnerability Management
- [ ] Scanner: Trivy, Nessus, or equivalent
- [ ] Schedule: Daily container, weekly host
- [ ] SLA: Critical 24h, High 72h, Medium 30d
- [ ] Exception process: Documented, time-bound, approved
- [ ] Patch testing: Staging before production

### Backup & Recovery
- [ ] RPO: ≤ 24 hours (daily pg_dump + WAL)
- [ ] RTO: ≤ 4 hours (tested monthly)
- [ ] Encryption: Separate keys, off-site
- [ ] Verification: Automated restore test weekly
- [ ] Point-in-time: WAL archiving for PITR
- [ ] Cross-region: Backup replication

### Disaster Recovery
- [ ] DR plan: Documented, tested quarterly
- [ ] RTO/RPO targets defined and met
- [ ] Failover: Automated or < 30min manual
- [ ] Data integrity: Checksums, verification
- [ ] Communication: Stakeholder notification plan

## Security Testing

### Automated
- [ ] Unit tests: Security-focused (auth, validation, SSRF)
- [ ] Integration tests: Auth bypass, RBAC, injection
- [ ] Contract tests: API schema validation
- [ ] Property tests: Edge cases, fuzzing
- [ ] Dependency tests: License, vulnerability, maintenance

### Manual
- [ ] Penetration test: Annual, third-party
- [ ] Red team exercise: Annual, scoped
- [ ] Code review: Security-focused, mandatory
- [ ] Architecture review: New features, major changes
- [ ] Threat model: Updated per release

### Specialized
- [ ] LLM security: Prompt injection, jailbreak, extraction
- [ ] Target agent: SSRF, injection, DoS
- [ ] Data pipeline: PII handling, redaction
- [ ] Cost controls: Budget enforcement, abuse

## Release Checklist

### Pre-Release
- [ ] All CI checks pass
- [ ] Security scans clean
- [ ] Dependencies updated
- [ ] Changelog includes security fixes
- [ ] Migration tested (up/down)
- [ ] Rollback plan documented
- [ ] Stakeholder sign-off

### Release Day
- [ ] Deploy during low-traffic window
- [ ] Monitoring elevated
- [ ] On-call confirmed
- [ ] Rollback tested in staging
- [ ] Communications sent

### Post-Release
- [ ] Health checks verified
- [ ] Metrics normal
- [ ] Error rates baseline
- [ ] Security events monitored
- [ ] Post-deploy review (24h)

## Quarterly Review

### Access Review
- [ ] User accounts: Active, roles correct
- [ ] Service accounts: Minimum permissions
- [ ] API keys: Rotated, usage reviewed
- [ ] Admin accounts: MFA, activity logged

### Configuration Review
- [ ] Network policies: Current, minimal
- [ ] Security groups: Least privilege
- [ ] Encryption: Algorithms current
- [ ] Certificates: Valid > 90 days
- [ ] Secrets: Rotated per schedule

### Process Review
- [ ] Incident response: Drills conducted
- [ ] Backup restore: Tested successfully
- [ ] Dependency updates: Applied
- [ ] Training: Security awareness completed
- [ ] Compliance: Evidence collected

## Annual Audit

### Internal
- [ ] Full configuration audit
- [ ] Access control audit
- [ ] Encryption verification
- [ ] Logging completeness
- [ ] Backup restore drill
- [ ] DR failover test
- [ ] Penetration test results reviewed
- [ ] Vendor security assessments

### External
- [ ] SOC 2 Type II audit
- [ ] Penetration test (third-party)
- [ ] Compliance certifications renewed
- [ ] Insurance review
- [ ] Legal/regulatory updates