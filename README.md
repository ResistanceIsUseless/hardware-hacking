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
| [CBECSC23.md](CBECSC23.md) | Additional reference material |

---

*Last Updated: January 2026*
