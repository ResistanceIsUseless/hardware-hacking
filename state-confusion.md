# State Confusion Vulnerability Guide

A practical guide for understanding State Confusion vulnerabilities—where a system's logical state machine is manipulated or misunderstood, allowing operations to occur out of order or bypass checks.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [Business Logic State Confusion](#business-logic-state-confusion)
  - [E-Commerce Workflows](#e-commerce-workflows)
  - [Multi-Step Authentication](#multi-step-authentication)
- [Protocol State Machines](#protocol-state-machines)
  - [TCP/TLS Transitions](#tcptls-transitions)
  - [Wireless Protocols (WPA)](#wireless-protocols-wpa)
- [Web Application State](#web-application-state)
  - [Race Conditions vs. State](#race-conditions-vs-state)
  - [Hidden States](#hidden-states)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Every piece of software is fundamentally a **Finite State Machine (FSM)**. It exists in a specific "State" (e.g., `LOGGED_OUT`, `PENDING_PAYMENT`, `ADMIN`) and moves to new states via "Transitions" (e.g., `login()`, `pay()`, `escalate()`).

State Confusion occurs when:
1.  The developer assumes a linear progression (A -> B -> C).
2.  The attacker forces a non-linear transition (A -> C).
3.  The system performs the action for C without checking if B ever happened.

### Foundational Examples

| CVE / Case | Product | Category | Impact |
|-----|---------|----------|--------|
| "The Key Reinstallation Attack" (KRACK) | WPA2 | Protocol Logic | Resetting state to replay encryption keys |
| E-Commerce Logic | Shopping Carts | Business Logic | Adding items after payment calculation |
| CVE-2020-0796 (SMBGhost) | Windows SMB | Protocol Logic | Integer overflow in state compression |
| Dirty Pipe | Linux Kernel | Kernel State | Uninitialized pipe flags allowed writes |

### Why These Bugs Keep Recurring

-   **Implicit State**: State is often stored in loose variables (cookies, hidden fields) rather than a rigid database enforcing valid transitions.
-   **Complexity**: As features grow, the number of states grows exponentially.
-   **Happy Path Testing**: QA tests A -> B -> C. Attackers try A -> C, B -> A, C -> B.

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

    Intended Flow:
    [ START ] --> [ VALIDATE ] --> [ PROCESS ] --> [ FINISH ]

    Attacker Flow (State Confusion):
    [ START ] -------------------> [ PROCESS ] --> [ FINISH ]
                       (Skip Validate)
                       
    Or Backtracking:
    [ PROCESS ] <--> [ FINISH ] (Repeating 'Finish' action)
    
```

### The "Undefined Transition"

In a strict FSM, if you are in State A and try to trigger Transition Z (which is only valid for State Y), the system should throw an error. In vulnerable systems, it simply processes Transition Z using whatever data is currently in memory.

---

## Business Logic State Confusion

### E-Commerce Workflows

**The "Standard" Workflow:**
1.  Add to Cart (State: `CART`)
2.  Checkout (State: `CHECKOUT`)
3.  Calculate Shipping/Tax (State: `CALC_DONE`)
4.  Payment (State: `PAID`)
5.  Order Confirmation (State: `COMPLETED`)

**The Attack:**
1.  User gets to Step 4 (`PAID`) with a cheap item ($5).
2.  User keeps Step 4 open in one tab.
3.  User opens Step 1 (`CART`) in another tab and adds a generic expensive item ($500).
4.  User submits the Step 4 form.
    *   **Vulnerability:** If the system recalculates the cart *contents* at step 4 but applies the *payment success* from the previous session state, the user might get the $500 item marked as Paid.

### Multi-Step Authentication

**Scenario:** 2FA Login
1.  Enter Username/Pass -> (State: `PRE_AUTH`, Session Variable: `2fa_pending=true`)
2.  Enter 2FA Code -> (State: `AUTHED`, Session Variable: `2fa_pending=false`)

**Attack:**
Force Browse directly to `/dashboard`.
*   **Vulnerability:** Does `/dashboard` check `is_logged_in()` OR does it check `!is_2fa_pending`?
*   If the code merely checks "Does user exist in session?", the state `PRE_AUTH` is confused with `AUTHED`.

---

## Protocol State Machines

Binary protocols (TCP, TLS, SMB) are rigid state machines.

### TCP/TLS Transitions
**Early CCS Injection (CVE-2014-0224):**
In OpenSSL, the `ChangeCipherSpec` (CCS) message signals "Switch to Encryption Mode". It is supposed to happen *after* the Key Exchange.
Attackers sent the CCS message *during* the handshake (out of order).
*   **Confusion:** OpenSSL switched to "Encrypted Mode" but with an empty (zero) key, because the key exchange hadn't finished.

### Wireless Protocols (WPA)
**KRACK (Key Reinstallation Attack):**
The WPA2 4-way handshake establishes a session key.
Message 3 installs the key.
*   **Attack:** Attacker replays Message 3.
*   **Confusion:** The client receives Message 3 again. The spec says "Install the Key". The client resets the "Nonce" (counter) to zero.
*   **Result:** Encryption stream reused (Nonce Reuse), breaking confidentiality. The state machine failed to handle "What if I receive the installation message twice?"

---

## Web Application State

### Hidden States

Developers often store state in the client to avoid server load.
*   Hidden Form Fields: `<input type="hidden" name="step" value="2">`
*   Cookies: `status=guest`
*   URLs: `/checkout/step2`

**Attack:** simply change `value="2"` to `value="4"`.
If the server implementation is: `process_step(int step)`, and it relies on the client to tell it what step it's on, you can jump to the final step (e.g., "Download File") bypassing payment.

### Dropping States

**Scenario:** Password Reset
1.  Request Reset -> Email Sent.
2.  Click Link -> Enter New Password.
3.  Submit -> Password Changed.

**Confusion:**
Can I manipulate Step 1 to generate a token for User A, but submit Step 3 for User B?
If the state (Which user is resetting?) is loosely coupled to the token, the application acts as if User B requested the reset.

---

## Pattern Recognition: Where Else to Look

### Visualizing the Machine
To find these bugs, draw the map.

```
       ┌───► [ STATE B ] ───┐
[ STATE A ]                 ▼
       └───► [ STATE C ] ──► [ STATE D ]
```

Ask:
*   Can I go A -> D directly?
*   Can I go D -> B?
*   What happens if I send the "State B" inputs while in "State D"?

### Common Targets
*   **Registration Flows:** Skipping email verification.
*   **Installation Wizards:** CMS installers often have `/install/step1`...`/install/complete`. Can you hit `/install/complete` on an existing site to reset the admin password?
*   **Refunds/Returns:** Can I initiate a "Return" state for an order that is in "Pending" state?

---

## Tools & Methodology

### Burp Suite Repeater
The primary tool for Web State confusion.
1.  Map the full valid flow. Save all requests in history.
2.  Take the request for Step 3.
3.  Send it while the account is actually in Step 1.
4.  Analyze the response. Did it process? Did it error?

### Finite State Machine Learning (fsm-learn)
For protocol testing (like TLS/SSH), tools like `stateafl` or `tls-attacker` can automatically learn the state machine and try to find paths that result in crashes or unexpected acceptance.

### Model Checking
Formal verification methods (TLA+) prevent these bugs, but few developers use them. As a researcher, you are effectively "Model Checking" the live system by probing invalid transitions.

---

## Legal & Ethical Considerations

### Do
*   Test logic flows with your own accounts.
*   Be gentle; logic bugs can corrupt database integrity (e.g., creating "paid" orders that don't exist).

### Don't
*   Exploit payment logic to steal goods (State Confusion is a common source of theft).
*   Leave systems in broken states (e.g., half-installed components).

---

*Document Version: 1.0*
*Last Updated: January 2026*
