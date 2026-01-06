# Reference Confusion Vulnerability Guide

A practical guide for understanding Reference Confusion vulnerabilities—including IDOR, Prototype Pollution, and specialized aliasing issues—where the application confuses the *identity* or *owner* of a resource.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [Insecure Direct Object Reference (IDOR)](#insecure-direct-object-reference-idor)
  - [The Database Lookup Fallacy](#the-database-lookup-fallacy)
  - [Blind IDOR](#blind-idor)
- [Object Graph & Graph Reference Confusion](#object-graph--graph-reference-confusion)
  - [Nested Object Access](#nested-object-access)
  - [GraphQL/API Over-Selection](#graphqlapi-over-selection)
- [Prototype Pollution (JS Reference Confusion)](#prototype-pollution-js-reference-confusion)
  - [The `__proto__` Attack](#the-__proto__-attack)
- [Python Class Pollution](#python-class-pollution)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Reference Confusion describes a class of bugs where the user supplies a reference (an ID, a pointer, a key, or a path), and the system accepts it without verifying:
1.  **Ownership:** Does the user own this reference?
2.  **Context:** Is this reference valid for the current operation?
3.  **Target:** Is this modifying the intended object or a base template?

### Foundational Examples

| CVE / Attack | Product | Category | Impact |
|-----|---------|----------|--------|
| - | Parler (2021) | IDOR | Mass scraping of user data via incrementing IDs |
| - | Uber (2019) | IDOR | Account takeover via `user_id` in API response |
| CVE-2019-10744 | Lodash | Prototype Pollution | RCE via uncontrolled property merge |
| CVE-2022-XXXX | Kibana | Prototype Pollution | RCE via Gadget chain |

### Why These Bugs Keep Recurring

-   **Separation of Concerns**: The database fetches data; the controller handles auth. The connection often breaks.
-   **Predictability**: Computer systems use sequential integers or predictable patterns for efficiency.
-   **Dynamic Languages**: JS and Python objects are mutable at runtime, allowing references to base classes (`Object.prototype`) to be modified.

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

    Step 1: THE REFERENCE
    User Request: GET /invoice?id=1001

    Step 2: THE LOOKUP (The "Direct" part)
    System: "SELECT * FROM invoices WHERE id = 1001"
    
    Step 3: THE MISSING CHECK
    System returns the object.
    
    FAILURE: The system never asked "Does User A own Invoice 1001?"
```

It is "Confused" because it treats the *validity of the ID* (it exists) as proof of *authorization* (you can see it).

---

## Insecure Direct Object Reference (IDOR)

### The Database Lookup Fallacy

Developers often write code like:
```php
// VULNERABLE
$invoice = Invoice::find($_GET['id']);
if ($invoice) {
    return view('invoice', $invoice);
}
```

Instead of:
```php
// SECURE
$invoice = Invoice::where('id', $_GET['id'])
                  ->where('user_id', current_user()->id)
                  ->first();
```

### Blind IDOR

Sometimes you don't *see* the result, but you can effect change.
*   `POST /password_change` with body `{"user_id": 1001, "new_pass": "123"}`.
*   System returns "Success".
*   You verified the IDOR not by reading data, but by changing the state of another user.

---

## Object Graph & Graph Reference Confusion

In modern APIs (REST/GraphQL), objects are nested.

### Nested Object Access

You might not be able to access `GET /users/1005` (Blocked).
But can you access `GET /company/99/users/1005`?

**Confusion:** The permissions might be checked on the **Parent** (Company 99), and if you belong to Company 99, the system implicitly trusts you can access all **Child** (User 1005) objects, even if User 1005 is marked "Private".

### GraphQL/API Over-Selection

Reference confusion often happens in the "fields" selector.
*   Query: `query { user(id:me) { friends { private_notes } } }`
*   The system checks: Can you access `user(id:me)`? YES.
*   The system fails to check: Can you access the *reference* `friends.private_notes`?

---

## Prototype Pollution (JS Reference Confusion)

This is a specific, high-impact form of Reference Confusion in JavaScript.

### The `__proto__` Attack

In JS, every object has a prototype. If you modify the prototype, **every object in the application** inherits that change.

**The Trigger:** A recursive merge function.
```javascript
merge(target, source) {
    for (key in source) {
        target[key] = source[key];
    }
}
```

**The Attack Payload:**
```json
{
    "__proto__": {
        "isAdmin": true
    }
}
```

**The Confusion:**
1.  The `merge` function treats `__proto__` as just another key.
2.  It writes to `target["__proto__"]["isAdmin"]`.
3.  This modifies `Object.prototype`.
4.  Later, the app checks `if (user.isAdmin)`.
5.  Since `user` object doesn't have an `isAdmin` property, JS looks up the prototype chain.
6.  It finds `Object.prototype.isAdmin = true`.
7.  Auth Bypass.

---

## Python Class Pollution

Similar to Prototype Pollution but in Python.

**Trigger:** Recursive updates or unsafe object merges often found in frameworks dealing with data binding.
**Reference:** `__class__.__init__.__globals__`.

If you can write to `user.__class__.__init__.__globals__`, you are referencing the global state of the application. You can overwrite configuration flags like `DEBUG=True` or `SECRET_KEY`.

---

## Pattern Recognition: Where Else to Look

### Locations
1.  **URL Parameters**: `id=`, `account=`, `file=`.
2.  **JSON APIs**: `{"user_id": ...}` properties in POST bodies.
3.  **Cookies**: `auth=101`.
4.  **Static Files**: `/images/1001.jpg` (Sequential static files often lack auth checks completely).

### UUIDs vs Integers
*   **Integers (1, 2, 3)**: Trivial to enumerate.
*   **UUIDs**: Harder to guess, but **still vulnerable**. If I refer someone else's UUID (found via another leak), the system still needs to check authorization. *Security by obscurity (hiding the UUID) is not Authorization.*

---

## Tools & Methodology

### Autorize (Burp Extension)
The gold standard for IDOR testing.
1.  Browse the app as **User A**.
2.  Autorize replays every request with the cookies of **User B** (or no cookies).
3.  If User B gets a "200 OK" for User A's resource, it flags a potential IDOR.

### Manual Pwn
1.  **Swap IDs**: Change `id=10` to `id=11`.
2.  **HTTP Parameter Pollution**: Send `id=10&id=11`. System might check 10 (Authorized) but fetch 11 (Target).
3.  **Type Juggling (JSON)**: Send `id: 100` (int) vs `id: "100"` (string) vs `id: [100]` (array). Sometimes parsers confuse arrays for single IDs bypassing filters.

---

## Legal & Ethical Considerations

### Do
*   Create two accounts (User A and User B) and attack B from A.
*   Report immediately if you see PII.

### Don't
*   Enumerate thousands of IDs to scrape data (this transforms a vulnerability into a breach).
*   Change passwords of random account IDs.

---

*Document Version: 1.0*
*Last Updated: January 2026*
