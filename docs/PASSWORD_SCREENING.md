# Password screening

The password-reset form screens a submitted new password against the free
[Have I Been Pwned Pwned Passwords range API](https://haveibeenpwned.com/API/v3#PwnedPasswords).
It sends only the first five hexadecimal characters of a locally computed SHA-1
hash over HTTPS, requests padded results and compares suffixes locally. SHA-1 is
used for this lookup protocol, not credential storage. Supabase retains responsibility
for authentication and password storage.

The form checks once on submission, not while the user types. A breach match blocks
the update. A failed, timed-out or malformed response also blocks the update and
allows retry. A nonmatch means only that the password was not found in the checked
data; it does not establish that a password can never be compromised. No password,
complete hash or provider response is written to application logs or persistent state.

For controlled account provisioning, the operator can screen a proposed password
before creating or resetting the approved account:

```powershell
cd backend
python scripts/check_password_safety.py
```

The prompt hides input. Do not supply passwords in command arguments, chat,
screenshots or shared files. Exit 0 means no match; 1 means a short or breached
password; 2 means the check did not complete. Provision only after a completed
nonmatching check. The command itself never creates accounts, changes roles or
updates credentials. Prefer letting the account owner select their password using
the existing approved recovery process.

This is an application safeguard and controlled provisioning procedure, not globally
enforced Supabase Auth policy. Direct Supabase password-update requests can bypass
the form. It does not enable the provider's paid integrated leaked-password feature,
remove its advisory, scan existing stored credentials, or claim comprehensive password
security. No existing password or original UAT response is changed by this addition.

Targeted verification covers lookup privacy, padded/malformed responses, network
failure, timeout, blocked updates, retries, successful updates and unchanged
authentication behavior. Analytics and model evaluation remain separate.
