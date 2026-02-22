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

Run the system via the following command which ensures the system is started from the root folder of PeTTa:

```
cp repos/mettaclaw/run.metta ./
OPENAI_API_KEY=... sh run.sh run.metta
```

**Auto-install/run**

Alternatively, if PeTTa is already installed and the latest version pulled (v1.0.2 or latest commit), then, running the following MeTTa file from the root folder, installs and runs MeTTaClaw (assuming OPENAI_API_KEY is set):

```
!(import! &self (library lib_import))
!(git-import! "https://github.com/patham9/mettaclaw.git")
!(import! &self (library mettaclaw lib_mettaclaw))

!(mettaclaw)
```

**Illustrations**

Long-Term Memory Recall:

<img width="638" height="125" alt="image" src="https://github.com/user-attachments/assets/0d4817ed-e743-4e44-8bd4-a10e27ea6380" />

Tool use:

<img width="1323" height="188" alt="image" src="https://github.com/user-attachments/assets/18ef19c4-010a-4c94-84ce-bb49277dccfc" />

Shell output of the actual invocation of the generated MeTTa code:

<img width="416" height="486" alt="image" src="https://github.com/user-attachments/assets/f5b27205-cdb2-47e7-821a-ffd93b3dd7c6" />

System also added it into its Atom Space storage (embedding vector omitted):

<img width="379" height="69" alt="image" src="https://github.com/user-attachments/assets/6aa59deb-33b4-42b9-a535-ae153b4b7a18" />




