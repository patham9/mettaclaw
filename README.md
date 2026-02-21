## MeTTaClaw

An agentic AI system implemented in MeTTa, guided by the MeTTaClaw proposal and an agent core inspired by Nanobot.
Beyond basic tool use, it features embedding-based long-term memory represented entirely in MeTTa AtomSpace format.

Long-term memory is maintained by the agent via `remember(string)` for adding memory items and `query(string)` for querying related memories.
The agent can learn and apply new skills and declarative knowledge through the use of memory items.

In addition, an initial set of OpenClaw-like tools is implemented, including web search, file modification, communication channels, and access to the operating system shell and its associated tools.

Simplicity of design, ease of prototyping, ease of extension, and transparent implementation in MeTTa were the primary design criteria.
The agent core comprises approximately 200 lines of code.

**Installation**

First, get [SWI-Prolog](https://www.swi-prolog.org/). Then:

```
git clone https://github.com/trueagi-io/PeTTa
cd PeTTa
mkdir -p repos && git clone https://github.com/patham9/mettaclaw repos/mettaclaw
```

**Usage**

```
cd repos/mettaclaw
OPENAI_API_KEY=... sh ../../run.sh run.metta
```

**Auto-install/run**

Alternatively, if PeTTa is already installed and the latest version pulled (v1.0.2 or latest commit), then running the following MeTTa file installs and runs MeTTaClaw:

```
!(import! &self (library lib_import))
!(git-import! "https://github.com/patham9/mettaclaw.git")
!(import! &self (library mettaclaw lib_mettaclaw))

!(mettaclaw)
```
