# Attack Pattern Guides

Educational guides focused on understanding the **fundamental patterns** behind common vulnerability classes. Each guide distills the core concept to help you recognize the same pattern across different contexts and technologies.

## Philosophy

These guides teach the **transferable pattern**, not just specific exploits. Once you understand the core concept, you can recognize it in:

- New technologies
- Different programming languages
- Novel attack surfaces

## Pattern Catalog

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

## Guide Structure

Each pattern guide follows a consistent structure:

1. **Title and Overview** - Clear description of the fundamental pattern
2. **Foundational Examples** - Real-world CVEs demonstrating the pattern (e.g., Heartbleed, Wallbleed)
3. **Deep Dive** - Byte-level analysis showing how the vulnerability works
4. **Pattern Recognition** - Where else this appears, common variants
5. **Attack Surfaces** - Categories of products/systems affected
6. **Lab Setup & Methodology** - How to research/test safely
7. **Tools Reference** - Static/dynamic analysis tools
8. **Legal & Ethical Considerations** - Authorized testing requirements

## Cross-References

Patterns often overlap and relate to each other:

- **Memory Disclosure** + **Canonicalization** → Path traversal with length manipulation
- **Parser Differential** + **Semantic Gap** → Multi-layer interpretation bugs
- **Type Confusion** + **Reference Confusion** → Memory safety issues
- **TOCTOU** + **State Confusion** → Race conditions in state machines

## Usage Notes

- These patterns apply to both **software** and **hardware** vulnerabilities
- Understanding these patterns helps with both **offensive** (pentesting, bug bounty) and **defensive** (secure code review, architecture design) security
- All techniques documented here are for **authorized testing only** - see individual guides for legal/ethical sections

---

*For hardware-specific security topics, see the [hardware guides](../) at repository root.*
