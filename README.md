# Attack Pattern Guides

A collection of educational guides focused on understanding the **fundamental patterns** behind common vulnerability classes. Each guide distills the core concept to help you recognize the same pattern across different contexts and technologies.

## Guides

| Pattern | Description | File |
|---------|-------------|------|
| **Memory Disclosure** | Attacker-controlled length fields cause buffer overreads, leaking sensitive data | [memory-disclosure.md](memory-disclosure.md) |
| **Parser Differential** | Two systems interpret the same input differently, creating security gaps | [parser-differential.md](parser-differential.md) |
| **Deserialization** | Untrusted data is converted back into live objects, enabling code execution | [deserialization.md](deserialization.md) |
| **Type Confusion** | A resource is accessed using an incompatible type, corrupting memory or logic | [type-confusion.md](type-confusion.md) |
| **TOCTOU** | Time gap between checking and using a resource allows state manipulation | [toctou.md](toctou.md) |
| **Canonicalization** | Data transforms into a "standard" form after security checks, bypassing them | [canonicalization.md](canonicalization.md) |
| **Gadget Chains** | Existing code is chained together to achieve malicious execution | [gadget-chains.md](gadget-chains.md) |
| **State Confusion** | Logical state machine is manipulated, allowing out-of-order operations | [state-confusion.md](state-confusion.md) |
| **Truncation** | Data is cut short due to limits or terminators, changing its meaning | [truncation.md](truncation.md) |
| **Reference Confusion** | System confuses the identity or ownership of a referenced resource | [reference-confusion.md](reference-confusion.md) |
| **Semantic Gap** | Different system layers interpret the same data differently | [semantic-gap.md](semantic-gap.md) |

## Philosophy

These guides aim to teach the **transferable pattern**, not just specific exploits. Once you understand the core concept, you can recognize it in:

- New technologies
- Different programming languages
- Novel attack surfaces

## Other Resources

| File | Description |
|------|-------------|
| [setup.md](setup.md) | Lab setup instructions |
| [targets-guide.md](targets-guide.md) | Target selection guidance |
| [CBECSC23.md](CBECSC23.md) | Hardware challenge walkthrough |

---

## Practice Platforms

### Reverse Engineering & Crackme Challenges

| Platform | Focus | Notes |
|----------|-------|-------|
| [crackmes.one](https://crackmes.one/) | RE challenges | Has an upcoming CTF competition starting February 2026 |
| [challenges.re](https://challenges.re/) | RE exercises | From the author of "Reverse Engineering for Beginners" - no solutions provided |
| [Nightmare](https://guyinatuxedo.github.io/index.html) | Binary exploitation/RE | 90+ challenges with detailed writeups, great linear progression |
| [exploit.education](https://exploit.education/) | Binary exploitation | VMs for learning various security issues |
| [ROP Emporium](https://ropemporium.com/) | Return-oriented programming | Focused specifically on ROP chains |
| [CryptoHack](https://cryptohack.org/) | Cryptography | Fun crypto-specific challenges |
| [CTFlearn](https://ctflearn.com/) | General CTF | Learn and compete |

### Hardware Hacking & IoT Focused

| Platform | Focus | Notes |
|----------|-------|-------|
| [Microcorruption](https://microcorruption.com/) | Embedded security | Browser-based debugger with MSP430 assembly - challenges you to bypass fictional embedded locks. Excellent intro without buying hardware. |
| [DVRF](https://github.com/praetorian-inc/DVRF) | Router firmware | Damn Vulnerable Router Firmware - learn MIPS exploitation. Can run in QEMU if you don't have the E1550 hardware. |
| [IoTGoat](https://github.com/OWASP/IoTGoat) | IoT firmware | Deliberately insecure firmware based on OpenWrt |
| [Rhme (Riscure Hack Me)](https://github.com/Riscure/Rhme-2016) | Hardware CTF | Hardware CTF challenges from 2015-2018 |
| [Hack The Box - Hardware](https://www.hackthebox.com/) | Hardware system hacking | Part of their broader CTF platform |
| [Ph0wn CTF](https://ph0wn.org/) | Smart devices/IoT | Jeopardy-style CTF dedicated to IoT, embedded systems, smartphones - local event in France but archives available |
| [IoT Village CTF (DEF CON)](https://www.iotvillage.org/) | Real IoT devices | DEF CON Black Badge awarded contest - exploits real-world vulnerabilities on actual devices (30+ devices) |

---

*Last Updated: January 2026*
