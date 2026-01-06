# TOCTOU (Time-of-Check to Time-of-Use) Vulnerability Guide

A practical guide for understanding and hunting Race Conditions specifically related to the gap between verifying a resource and interacting with it.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [Filesystem TOCTOU](#filesystem-toctou)
  - [The Symlink Attack](#the-symlink-attack)
  - [Temporary File Hijacking](#temporary-file-hijacking)
- [Web & Business Logic TOCTOU](#web--business-logic-toctou)
  - [Limit Bypass](#limit-bypass)
  - [Double Spending](#double-spending)
- [Kernel Double-Fetch](#kernel-double-fetch)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Attack Surfaces](#attack-surfaces)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

TOCTOU (Time-of-Check to Time-of-Use) is a subset of race conditions. It occurs when a program checks the state of a resource (file, variable, permission) to ensure it's safe or valid, but the state changes before the program actually uses that resource.

If an attacker can effectively manipulate memory, files, or state during that tiny window of time, they can bypass the check completely.

### Foundational Examples

| CVE | Product | Category | Impact |
|-----|---------|----------|--------|
| CVE-2024-XXXX | Linux Utils | Local Privilege Escalation | Root file write via /tmp race |
| CVE-2016-10033 | PHPMailer | Library | RCE via log file race |
| "Dirty COW" | Linux Kernel | Kernel | Copy-on-Write race violation |
| Logic Bugs | E-commerce | Web App | Using coupon code multiple times |

### Why These Bugs Keep Recurring

-   **Non-Atomic Operations** — OS APIs often separate "check" and "open".
-   **Concurrency** — Identifying all threads/processes touching a resource is hard.
-   **Assumption of Stability** — Developers assume "If I checked it, it's true."
-   **Speed** — The "race window" might be nanoseconds, but computers are fast enough to hit it.

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

    Step 1: THE CHECK (Time of Check)
       │    "Does the user own /tmp/file?" -> YES
       │
    [ RACE WINDOW ] <--- ATTACKER ACTS HERE
       │                 (e.g., Delete /tmp/file, replace with symlink)
       │
    Step 2: THE USE (Time of Use)
            "Write to /tmp/file" -> Writes to attacker's target
```

### The Gap

The vulnerability isn't in the check or the use, but the **atomicity** (indivisibility) of the transaction. If `Check + Use` is not one atomic instruction, a race exists.

---

## Filesystem TOCTOU

This is the classic UNIX vulnerability.

### The Symlink Attack

Vulnerable privileged code (running as Root):

```c
// VULNERABLE CODE
char *filename = "/tmp/user_data";

// 1. CHECK: Does file exist? Is it a regular file?
if (access(filename, W_OK) == 0) {
    
    // [ ATTACKER SWITCHES FILE HERE ]
    
    // 2. USE: Open the file
    FILE *f = fopen(filename, "w");
    fprintf(f, "secret_data");
    fclose(f);
}
```

**The Exploit:**

1.  Attacker creates `/tmp/user_data`.
2.  Program runs `access()`. It returns SUCCESS because attacker owns it.
3.  **Immediately**, attacker runs `rm /tmp/user_data; ln -s /etc/passwd /tmp/user_data`.
4.  Program runs `fopen()`. It follows the link.
5.  Program writes "secret_data" into `/etc/passwd`.

**Code Fix:** Use file descriptors. `fstat()` the descriptor *after* opening to ensure it matches expectations. Or use `open()` flags like `O_NOFOLLOW`.

### Temporary File Hijacking

Common in installation scripts or cleanup jobs.

1.  Script checks `if (!exists("/tmp/install.log"))`.
2.  Script prepares to write.
3.  Attacker creates `/tmp/install.log` with malicious permissions or content.
4.  Script writes to file, inheriting attacker's set permissions or appending to it.

---

## Web & Business Logic TOCTOU

In web apps, the race usually involves database states and multiple parallel requests.

### Limit Bypass

**Scenario:** A user can only upload 3 files.

```php
// VULNERABLE LOGIC
$count = $db->query("SELECT count(*) FROM uploads WHERE user_id = ?", $uid);

if ($count < 3) {
    // [ RACE WINDOW ]
    $db->query("INSERT INTO uploads ...");
    saveFile();
}
```

**Exploit:**
The attacker sends 10 requests **simultaneously** (using Turbo Intruder or Burp).
All 10 requests read the database at the same time.
All 10 see `count = 0`.
All 10 pass the check.
All 10 insert.
User now has 10 files.

### Double Spending

**Scenario:** Gift Card balance.

1.  Request 1: Check Balance ($100) -> OK.
2.  Request 2: Check Balance ($100) -> OK (Request 1 hasn't saved new balance yet).
3.  Request 1: Deduct $100.
4.  Request 2: Deduct $100.
5.  Result: $200 spent with $100 balance.

---

## Kernel Double-Fetch

A specialized binary exploitation technique. Kernels read data from "User Space" (untrusted) into "Kernel Space" (trusted).

**The Double Fetch:**
1.  Kernel reads a length field from User Pointer.
    *   `if (user_len > 100) return ERROR;` (Check)
2.  Kernel allocates `user_len` (e.g., 50 bytes).
3.  Kernel reads the data again (Double Fetch) from User Pointer to copy it.
    *   **Race:** Another user thread changed the length at that address to 1000 between fetch 1 and 2.
4.  Kernel copies 1000 bytes into a 50 byte buffer.
5.  **Result:** Buffer Overflow in Kernel Space.

---

## Pattern Recognition: Where Else to Look

### Code Patterns

```c
// C/C++ Filesystem
access(file, ...) followed by open(file, ...)
stat(file, ...) followed by open(file, ...)
mktemp() (Use mkstemp instead!)

// Web / SQL
SELECT ... read balance
// code logic
UPDATE ... set balance

// Binary
Multiple reads from the same pointer reference in a function without caching the value in a local register/variable.
```

### Contexts
1.  **Shared Resources:** Files in `/tmp`, `/var/run`, shared memory segments.
2.  **Payment Gateways:** Coupon redemptions, transfers, distinct limit checks.
3.  **Installation Scripts:** Shell scripts checking for file existence.
4.  **Signal Handling:** If a signal handler modifies a global variable checked by main loop.

---

## Attack Surfaces

### Web Applications
-   **Coupons/Vouchers**: "Redeem Once" logic.
-   **Inventory**: "Only 1 item left".
-   **Transfers**: Send money between accounts.

### Operating Systems
-   **SUID Binaries**: Programs that run as root but handle user files.
-   **Installers**: Package managers (yum/apt) scripts running as root in shared dirs.
-   **Antivirus**: Scanners that check a file, verify it's clean, then let the OS open it (classic AV bypass).

---

## Tools & Methodology

### Filesystem Races
-   **Inotify tools**: Watch file access events to time attacks.
-   **RaceTheWeb**: Tools to send parallel HTTP requests.
-   **TOCTOU-fuzzer**: Specialized scripts that loop creation/deletion of symlinks while running a target binary.

### Web Races
-   **Burp Suite Turbo Intruder**: Essential tool. Allows sending a "block" of requests that are released to the server in the same TCP packet window to maximize concurrency.

### Kernel
-   **Bochs/QEMU**: Instrumented emulators to detect double reads from user-space addresses.

---

## Legal & Ethical Considerations

### Do
-   Test web races on test accounts only.
-   Be careful with DoS; race testing generates high traffic.

### Don't
-   Attempt to race condition a bank or financial platform without explicit authorization (this is fraud).
-   Crash shared servers by exhausting file descriptors or threads.

---

*Document Version: 1.0*
*Last Updated: January 2026*
