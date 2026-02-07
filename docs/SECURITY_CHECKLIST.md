# Security Checklist: AI Proctored Exam Platform

**Status:** DRAFT
**Version:** 1.0

## 1. Authentication & Authorization
- [x] **JWT Implementation:** Ensure `flask-jwt-extended` is used with a strong `JWT_SECRET_KEY`.
- [ ] **Token Expiry:** Verify access tokens expire in < 1 hour; Refresh tokens in < 24 hours.
- [ ] **Password Hashing:** Confirm `bcrypt` or `Argon2` is used for all user passwords.
- [ ] **Role-Based Access:** Verify `/api/admin` endpoints strictly enforce `user_role == 'admin'`.

## 2. Infrastructure Security
- [ ] **HTTPS Enforcement:** Production deployment must force SSL/TLS.
- [ ] **CORS Policy:** Restrict `CORS_ORIGINS` to trusted frontend domains (no `*`).
- [ ] **Environment Variables:**
    - `FLASK_ENV` set to `production`.
    - `GEMINI_API_KEY` loaded from secure vault/env, NEVER committed.
    - `JWT_SECRET_KEY` is high-entropy (min 32 chars).

## 3. Data Protection
- [ ] **Database Encryption:** Ensure `exam_platform.db` resides on an encrypted volume.
- [ ] **Log Sanitization:** Check `suspicion_log.json` and server logs for PII (Personal Identifiable Information) leaks.
- [ ] **Input Validation:**
    - File Uploads: Validate PDF/DOCX magic numbers, not just extensions.
    - SQL Injection: Ensure all `DatabaseManager` queries use parameterized inputs.

## 4. API Security
- [ ] **Rate Limiting:** Implement `Flask-Limiter` on `/api/login` and `/api/register` (e.g., 5 req/min).
- [ ] **Payload Limits:** Restrict upload size to 10MB to prevent DoS.
- [ ] **Socket Security:** Validate `session_id` on all WebSocket events.

## 5. Deployment Verified
- [ ] **Dependency Scan:** Run `safety check` or `pip-audit` on `requirements.txt`.
- [ ] **Debug Mode:** Ensure `debug=False` in `app.run()`.
