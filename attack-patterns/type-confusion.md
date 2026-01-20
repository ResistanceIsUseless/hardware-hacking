# Type Confusion Vulnerability Guide

A practical guide for understanding and hunting type confusion vulnerabilities—where a program accesses a resource using an incompatible type, causing memory corruption or logic errors.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [C++ Type Confusion Deep Dive](#c-type-confusion-deep-dive)
  - [Casting Mechanics](#casting-mechanics)
  - [VTable Confusion](#vtable-confusion)
- [Browser (JIT) Type Confusion](#browser-jit-type-confusion)
  - [JavaScript Engine Optimization](#javascript-engine-optimization)
  - [Array Type Transitions](#array-type-transitions)
- [Adobe/PDF Type Confusion](#adobepdf-type-confusion)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Attack Surfaces](#attack-surfaces)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Type confusion occurs when a program allocates or initializes a resource (like an object or variable) as one type (Type A), but later accesses it as a different, incompatible type (Type B). This mismatch allows attackers to interpret data pointers as function pointers, integers as pointers, or bypass type-safe checks.

### Foundational Examples

| CVE | Product | Category | Impact |
|-----|---------|----------|--------|
| CVE-2015-0313 | Adobe Flash | ActionScript | RCE via type confusion |
| CVE-2018-8174 | VBScript Engine | Scripting | RCE (Double Kill) |
| CVE-2019-0567 | Microsoft Edge | Browser (Chakra) | RCE via JIT type confusion |
| CVE-2023-2033 | Google Chrome | Browser (V8) | RCE in V8 type inference |
| CVE-2016-1010 | Adobe Reader | PDF Parsing | RCE via invalid cast |

### Why These Bugs Keep Recurring

-   **Optimization complexity** — JIT compilers speculate on types for speed.
-   **Manual memory management** — C/C++ `void*` casts remove safety rails.
-   **Legacy codebases** — Older generic object handlers lack rigorous tagging.
-   **Object Polymorphism** — Complex inheritance hierarchies confuse casting logic.

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

MEMORY LAYOUT (Reality):
┌───────────────────────────┐
│ Object A (The "truth")    │
│ [ Integer : 0x41414141 ]  │  <-- Just a number
│ [ String  : "Hello"    ]  │
└───────────────────────────┘

CASTING OPERATION (The Lie):
Program takes pointer to Object A, but says: 
"Trust me, this is actually Object B"

INTERPRETATION (The vulnerability):
┌───────────────────────────┐
│ Object B (The "lie")      │
│ [ Function Ptr ] <---------- The program executes 0x41414141
│ [ ...          ]          │  as a code address!
└───────────────────────────┘

Result: Control Flow Hijacking or Memory Disclosure
```

### The Three Type Confusion Patterns

```
PATTERN 1: BAD CASTING (C++)
─────────────────────────────────────────────────────────
Base class pointer actually holds DerivedA.
Program casts it to DerivedB.
DerivedB accesses fields that exist in B but not A.

PATTERN 2: JIT OPTIMIZATION (Browsers)
─────────────────────────────────────────────────────────
1. JIT assumes variable 'x' is always an Integer array.
2. Generates optimized code without type checks.
3. Attacker uses side-effect to change 'x' to Object array.
4. Optimized code runs, treating Object pointer as Integer.

PATTERN 3: UNION CONFUSION
─────────────────────────────────────────────────────────
C Struct uses a Union (shares memory).
1. Store generic data in Union Field A (Integer).
2. Read data from Union Field B (Pointer).
3. Integer value becomes a memory address.
```

---

## C++ Type Confusion Deep Dive

C++ polymorphism allows objects to be treated as their parent classes. Vulnerabilities arise when downcasting (Parent -> Child) incorrectly.

### Casting Mechanics

```cpp
class Animal { public: virtual void speak() {} };
class Dog : public Animal { 
    public: int dogTag; 
    void bark() { ... } 
};
class Cat : public Animal { 
    public: void* exploitAddress; 
    void meow() { ... } 
};

// VULNERABLE CODE
void makeSpeak(Animal* anim) {
    // BLIND CAST: Assumes input is always a Dog
    Dog* d = static_cast<Dog*>(anim);
    
    // If anim is actually a Cat:
    // d->dogTag accesses Cat::exploitAddress memory!
    std::cout << d->dogTag; 
}

// SAFE CODE
void makeSpeakSafe(Animal* anim) {
    // CHECKS RTTI (Run-Time Type Information)
    Dog* d = dynamic_cast<Dog*>(anim);
    if (d == nullptr) return; // Cast failed, types didn't match
    d->bark();
}
```

*Note: `static_cast` is faster but unsafe because it simply tells the compiler "treat this pointer as type X". `dynamic_cast` checks specific runtime tags but is slower.*

### VTable Confusion

Virtual functions work via a VTable (table of function pointers). Confusion allows swapping VTables.

```
MEMORY LAYOUT 'Greeter' Object:
[ VTable Ptr ] -----> [ greet() func addr ]

MEMORY LAYOUT 'Gadget' Object:
[ VTable Ptr ] -----> [ system() func addr ]

ATTACK:
1. Create 'Greeter' object.
2. Trick program into confusing it with 'Gadget' object structure (or overwriting the ptr).
3. Call greeter->greet().
4. Actually calls system().
```

---

## Browser (JIT) Type Confusion

Browsers use Just-In-Time (JIT) compilers (V8 for Chrome, SpiderMonkey for Firefox) that optimize JavaScript by guessing types.

### JavaScript Engine Optimization

JS is dynamically typed, but CPU instructions are statically typed.

1.  **Observation**: The engine runs code like `func(arr) { return arr[0]; }`. It sees you always pass an Array of Integers (SMI).
2.  **Speculation**: "The user will probably *always* pass Array of Integers."
3.  **Optimization**: Compile machine code that reads memory directly, skipping the "Is this an integer?" check.
4.  **Guard Rails**: Insert a small check at the start. "If not Integer Array, de-optimize (bailout)."

### Array Type Transitions

The vulnerability happens when you can change the type *after* the guard check but *before* the memory access.

```javascript
/* CONCEPTUAL JIT EXPLOIT */

function vulnerable(arr, trigger) {
    // 1. JIT assumes 'arr' is [Double, Double]
    // 2. Guard Check: Is arr type Double Array? Yes.
    
    // 3. User code runs (The Side Effect)
    trigger.valueOf = function() {
        arr[0] = {}; // TRANSITION! Array is now [Object, Double]
        return 0;
    };
    
    // 4. Force side effect
    var x = trigger + 1; 
    
    // 5. VULNERABILITY
    // JIT code still thinks 'arr' is Double Array.
    // Reading arr[0] returns the Object address as a raw double.
    // MEMORY LEAK (Pointer Disclosure)
    return arr[0]; 
}
```

This gives the attacker the raw memory address of the Object, bypassing ASLR. The reverse allows writing arbitrary addresses to memory.

---

## Adobe/PDF Type Confusion

PDFs format is object-oriented. Dictionaries, Streams, references.

```
OBJECT 1 (Link Annotation):
<< /Type /Annot /Subtype /Link /A << ... >> >>

OBJECT 2 (Multimedia):
<< /Type /Rendition /Media ... >>
```

**The Vulnerability:**
The parser expects a `/Link` object to handle a click. The attacker provides a `/Rendition` object ID but contexts it where a Link is expected. The parser reads the `/Media` field offset, thinking it's reading the Link's `/A` (Action) field.

---

## Pattern Recognition: Where Else to Look

### Locations

```
Domain                 Vulnerability Source
─────────────────────────────────────────────────────────────
Browsers (JS Engines)  JIT Optimization phases (Typer, RangeAnalysis)
PDF Parsers            Object processing (U3D, XFA legacy forms)
Fonts (OpenType)       Table parsing (casting headers)
Kernel (Windows)       Win32k.sys object handling (Window vs Menu objects)
PHP/Python Core        Internal C structures (zval) handling
Video Decoders         Variable bitrate streaming objects
Serialized Data        Deserializing into wrong class (see Deserialization)
```

### Code Patterns (C/C++)

Search for dangerous casts close to usage:

```cpp
// 1. Static Casts on complex objects
static_cast<MyClass*>(ptr)

// 2. C-Style Casts (Brutal Force)
(MyClass*)ptr
reinterpret_cast<MyClass*>(ptr)

// 3. Void Pointer Retrieval
void* data = context->getData();
SpecificObj* obj = (SpecificObj*)data; // Assumption!

// 4. Union Usage
union {
    int   asInt;
    char* asPtr; // unsafe access
} u;
```

---

## Attack Surfaces

### Web Browsers
-   **V8 (Chrome/Node)**: `TurboFan` optimization pipeline.
-   **JavaScriptCore (Safari)**: `DFG` and `FTL` JIT compilers.
-   **SpiderMonkey (Firefox)**: `IonMonkey`.

### Kernels
-   **Windows win32k**: Historical hotbed of User Object vs Desktop Object confusion.
-   **Linux ebpf**: Verifier bugs where the kernel is confused about register types.

### File Format Parsers
-   **Image Parsers**: Metadata tags (EXIF) confusion.
-   **Archive Formats**: Header Interpretation.

---

## Tools & Methodology

### Fuzzing with Sanitizers
The standard way to catch these is compiling with AddressSanitizer (ASAN) and UndefinedBehaviorSanitizer (UBSAN).

```bash
# Compile target
clang++ -fsanitize=address,undefined -g target.cpp -o target

# UBSAN will shout if you cast wildly invalid types
# ASAN will shout if you access out of bounds due to confusion
```

### Static Analysis
Look for `static_cast` in inheritance trees where `dynamic_cast` should be used.
Look for `void*` context pointers that are cast to different types in different callbacks.

### Browser/JS methodologies
Use "Fuzzilli" (JavaScript fuzzer) or "Dharma" to generate JS code that forces unexpected type transitions.

---

## Legal & Ethical Considerations

### Do
-   Research on open-source engines (V8, WebKit) in test environments.
-   Report findings via vendor bug bounties (Chrome VRP is very active).

### Don't
-   Weaponize JIT bugs against users.
-   Target production kernels.

---

*Document Version: 1.0*
*Last Updated: January 2026*
