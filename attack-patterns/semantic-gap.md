# Semantic Gap Vulnerability Guide

A practical guide for understanding Semantic Gap vulnerabilities—where different layers of a system (Hardware, OS, Hypervisor, Application) interpret the same data or state differently, creating security blind spots.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [Polyglot Files](#polyglot-files)
  - [GIF/JS Polyglots](#gifjs-polyglots)
  - [Zip/Jar/Dex Fusion](#zipjardex-fusion)
- [WAF vs. Application Gaps](#waf-vs-application-gaps)
  - [Parameter Pollution (HPP)](#parameter-pollution-hpp)
  - [Encoding Differences](#encoding-differences)
- [Virtualization Gaps (VMI)](#virtualization-gaps-vmi)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Complex systems are layered. A file is just bits to the disk, sectors to the driver, clusters to the filesystem, a stream to the OS, and an image to the application.
A Semantic Gap exists when Layer A thinks the data means "X", but Layer B thinks the data means "Y".

### Foundational Examples

| CVE / Attack | Context | Layer A View | Layer B View | Impact |
|-----|---------|--------------|--------------|--------|
| Gifar | Web | Start is GIF (Image) | End is JAR (Code) | XSS/RCE via Java Applet |
| HTTP Parameter Pollution | Web | Sees first param | Sees last param | WAF Evasion |
| Rowhammer | Hardware | Bits are stable | Bits are flipped | Memory Corruption |
| Sandbox Escape | Malware | Benign activity | Malicious intent | Detection Bypass |

### Why These Bugs Keep Recurring

-   **Parsing is Hard**: File formats (PDF, PE, ZIP) are complex and specifications are vague.
-   **Defense-in-Depth Disconnect**: The firewall is built by Vendor A, the App Server by Vendor B. They don't share parsing logic.
-   **Abstraction Leaks**: High-level code assumes hardware is perfect. It isn't.

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

    DATA: [ Header A ] [ Junk ] [ Header B ] [ Payload ]

    LAYER 1 LOOKS (e.g., Filtering Proxy):
    "I see Header A. This is a PNG image. Safe."
    -> PASS

    LAYER 2 LOOKS (e.g., Browser Script Engine):
    "I see Header B (at offset 100). This is a Script."
    -> EXECUTE

    The gap is in the definition of "What is a file?"
    Is it defined by the first bytes? The extension? Or valid internal structures?
```

---

## Polyglot Files

A Polyglot is a file that is valid in multiple formats simultaneously.

### GIF/JS Polyglots

Browsers are linient.
*   **GIF Header**: `GIF89a...`
*   **JavaScript**: `GIF89a = 1; alert(1);`

If you serve this file as an image (`Content-Type: image/gif`), the browser renders it.
If you can trick the site into serving it as a script (`<script src="image.gif">`), the browser executes it as JS. The `GIF89a` is seen as a variable assignment.

### Zip/Jar/Dex Fusion

*   **ZIP files** are parsed from the *End of Central Directory* (footer).
*   **PDF/JPEG files** are parsed from the *Header*.

**Attack:**
Create a file that starts with `JPEG Header` + `Image Data`.
Append `ZIP` structure at the end containing `classes.dex`.
*   Image Viewer sees: Valid JPEG.
*   Android Packer sees: Valid APK (ZIP).
*   Result: Hide malware inside an image.

---

## WAF vs. Application Gaps

### Parameter Pollution (HPP)

**Input:** `POST /transfer?to=attacker&to=victim`

*   **WAF (Layer 1)**: Checks the *last* parameter. "recipient = victim". Safe.
*   **Application (Layer 2)**: Takes the *first* parameter. "recipient = attacker".
*   **Result:** WAF thinks the request is for the victim, App gives money to attacker.

**Variation Matrix:**
| Technology | Behavior with `?p=1&p=2` |
| :--- | :--- |
| ASP.NET | `p=1,2` (Concatenates) |
| PHP | `p=2` (Last wins) |
| JSP | `p=1` (First wins) |
| Node.js | `p=[1, 2]` (Array) |

### Encoding Differences

*   **WAF**: Decodes UTF-8.
*   **App**: Decodes IBM037 (EBCDIC) or non-standard Unicode.
*   **Attack**: Send payload in an encoding the WAF doesn't understand but the App does.

---

## Virtualization Gaps (VMI)

**Virtual Machine Introspection (VMI)** involves a Hypervisor looking at the memory of a Guest VM to detect malware.
*   **The Gap**: The Hypervisor sees "Physical Pages" (Raw Hex). It has to *reconstruct* the OS knowing the kernel version, struct layouts, etc.
*   **The Attack (DKOM)**: Direct Kernel Object Manipulation. Malware unlinks itself from the Windows Process Linked List.
    *   OS List: Process is gone.
    *   Scheduler: Process is still running (thread pointers exist).
    *   VMI Tool: Scans list, sees nothing. "System Clean".

---

## Pattern Recognition: Where Else to Look

### Boot Loaders (Secure Boot)
*   **Hardware**: Checks signature of the Bootloader.
*   **Semantics**: "Signature is valid."
*   **Software**: "This is a signed bootloader, but it's an OLD version with a known vulnerability." (Rollback attack). The semantic gap is "Valid Signature" vs "Secure Version".

### Network Instruction Detection (NIDS)
*   **NIDS**: Reconstructs TCP stream. Sees `GET /index.html`.
*   **Target Server**: Receives overlapping IP fragments differently than the NIDS. Sees `GET /evil.php`.
*   **Technique**: IP Fragmentation attacks / TCP Segmentation Offloading abuse.

---

## Tools & Methodology

### File Dissectors
*   **binwalk**: Visualize file structures. Look for embedded headers (e.g., a ZIP header appearing in the middle of a PDF).
*   **010 Editor**: Templates show how different parsers view the bytes.

### Polyglot Generators
*   **Mitra**: A tool to generate binary polyglots (e.g., PDF+JPG, PE+ZIP).

### HPP Param Miner
*   Burp Suite extension to test how servers handle duplicate parameters.

---

## Legal & Ethical Considerations

### Do
*   Use HPP to test WAF resiliency.
*   Demonstrate how benign-looking files can harbor malicious code (steganography/polyglots).

### Don't
*   Upload obfuscated malware to VirusTotal to "test" evasion (it pollutes the dataset).
*   Bypass malware scanners on production email gateways.

---

*Document Version: 1.0*
*Last Updated: January 2026*
