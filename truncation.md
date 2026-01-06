# Truncation Vulnerability Guide

A practical guide for understanding Truncation vulnerabilities—where data is cut short due to fixed limits or terminator characters, changing the meaning or validity of the remaining data.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [Null Byte Truncation](#null-byte-truncation)
  - [The C vs. Managed String Gap](#the-c-vs-managed-string-gap)
  - [File Extension Bypass](#file-extension-bypass)
- [Database & Storage Truncation](#database--storage-truncation)
  - [SQL Column Truncation](#sql-column-truncation)
  - [Username Impersonation](#username-impersonation)
- [Numeric Truncation](#numeric-truncation)
  - [Integer Casting](#integer-casting)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Software systems have limits. Buffers have sizes, database columns have lengths, and strings have terminators.
Truncation vulnerabilities occur when input exceeds these limits and is "chopped off" in a way that benefits the attacker. The system usually fails to reject the input, instead silently modifying it to fit.

### Foundational Examples

| CVE / Attack | Product | Category | Impact |
|-----|---------|----------|--------|
| - | MySQL (Legacy) | Database | Admin account takeover via space truncation |
| CVE-2006-2753 | PHP (Various) | Null Byte | `include()` local file inclusion |
| CVE-202X-XXXX | Smart Contracts | Integer | Overflow/Truncation causing balance errors |
| Golden Null | Certificates | PKI | Rogue CA certificates via null byte in Common Name |

### Why These Bugs Keep Recurring

-   **Implicit Behavior**: functions like `strncpy` or databases in non-strict mode fail silently.
-   **Language Mismatch**: C strings end at `\0` (0x00). PHP/Java/Python strings carry a length property and can contain `\0`.
-   **Optimization**: Checking bounds is "expensive" or "annoying" to handle errors for.

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

    Step 1: INPUT
    User sends: "admin___________[malicious_suffix]"

    Step 2: THE LIMIT
    System buffer/column size: 10 chars.

    Step 3: THE TRUNCATION
    System stores: "admin_____" (First 10 chars)
    [malicious_suffix] is discarded.

    Step 4: THE RESULT
    If the system explicitly checks for "admin", it might match.
    If the suffix contained a restriction (e.g. "role=user"), it is gone.
```

### The "Security Suffix" Failure

Many systems append a suffix to enforce security which gets truncated.
Example: `fopen(user_input + ".txt")`.
If `user_input` is long enough, `.txt` falls off the end of the buffer, allowing the user to open *any* file extension.

---

## Null Byte Truncation

This is the classic "Semantic Gap" between C-style strings and length-prefixed strings.

### The C vs. Managed String Gap

*   **C/C++**: Strings are defined by a starting pointer and end at the first null byte (`0x00`).
*   **PHP/Java/Python**: Strings are objects storing `(Buffer Pointer, Length)`. They support null bytes *inside* the string.

### File Extension Bypass

**Scenario:** Image Upload
Code (PHP):
```php
$filename = $_POST['filename']; // "shell.php%00.jpg"
if (endswith($filename, ".jpg")) {
    // PHP sees ".jpg" at the end. Content is safe.
    save_file($filename); 
}
```

**Under the Hood (OS/Filesystem):**
PHP calls libc `open()` or `fwrite()`.
Libc reads `$filename` until it hits `%00` (`\0`).
Libc sees: `"shell.php"`
File saved as: `shell.php`.

**Result:** PHP logic checked the extension, but the OS wrote a PHP file.

---

## Database & Storage Truncation

### SQL Column Truncation

In MySQL (typically older versions or non-strict mode), if you insert a string longer than the column definition (`VARCHAR(10)`), it truncates the string and throws a warning, not an error.

**Scenario:**
-   Table `users` has column `username VARCHAR(10)`.
-   Admin user exists: `admin`.

**The Attack:**
1.  Register as: `admin       x` (spaces + x).
2.  Database truncates to 10 chars: `admin     `.
3.  **Critical MySQL Behavior:** When comparing strings, trailing spaces are often ignored. `admin     ` == `admin`.
4.  Registration succeeds (unique constraint check might see the *full* string before truncation or be bypassed depending on logic order).
5.  Login: Authenticate as `admin       x`. Query looks up truncated version `admin`.
6.  **Result:** Logged in as `admin`.

### Username Impersonation

If a system creates an email address based on username: `username` + `@company.com`.
Limit: 20 chars.
1.  Attacker registers `admin_recovery_serv`.
2.  System appends `@company.com`.
3.  Total string: `admin_recovery_serv@company.com`.
4.  Truncation at 20: `admin_recovery_serv@`.
5.  If this is used in a display context, it might mislead users.

---

## Numeric Truncation

Occurs when converting larger integer types to smaller ones (e.g., 64-bit to 32-bit, or 32-bit to 16-bit).

### Integer Casting

```c
// VULNERABLE CODE
void process_packet(int length) { // length is 32-bit (e.g., 65537)
    unsigned short len = length;  // Cast to 16-bit
    // 65537 (0x10001) truncates to 1 (0x0001)
    
    char *buf = malloc(len);      // Allocates 1 byte
    memcpy(buf, input, length);   // Copies 65537 bytes -> HEAP OVERFLOW
}
```

**The Logic:**
`0x00010001` (32-bit) -> `0x0001` (16-bit).
The "upper bits" are truncated (lost).
The allocator sees a small safe number. The copy operation uses the original large number.

---

## Pattern Recognition: Where Else to Look

### Locations
1.  **Fixed-Width Protocols**: ISO 8583 (Financial), heavy C-struct based networking. If a field `Name` is fixed 10 chars, what happens if I send 11?
2.  **Filenames**: Windows limit `MAX_PATH` (260 chars). Linux `NAME_MAX` (255 chars).
3.  **Certificates**: Before 2011, `www.paypal.com\0.evil.com` was a valid technique to get an SSL cert for PayPal (truncation in CA validation).
4.  **JWTs**: Sometimes parsers behave weirdly if the Base64 string is cut off.

### Behavior Signatures
-   **Silent Success**: You blindly send huge data, and the application "works" but the data retrieved later is shorter.
-   **Warnings vs Errors**: Logs showing "Data truncated for column X" but the request returning 200 OK.

---

## Tools & Methodology

### Fuzzing
-   **Long Strings**: Send 100, 1000, 10000, 65536 characters.
-   **Null Bytes**: Inject `%00` in every string position.

### Diffing
-   Input: `AAAA...[marker]`
-   Output: Check if `[marker]` survives. If not, calculate the offset where it was cut.

---

## Legal & Ethical Considerations

### Do
-   Test truncation limits on registration forms to see if unique constraints fail.
-   Check file uploads with null bytes in filenames.

### Don't
-   Crash DBs by sending megabytes of data to a column (DoS).
-   Impersonate admins on live systems using SQL truncation.

---

*Document Version: 1.0*
*Last Updated: January 2026*
