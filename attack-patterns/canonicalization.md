# Canonicalization Vulnerability Guide

A practical guide for understanding vulnerabilities arising from how systems convert data (paths, URLs, Unicode) into a standard "canonical" form.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [Path Canonicalization](#path-canonicalization)
  - [Directory Traversal](#directory-traversal)
  - [Slash Confusion](#slash-confusion)
- [Web & URL Canonicalization](#web--url-canonicalization)
  - [Double Encoding](#double-encoding)
  - [Normalization Bypass](#normalization-bypass)
- [Unicode Canonicalization](#unicode-canonicalization)
  - [Homoglyphs & Normalization Forms](#homoglyphs--normalization-forms)
  - [Case Mapping Collisions](#case-mapping-collisions)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Attack Surfaces](#attack-surfaces)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Canonicalization (or normalization) is the process of converting data that has more than one possible representation into a "standard" (canonical) representation.

Security issues arise when:
1.  **Inconsistent Interpretation:** The security check sees the raw data, but the backend sees the canonical data.
2.  **Order of Operations:** Checks are performed *before* canonicalization (Check -> Decode -> Use).
3.  **Ambiguity:** The rules for "standard" differ between systems (e.g., Windows vs Linux paths).

### Foundational Examples

| CVE | Product | Category | Impact |
|-----|---------|----------|--------|
| CVE-2021-41773 | Apache HTTPD | Path Traversal | RCE via double URL decoding |
| CVE-2019-11510 | Pulse Secure | Path Traversal | File read via `%2e%2e/` (encoded ../) |
| Log4Shell | Log4j | JNDI | Bypassing filters via `${lower:j}ndi` |
| Spotify | Web Account | Unicode | Account takeover via `ᴷ` vs `K` normalization |

### Why These Bugs Keep Recurring

-   **Complexity of Strings** — Text is hard. Unicode is massive. URLs are complex.
-   **Layered Architecture** — WAF decodes input once. App Server decodes it again. Backend File Server normalizes path.
-   **Defense First** — Developers naturally validate input *as they receive it*, not realizing it will morph later.

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

    Step 1: INPUT
    User sends: "%2e%2e/secret" (Encoded "../secret")

    Step 2: THE CHECK (VULNERABLE)
    "Does string contain '../' ?"
    -> NO. (It contains key %2e%2e/)
    -> ALLOW.

    Step 3: CANONICALIZATION (The Morph)
    System decodes URL encoding.
    "%2e%2e/" becomes "../"

    Step 4: THE USE
    "Open ../secret"
    -> TRAVERSAL SUCCESS.
```

 **The Correct Pattern:** Canonicalize FIRST, Check SECOND. Use LAST.

---

## Path Canonicalization

The most common form is Directory Traversal.

### Directory Traversal

Representations of "Parent Directory":
-   `../` (Standard)
-   `..\` (Windows)
-   `..` (Just dots)
-   `.../` (Some parsers strip extra dots)
-   `%2e%2e%2f` (URL Encoded)
-   `%252e%252e%252f` (Double URL Encoded)
-   `..%c0%af` (UTF-8 Overlong Encoding for slash)

**The Attack:**
If a filter blacklists `../`, can we use `..\/`? Can we use `....//` (which becomes `../` if the filter removes one `../` recursively)?

### Slash Confusion

Windows treats `/` and `\` as separators. Linux only uses `/`.
-   Input: `dir\..\secret`
-   Linux Check: "File name is `dir\..\secret`". Safe.
-   Windows Backend: "Directory `dir`, Parent `..`, File `secret`". Traversal.

---

## Web & URL Canonicalization

URLs are decoded by almost every device they pass through (Load Balancer, Proxy, WAF, Web Server, App Framework).

### Double Encoding

Refers to encoding the `%` sign itself.

1.  Attack: `%252e%252e%252f`
2.  WAF Layer: Decodes `%25` -> `%`. Result: `%2e%2e%2f`.
    *   WAF checks: Is this `../`? No. Pass.
3.  App Layer: Decodes `%2e` -> `.`, `%2f` -> `/`. Result: `../`.
4.  Action: Traversal.

### Normalization Bypass

Some endpoints are case-sensitive, some aren't.
-   Rule: `Block /ADMIN`
-   Attack: `GET /admin` -> Blocked?
-   attack: `GET /%61dmin` -> WAF sees encoding, might miss rule. Backend normalizes to `/admin`.

---

## Unicode Canonicalization

Unicode is a goldmine for canonicalization bugs due to "Compatibility Normalization" (NFKC).

### Homoglyphs & Normalization Forms

Characters that look different but normalize to the same value.

**Example: The Kelvin Sign**
-   Standard `K` (U+004B)
-   Kelvin Sign `K` (U+212A)

**Vulnerability:**
1.  Password Reset Logic checks: `if (username == "admin") fail("Locked");`
2.  Attacker registers: `admin` (using Kelvin K).
3.  Check: `admin` (Kelvin) != `admin` (ASCII). Check passed.
4.  Database Storage: Normalizes strings before query. `K` becomes `K`.
5.  Result: Query executes against `admin`. Logic bypassed.

### Case Mapping Collisions

-   `ß` (German Eszett) uppercases to `SS`.
-   `ﬁ` (Ligature) normalizes to `fi`.
-   `ı` (Turkish dotless i) behaves weirdly in capitalization logic.

**Exploit:**
If a WAF filters `<script>`, does it filter `<ſcript>` (Long S)? If the browser or backend normalizes `ſ` to `s`, the XSS payload triggers.

---

## Pattern Recognition: Where Else to Look

### Locations
1.  **Filenames**: NTFS Alternate Data Streams (`file.txt:stream`), trailing dots (`file.txt.`), reserved names (`CON`, `AUX`, `NUL` on Windows).
2.  **Email Addresses**: `gmail.com` ignores dots (`u.ser` == `user`).
3.  **Username Registration**: Homoglyph attacks to impersonate admins.
4.  **JSON/XML Parsers**: Duplicate keys (`{"a": 1, "a": 2}`). Does the parser take the first or last?

### Code Patterns (Java/Python used as examples)

```java
// VULNERABLE
public void serveFile(String path) {
    if (path.contains("..")) throw new Error(); // Check
    
    path = URLDecoder.decode(path, "UTF-8");    // Canonicalize
    File f = new File(path);                    // Use
}

// SAFE
public void serveFileSafe(String path) {
    path = URLDecoder.decode(path, "UTF-8");    // Canonicalize
    File f = new File(path);
    String canonicalPath = f.getCanonicalPath(); // OS Normalization
    
    if (!canonicalPath.startsWith("/safe/dir/")) throw new Error(); // Check
}
```

---

## Attack Surfaces

### Content Delivery Networks (CDNs)
CDNs cache content based on URL paths. If you can request `/static/..%2fprivate`, and the CDN normalizes it to `/private` but thinks it's serving specific static content, you might poison the cache or bypass auth.

### Microservices
Service A validates input. Service B assumes input is valid. If Service B performs *additional* normalization (e.g., JSON decoding), attacks slip through.

---

## Tools & Methodology

### Fuzzing Strings
Use lists of "naughty strings":
-   Unicode homoglyphs.
-   Overlong UTF-8 (`%C0%AE` for `.`).
-   Windows reserved filenames (`COM1`).

### Burp Suite
-   **Decoder Tab**: Manually normalize strings to see what they might become.
-   **Active Scan**: Checks for standard path traversals.

### WAF Bypass Techniques
-   Try varying encodings (`UTF-16`, `IBM037`).
-   Try inserting "junk" characters that specific parsers ignore (Null bytes `%00`, Tabs `%09`).

---

## Legal & Ethical Considerations

### Do
-   Test boundary cases on standard, non-production inputs.
-   Verify if your target (e.g., IIS, Nginx) has specific normalization quirks documented.

### Don't
-   Use directory traversal to pull Sensitive PII (e.g., `/etc/shadow`) just to "prove" it. Read `/etc/hostname` or a benign file instead.

---

*Document Version: 1.0*
*Last Updated: January 2026*
