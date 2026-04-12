# InterlaceX

> Enhanced fork of Interlace — Turn single-threaded CLI tools into fast, multi-threaded powerhouses with CIDR, glob, and dash-range support.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL3-red.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

---

## 📌 Table of Contents

- [What's New](#-whats-new-in-interlacex)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Full CLI Reference](#-full-cli-reference)
  - [Input Options](#input-options)
  - [Command Options](#command-options)
  - [Output Options](#output-options)
  - [Variable Options](#variable-options)
- [Variable Replacements](#-variable-replacements)
- [Target Formats](#-target-formats)
- [Output Modes](#-output-modes)
- [Advanced Usage](#-advanced-usage)
  - [Blockers](#blockers)
  - [Blocks](#blocks)
  - [Exclusions](#exclusions)
  - [Proxy Rotation](#proxy-rotation)
  - [Random Files](#random-files)
  - [Repeat Mode](#repeat-mode)
- [Real-World Examples](#-real-world-examples)
- [Piping & Chaining](#-piping--chaining)
- [Tips & Gotchas](#-tips--gotchas)
- [Example Files](#-example-files)
- [Credits](#-credits)

---

## ✨ What's New in InterlaceX

| Feature | Description |
|---------|-------------|
| **Python 3.13+ Support** | Full compatibility with latest Python versions |
| **`--silent` Mode** | Show only command output — no banner, no thread info |
| **`--quiet` / `-q` Mode** | Completely suppress all output including command stdout |
| **`-V` / `--version`** | Quick version check without parsing other args |
| **Graceful Ctrl+C** | Clean shutdown via signal handling — no zombie processes |
| **Comma-Safe URLs** | URLs with commas in `-tL` files are treated as single targets |
| **stderr Suppression** | In quiet mode, subprocess stderr is also suppressed |
| **Progress Bar Fix** | Progress bar updates after task completion, not before |
| **Proxy Clone Fix** | `--repeat` with `-pL` now correctly rotates proxies each iteration |
| **Safe Random Dir** | `-random` with empty directory raises a clear error instead of crashing |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/0xhunster/InterlaceX.git
cd InterlaceX

# Install (standard)
pip install .

# OR using pipx (recommended — keeps dependencies isolated)
pipx install .

# Verify installation
interlacex -V
```

---

## 🚀 Quick Start

```bash
# Pipe a single target
echo "example.com" | interlacex -c 'nmap -sV _target_'

# Run against a target file
interlacex -tL targets.txt -c 'nmap -sV _target_'

# Multiple threads
interlacex -tL targets.txt -c 'nmap -sV _target_' -threads 20

# Silent mode — only show command output, pipe-friendly
interlacex -tL targets.txt -c 'dig +short _target_' --silent

# Quiet mode — suppress everything, just save output to files
interlacex -tL targets.txt -c 'nmap -sV _target_ -oN _output_/_target_.txt' -o ./scans -q
```

---

## 📖 Full CLI Reference

```
interlacex [input options] [command options] [output options] [variable options]
```

---

### Input Options

These control where targets come from.

| Flag | Argument | Description |
|------|----------|-------------|
| `-t` | `TARGET` | One or more targets, comma-separated inline |
| `-tL` | `FILE` | Path to a file containing targets, one per line |
| *(stdin)* | — | Pipe targets directly from another command |
| `-e` | `EXCLUSIONS` | Comma-separated targets or CIDRs to exclude |
| `-eL` | `FILE` | File containing exclusions, one per line |

**Details:**

**`-t TARGET`** — Accepts a single target or a comma-separated list. Supports all target formats (domain, IP, CIDR, glob, dash-range). Commas are treated as delimiters here.

```bash
interlacex -t example.com -c 'ping -c 1 _target_'
interlacex -t 192.168.1.1,192.168.1.2,10.0.0.1 -c 'ping -c 1 _target_'
interlacex -t 192.168.1.0/24 -c 'ping -c 1 _target_'
```

**`-tL FILE`** — Each line in the file is treated as one complete target. Commas are NOT treated as delimiters here, so URLs containing commas are safe.

```bash
interlacex -tL targets.txt -c 'curl -s _target_'
```

**stdin** — When no `-t` or `-tL` is given, InterlaceX reads targets from stdin. Useful for chaining tools.

```bash
cat domains.txt | interlacex -c 'dig +short _target_' --silent
subfinder -d example.com -silent | interlacex -c 'httpx -u _target_ -silent' --silent
```

**`-e EXCLUSIONS`** — Exclude specific targets. Supports the same formats as `-t` (comma-separated, CIDR, etc.).

```bash
interlacex -t 192.168.1.0/24 -e 192.168.1.1,192.168.1.254 -c 'nmap _target_'
```

**`-eL FILE`** — Exclude targets listed in a file, one per line.

```bash
interlacex -t 10.0.0.0/8 -eL do_not_scan.txt -c 'nmap _target_'
```

> ⚠️ `-t` and `-tL` are mutually exclusive. `-e` and `-eL` are mutually exclusive.

---

### Command Options

These control what gets executed and how.

| Flag | Argument | Default | Description |
|------|----------|---------|-------------|
| `-c` | `COMMAND` | — | A single shell command to run per target |
| `-cL` | `FILE` | — | A file containing multiple commands to run per target |
| `-threads` | `N` | `5` | Max number of concurrent threads |
| `-timeout` | `N` | `600` | Per-command timeout in seconds |
| `--repeat` | `N` | `1` | Number of times to repeat the full command set |

**Details:**

**`-c COMMAND`** — The command string to execute for each target. Use variable placeholders like `_target_`, `_port_`, etc. (see [Variable Replacements](#-variable-replacements)).

```bash
interlacex -t example.com -c 'nmap -sV _target_'
interlacex -t example.com -p 80,443 -c 'curl -I http://_target_:_port_'
```

> ⚠️ Wrap commands in single quotes to prevent shell from interpreting special characters before InterlaceX can.

**`-cL FILE`** — Run multiple commands per target from a file. Each line is one command. Lines starting with `_block:` or `_blocker_` are control directives (see [Advanced Usage](#-advanced-usage)).

```bash
interlacex -tL targets.txt -cL commands.txt -o ./output
```

> ⚠️ `-c` and `-cL` are mutually exclusive.

**`-threads N`** — Controls parallelism. Must be a positive integer. InterlaceX automatically caps the thread count to the total number of tasks if tasks < threads.

```bash
interlacex -tL targets.txt -c 'nmap _target_' -threads 50
```

> 💡 Higher thread counts are great for fast, I/O-bound tasks (HTTP checks, DNS). Lower counts are safer for heavy tools (nmap, nikto) to avoid overwhelming the network.

**`-timeout N`** — Maximum seconds a single command is allowed to run. After this, the process is killed. Must be a positive integer.

```bash
interlacex -tL targets.txt -c 'nmap -sV _target_' -timeout 120
```

**`--repeat N`** — Repeats the entire task set N times. Useful for continuous monitoring or brute-force-style repetition. Must be a positive integer. With `-pL`, proxies rotate correctly across repeats.

```bash
# Run the command set 3 times
interlacex -tL targets.txt -c 'curl -s _target_' --repeat 3

# Continuous proxy rotation across repeats
interlacex -tL targets.txt -pL proxies.txt -c 'curl -x _proxy_ _target_' --repeat 5
```

---

### Output Options

These control what is shown on the terminal.

| Flag | Description |
|------|-------------|
| `-o FOLDER` | Save output to a folder. Use `_output_` in commands to reference it |
| `-v` / `--verbose` | Show verbose/debug info including internal thread events |
| `--silent` / `-s` | Show only command stdout — hides banner, thread info, and progress bar |
| `--quiet` / `-q` | Suppress everything — no banner, no thread info, no command output |
| `--no-bar` / `-nb` | Hide progress bar and banner, but keep thread info and command output |
| `--no-color` / `-nc` | Strip all ANSI color codes from terminal output |
| `-V` / `--version` | Print version and exit immediately |

**Details:**

**`-o FOLDER`** — Creates an output directory variable accessible as `_output_` inside commands. InterlaceX does not create the folder itself — your command must do so if needed.

```bash
interlacex -tL targets.txt -c 'mkdir -p _output_ && nmap _target_ -oN _output_/_target_.txt' -o ./results
```

**`--verbose` / `-v`** — Shows extra internal information including when each task is added to the thread queue. Useful for debugging command execution order.

```bash
interlacex -t example.com -c 'echo _target_' -v
```

**`--silent` / `-s`** — Hides everything except the actual output of your commands. Ideal for piping results into another tool. Progress bar and banner are suppressed. Command stdout is still shown.

```bash
interlacex -tL targets.txt -c 'dig +short _target_' --silent | sort -u
```

**`--quiet` / `-q`** — Suppresses all output including command stdout and stderr. Use this when you are saving output to files with `-o` and don't want anything on screen.

```bash
interlacex -tL targets.txt -c 'nmap _target_ -oN _output_/_target_.txt' -o ./scans -q
```

**`--no-bar` / `-nb`** — Removes the progress bar and banner, but still shows thread info and command output. Good middle ground between default and silent.

```bash
interlacex -tL targets.txt -c 'nmap _target_' --no-bar
```

> ⚠️ `--verbose`, `--silent`, and `--quiet` are mutually exclusive — only one can be used at a time.

---

### Variable Options

These inject additional values into your commands via placeholder variables.

| Flag | Argument | Variable | Description |
|------|----------|----------|-------------|
| `-p` | `PORT(S)` | `_port_` | Port or ports to use in commands |
| `-rp` | `PORT` | `_realport_` | A secondary "real" port variable |
| `--proto` | `PROTO(S)` | `_proto_` | Protocol(s) to use in commands |
| `-pL` | `FILE` | `_proxy_` | File of proxies, rotated per task |
| `-random` | `DIR` | `_random_` | Directory of files — one is picked randomly per run |
| `--no-cidr` | — | — | Treat CIDR notation as a literal string, do not expand |

**Details:**

**`-p PORT`** — Injects a port into `_port_`. Supports comma-separated values or a dash range. Each port generates a separate task per target.

```bash
# Single port
interlacex -t example.com -p 443 -c 'curl https://_target_:_port_'

# Comma-separated — 3 tasks per target
interlacex -tL targets.txt -p 80,443,8080 -c 'curl http://_target_:_port_'

# Dash range — generates tasks for ports 8000 to 8010
interlacex -tL targets.txt -p 8000-8010 -c 'curl http://_target_:_port_'
```

**`-rp PORT`** — A second port variable `_realport_` for cases where you need to distinguish between an original port and a mapped/forwarded port.

```bash
interlacex -t example.com -p 8080 -rp 80 -c 'curl -H "Host: _target_:_realport_" http://_target_:_port_'
```

**`--proto PROTO`** — Injects protocol names into `_proto_`. Comma-separated for multiple values. Each protocol creates a separate task per target.

```bash
# Single protocol
interlacex -tL targets.txt --proto https -c '_proto_://_target_'

# Multiple protocols — 2 tasks per target
interlacex -tL targets.txt --proto http,https -c 'curl _proto_://_target_'
```

**`-pL FILE`** — File containing proxy addresses (one per line). Proxies are assigned to tasks in a round-robin rotation. Each task gets the next proxy in the cycle.

```bash
# proxies.txt contains one proxy per line: http://1.2.3.4:8080
interlacex -tL targets.txt -pL proxies.txt -c 'curl -x _proxy_ http://_target_'
```

**`-random DIR`** — Picks one random file from the given directory at startup and injects its path as `_random_` in all commands. Useful for wordlists or payloads. The directory must not be empty.

```bash
# Randomly pick one wordlist from ./wordlists/ and use it
interlacex -tL targets.txt -random ./wordlists -c 'ffuf -u http://_target_/FUZZ -w _random_'
```

**`--no-cidr`** — Disables automatic CIDR expansion. `192.168.1.0/24` will be passed to the command as-is instead of being expanded into 256 individual IPs.

```bash
interlacex -t 192.168.1.0/24 --no-cidr -c 'echo _target_'
# Output: 192.168.1.0/24 (not expanded)
```

---

## 🔄 Variable Replacements

Use these placeholders inside `-c` or `-cL` commands. InterlaceX replaces them at runtime.

| Variable | Source Flag | Description |
|----------|-------------|-------------|
| `_target_` | `-t` / `-tL` / stdin | The current target as-is |
| `_host_` | same as above | Alias for `_target_` — identical behavior |
| `_cleantarget_` | same as above | Target with `http://`, `https://`, and trailing `/` stripped. Slashes replaced with `-` |
| `_safe-target_` | same as above | Target wrapped in single quotes for shell-safe usage |
| `_output_` | `-o` | The output folder path |
| `_port_` | `-p` | Current port value |
| `_realport_` | `-rp` | Secondary port value |
| `_proto_` | `--proto` | Current protocol value |
| `_proxy_` | `-pL` | Current proxy (round-robin) |
| `_random_` | `-random` | Path to a randomly selected file from the directory |

**Examples:**

```bash
# _target_ vs _cleantarget_
# target = https://example.com/path
# _target_      → https://example.com/path
# _cleantarget_ → example.com-path

interlacex -t "https://example.com/path" -c 'echo _cleantarget_'

# _safe-target_ — wraps in quotes for shell safety
# target = example.com; rm -rf /
# _safe-target_ → 'example.com; rm -rf /'  (safely quoted)

interlacex -t "example.com" -c 'nmap _safe-target_'
```

---

## 🎯 Target Formats

InterlaceX supports multiple target specification formats.

| Format | Example | Result |
|--------|---------|--------|
| Single domain | `example.com` | 1 target |
| Single IP | `192.168.1.1` | 1 target |
| Comma-separated (with `-t`) | `a.com,b.com,c.com` | 3 targets |
| CIDR | `192.168.1.0/24` | 256 targets |
| Glob | `192.168.1.*` | 256 targets |
| Dash range | `192.168.1.1-50` | 50 targets |
| File (with `-tL`) | `targets.txt` | One target per line |
| stdin | `cat hosts.txt \| interlacex ...` | One target per line |

> ⚠️ When using `-tL`, each full line is treated as one target. Commas in URLs are safe and will **not** be split.

---

## 🔒 Output Modes

| Mode | Flag | Banner | Thread Info | Progress Bar | Command Output |
|------|------|--------|-------------|--------------|----------------|
| Default | *(none)* | ✅ | ✅ | ✅ | ✅ |
| No Bar | `--no-bar` | ❌ | ✅ | ❌ | ✅ |
| Verbose | `-v` | ✅ | ✅ + debug | ✅ | ✅ |
| Silent | `--silent` | ❌ | ❌ | ❌ | ✅ |
| Quiet | `--quiet` | ❌ | ❌ | ❌ | ❌ |

> 💡 Use `--silent` when piping results to another tool. Use `--quiet` when saving everything to files.

---

## 🔧 Advanced Usage

### Blockers

A `_blocker_` directive inside a command file forces all commands **after** it to wait until the command **immediately before** the blocker has finished. This is useful for setup steps.

**commands.txt:**
```
mkdir -p _output_/_target_/
_blocker_
nmap _target_ -oN _output_/_target_/nmap.txt
nikto --host _target_ > _output_/_target_/nikto.txt
```

**Execution order:**
1. `mkdir` runs first for all targets
2. Once `mkdir` completes → `nmap` and `nikto` run concurrently

```bash
interlacex -tL targets.txt -cL commands.txt -o ./results
```

---

### Blocks

A `_block:name_` directive wraps commands into a **sequential group**. Commands inside the block run one after another (not in parallel). The block is opened and closed with the same name tag.

**commands.txt:**
```
_block:setup_
mkdir -p _output_/_target_/
touch _output_/_target_/started.txt
_block:setup_
nmap _target_ -oN _output_/_target_/nmap.txt
gobuster dir -u http://_target_ -w common.txt -o _output_/_target_/gobuster.txt
```

**Execution order:**
1. `mkdir` runs
2. `touch` runs (waits for mkdir)
3. `nmap` and `gobuster` run in parallel (after block completes)

---

### Exclusions

Remove specific targets from the scan scope.

```bash
# Exclude single IPs using -e (comma-separated)
interlacex -t 192.168.1.0/24 -e 192.168.1.1,192.168.1.254 -c 'nmap _target_'

# Exclude a CIDR range
interlacex -t 10.0.0.0/8 -e 10.0.1.0/24 -c 'ping -c 1 _target_'

# Exclude from file
interlacex -t 192.168.0.0/16 -eL exclusions.txt -c 'nmap _target_'
```

**exclusions.txt:**
```
192.168.1.1
192.168.1.254
10.0.0.0/24
```

---

### Proxy Rotation

Proxies from `-pL` are assigned to tasks in round-robin order. Each task gets the next proxy in the list cyclically.

```bash
interlacex -tL targets.txt -pL proxies.txt -c 'curl -x _proxy_ http://_target_' -threads 10
```

**proxies.txt:**
```
http://proxy1.example.com:8080
http://proxy2.example.com:8080
socks5://proxy3.example.com:1080
```

> 💡 With `--repeat`, proxies continue rotating across repetitions — each new task gets the next proxy in the cycle.

---

### Random Files

The `-random` flag selects **one** random file from a directory at startup. That same file path is used for all tasks in the run via `_random_`.

```bash
# Pick one random wordlist for all targets
interlacex -tL targets.txt -random ./wordlists -c 'ffuf -u http://_target_/FUZZ -w _random_'
```

> ⚠️ The directory must contain at least one file. An empty directory will raise an error.

---

### Repeat Mode

`--repeat N` reruns the entire task set N times. Useful for continuous monitoring or scheduled retesting.

```bash
# Run the scan set 5 times
interlacex -tL targets.txt -c 'nmap -sV _target_' --repeat 5

# Combined with timeout for rate-limited retesting
interlacex -tL targets.txt -c 'curl -s _target_' --repeat 10 -timeout 30
```

---

## 📚 Real-World Examples

### Subdomain Enumeration

```bash
interlacex -tL domains.txt -c 'subfinder -d _target_ -silent -o _output_/_target_-subs.txt' \
    -o ./enum -threads 10 --silent
```

### HTTP Probing

```bash
interlacex -tL subdomains.txt -p 80,443,8080,8443 \
    -c 'curl -sk -o /dev/null -w "%{http_code} _target_:_port_\n" http://_target_:_port_' \
    --silent -threads 30
```

### Nmap Full Pipeline

```bash
interlacex -tL targets.txt \
    -c 'nmap -sV -sC -oN _output_/_cleantarget_.txt _target_' \
    -o ./nmap_results -threads 5 -timeout 300
```

### Nuclei Scanning with Silent Output

```bash
cat live_hosts.txt | interlacex \
    -c 'nuclei -u _target_ -silent -o _output_/_cleantarget_.txt' \
    -o ./nuclei_out --silent -threads 20
```

### SSL/TLS Audit

```bash
interlacex -tL targets.txt \
    -c 'testssl.sh --quiet _target_:443 > _output_/_cleantarget_-ssl.txt' \
    -o ./ssl_audits -threads 3 -timeout 180
```

### Directory Fuzzing with Random Wordlist

```bash
interlacex -tL live_hosts.txt -random ./wordlists \
    -c 'ffuf -u http://_target_/FUZZ -w _random_ -mc 200,301,302 -o _output_/_cleantarget_.json' \
    -o ./fuzz_results -threads 5
```

### Multi-Protocol Scanning

```bash
interlacex -tL targets.txt --proto http,https \
    -c 'curl -sk _proto_://_target_ -o _output_/_cleantarget_-_proto_.html' \
    -o ./web_results -threads 15
```

### Full Recon Pipeline

```bash
# Step 1: Subdomain discovery
cat domains.txt | interlacex -c 'subfinder -d _target_ -silent' --silent > all_subs.txt

# Step 2: HTTP probing
cat all_subs.txt | interlacex -c 'httpx -u _target_ -silent' --silent > live_hosts.txt

# Step 3: Vulnerability scanning
cat live_hosts.txt | interlacex -c 'nuclei -u _target_ -silent' --silent
```

---

## 🔗 Piping & Chaining

InterlaceX reads from stdin automatically when no `-t` or `-tL` is given. The `--silent` flag makes output clean for piping.

```bash
# Chain three tools
subfinder -d example.com -silent \
    | interlacex -c 'httpx -u _target_ -silent' --silent \
    | interlacex -c 'nuclei -u _target_ -silent' --silent

# Collect unique results
interlacex -tL domains.txt -c 'dig +short _target_' --silent | sort -u > resolved_ips.txt

# Filter and pipe
interlacex -tL targets.txt -c 'curl -sk -o /dev/null -w "%{http_code} _target_"' --silent \
    | grep "^200" | awk '{print $2}' > live_200.txt
```

---

## 💡 Tips & Gotchas

**Use single quotes around commands:**
```bash
# ✅ Correct — shell won't interpret _target_ early
interlacex -t example.com -c 'echo _target_'

# ❌ Wrong — shell may interpret variables before InterlaceX sees them
interlacex -t example.com -c "echo _target_"
```

**Thread count vs tool load:**
```bash
# Light tools — high threads OK
interlacex -tL targets.txt -c 'ping -c 1 _target_' -threads 100

# Heavy tools — keep threads low
interlacex -tL targets.txt -c 'nmap -A _target_' -threads 3
```

**Output mode for piping — always use `--silent`:**
```bash
interlacex -tL targets.txt -c 'dig +short _target_' --silent | grep -v "^$"
```

**Save output when using `-q`:**
```bash
# -q suppresses all screen output, always pair with file output in command
interlacex -tL targets.txt -c 'nmap _target_ -oN _output_/_target_.txt' -o ./scans -q
```

**CIDR with many IPs — set appropriate timeout:**
```bash
interlacex -t 10.0.0.0/16 -c 'ping -c 1 _target_' -threads 200 -timeout 5
```

---

## 📁 Example Files

### targets.txt
```
example.com
test.example.com
192.168.1.0/24
10.0.0.1-10
https://api.example.com
```

### commands.txt (simple)
```
nmap -sV _target_ -oN _output_/_cleantarget_-nmap.txt
nikto --host _target_ > _output_/_cleantarget_-nikto.txt
gobuster dir -u http://_target_ -w common.txt -o _output_/_cleantarget_-gobuster.txt
```

### commands.txt (with blocker)
```
mkdir -p _output_/_cleantarget_/
_blocker_
nmap -sV _target_ -oN _output_/_cleantarget_/nmap.txt
nikto --host _target_ > _output_/_cleantarget_/nikto.txt
gobuster dir -u http://_target_ -w common.txt -o _output_/_cleantarget_/gobuster.txt
```

### commands.txt (with block)
```
_block:init_
mkdir -p _output_/_cleantarget_/
echo "Started: _target_" > _output_/_cleantarget_/status.txt
_block:init_
nmap -sV _target_ -oN _output_/_cleantarget_/nmap.txt
nikto --host _target_ > _output_/_cleantarget_/nikto.txt
```

### proxies.txt
```
http://proxy1.example.com:8080
http://proxy2.example.com:3128
socks5://proxy3.example.com:1080
```

### exclusions.txt
```
192.168.1.1
192.168.1.254
10.0.0.0/24
```

---

## 🙏 Credits

**Original Authors:**
- Michael Skelton ([@codingo_](https://twitter.com/codingo_))
- Sajeeb Lohani ([@sml555_](https://twitter.com/sml555_))

**Fork Maintainer:**
- 0xhunster ([@0xhunster](https://github.com/0xhunster))

---

## 📄 License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for full text.
