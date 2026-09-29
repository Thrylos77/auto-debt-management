# TLS-CCA — Authentication lifecycle

## Principles

TLS-CCA uses password + Authenticator (TOTP) as the normal authentication pair. Email is used for invitation, password-recovery and security notifications; it is not an alternative second factor for normal login. Recovery codes are not part of the authentication contract.

## Account onboarding

```text
Admin creates account
        ↓
INVITED
        ↓
Invitation email
        ↓
User sets password
        ↓
PASSWORD_SET
        ↓
Authenticator enrollment
        ↓
First valid TOTP
        ↓
ACTIVE
```

No normal access token or application session is issued before the first successful TOTP verification.

### Endpoints

- `POST /api/v1/auth/invitation/accept/` — define the password and receive the temporary TOTP setup payload.
- `POST /api/v1/auth/invitation/verify-2fa/` — validate the first TOTP and create the initial session.
- `POST /api/v1/auth/2fa/enroll/verify/` — complete mandatory enrollment for an existing account that has no TOTP yet.

## Normal login

```text
Password
   ↓
TOTP challenge
   ↓
Authenticator code
   ↓
Access + refresh tokens
```

The password endpoint never returns tokens by itself. The TOTP verification step is the token-issuing step.

## Change own password

An authenticated user must provide:

- current password;
- new password;
- current TOTP code.

Changing the password revokes every existing session, including the session used for the change. The user signs in again after the change.

## Forgot password

For an ordinary active account with TOTP enabled:

```text
Forgot password
      ↓
security email with single-use link
      ↓
reset link + current TOTP
      ↓
new password
      ↓
all sessions revoked
```

The reset link is opaque, single-use and time-limited. A successful reset never automatically logs the user in.

Privileged accounts (`is_staff` / `is_superuser`) do not use this self-service route.

## Administrator-triggered password reset

A `USER_ADMIN` or `SECURITY_ADMIN` can trigger a reset through `user.security.reset_password`. The administrator does not set or see the new password. The user receives the one-time link and chooses the password.

The operation is audited and all previous sessions are revoked when the password is actually changed.

## Authenticator recovery

A `SECURITY_ADMIN` can use `user.security.reset_2fa`. The operation:

1. disables the current TOTP secret;
2. invalidates outstanding TOTP setup/challenge tokens;
3. revokes all active sessions;
4. puts the account back into `PASSWORD_SET`;
5. generates a new temporary enrollment setup;
6. emails the recovery enrollment link.

The user completes the new enrollment with a valid TOTP. Tokens are issued only after that validation.

## Lost password + lost Authenticator

The two administrative actions are intentionally separate:

```text
Security Admin
   ├── reset password → user chooses new password
   └── reset 2FA      → user enrolls a new Authenticator
```

This does not create an email-based login bypass. The account becomes `ACTIVE` only when the password is usable and a new Authenticator enrollment has been successfully verified.

## Roles and permissions

| Role | `user.security.reset_password` | `user.security.reset_2fa` |
|---|---:|---:|
| `USER_ADMIN` | yes | no |
| `SECURITY_ADMIN` | yes | yes |
| Standard business roles | no | no |

The direct manager/business-role concept does not automatically inherit credential-recovery permissions.

## Security properties

- security tokens are generated with cryptographically secure randomness;
- only token hashes are persisted for invitations, password resets and TOTP challenges;
- TOTP secrets are encrypted at rest;
- production requires a dedicated Fernet TOTP encryption key;
- login, TOTP and password-reset endpoints are rate-limited;
- JWT authentication and refresh require an active account that has completed TOTP enrollment;
- password and 2FA security actions revoke sessions and emit audit events;
- reset and invitation tokens expire and are single-use;
- authentication-security notifications cannot be disabled through ordinary notification preferences.

## Future evolution

WebAuthn/passkeys can be added later as a phishing-resistant MFA mechanism without changing the administrative recovery separation established here.
