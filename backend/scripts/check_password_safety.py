"""Screen a proposed provisioning password without creating or changing an account."""
from getpass import getpass
from hashlib import sha1
import re
from urllib.request import Request, urlopen


def is_compromised(password: str) -> bool:
    # SHA-1 is used only for the provider's range protocol, never password storage.
    digest = sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    request = Request(
        "https://api.pwnedpasswords.com/range/" + digest[:5],
        headers={"Add-Padding": "true", "User-Agent": "PESLC-Password-Screening"},
    )
    with urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise ValueError("Screening unavailable")
        body = response.read(1_000_001)
    if len(body) > 1_000_000:
        raise ValueError("Invalid screening response")
    found = False
    for line in body.decode("ascii").strip().splitlines():
        match = re.fullmatch(r"([A-Fa-f0-9]{35}):([0-9]+)", line)
        if not match:
            raise ValueError("Invalid screening response")
        if match[1].upper() == digest[5:] and any(c != "0" for c in match[2]):
            found = True
    if not body.strip():
        raise ValueError("Empty screening response")
    return found


def main() -> int:
    password = getpass("Proposed password (hidden): ")
    if len(password) < 12:
        print("Use at least 12 characters. Do not provision this password.")
        return 1
    try:
        compromised = is_compromised(password)
    except Exception:
        print("Screening unavailable. Do not provision this password until the check completes.")
        return 2
    finally:
        password = ""
    if compromised:
        print("Found in known breaches. Choose a different, unique password.")
        return 1
    print("Not found in the checked Pwned Passwords data. This is not a guarantee of password safety.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
