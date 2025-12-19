# InterlaceX

> Enhanced fork of Interlace - Turn single-threaded CLI apps into fast, multi-threaded tools with CIDR and glob support.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL3-red.svg)](https://www.gnu.org/licenses/gpl-3.0.en.html)

## ✨ What's New in InterlaceX

| Feature | Description |
|---------|-------------|
| **Python 3.13+ Support** | Full compatibility with latest Python versions |
| **`--silent` Mode** | Show only command output (no banner, no thread info) |
| **`--quiet` / `-q` Mode** | Completely suppress all output |
| **`-V` / `--version`** | Quick version check |
| **Graceful Ctrl+C** | Clean shutdown with signal handling |
| **Comma-Safe URLs** | URLs with commas in `-tL` files work correctly |
| **Update Progress Bar** | Progress bar writes to stderr, doesn't mix with output |



## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/0xhunster/InterlaceX.git
cd InterlaceX

# Install
pip install .

# OR using pipx (Recommended for isolation)
pipx install .

# Verify installation
interlacex -V
```

## 🚀 Quick Start

```bash
# Basic usage - run command for each target
echo "example.com" | interlacex -c 'echo _target_'

# From file
interlacex -tL targets.txt -c 'echo _target_'

# Silent mode - only output
interlacex -tL targets.txt -c 'nmap -sV _target_' --silent

# Quiet mode - no output at all
interlacex -tL targets.txt -c 'nmap -sV _target_ -oN _target_.txt' -q
```



## 📖 Usage

```
interlacex [options]
```

### Input Options

| Flag | Description |
|------|-------------|
| `-t TARGET` | Single target or comma-separated targets |
| `-tL FILE` | File containing targets (one per line) |
| `(stdin)` | Pipe targets from another command |
| `-e EXCLUSIONS` | Targets to exclude |
| `-eL FILE` | File containing exclusions |

### Command Options

| Flag | Description |
|------|-------------|
| `-c COMMAND` | Single command to execute |
| `-cL FILE` | File containing commands |
| `-threads N` | Maximum concurrent threads (default: 5) |
| `-timeout N` | Timeout per command in seconds (default: 600) |
| `--repeat N` | Repeat the command set N times |

### Output Options

| Flag | Description |
|------|-------------|
| `-o FOLDER` | Output folder (use `_output_` in commands) |
| `-v` / `--verbose` | Show verbose output |
| `--silent` | Show only command output (no banner/thread info) |
| `-q` / `--quiet` | Suppress all output including command output |
| `--no-bar` | Hide progress bar and banner |
| `--no-color` | Disable colored output |
| `-V` / `--version` | Show version and exit |

### Variable Options

| Flag | Description |
|------|-------------|
| `-p PORT` | Port(s) to use as `_port_` variable |
| `-rp PORT` | Real port as `_realport_` variable |
| `--proto PROTO` | Protocol(s) as `_proto_` variable |
| `-pL FILE` | Proxy list file |
| `-random DIR` | Directory for random file selection |
| `--no-cidr` | Don't expand CIDR notation |



## 🔄 Variable Replacements

| Variable | Replacement |
|----------|-------------|
| `_target_` | Current target |
| `_host_` | Same as `_target_` |
| `_cleantarget_` | Target without http:// or https:// |
| `_safe-target_` | Target with special chars escaped |
| `_output_` | Output folder from `-o` |
| `_port_` | Current port from `-p` |
| `_realport_` | Real port from `-rp` |
| `_proto_` | Protocol from `--proto` |
| `_proxy_` | Current proxy from `-pL` |
| `_random_` | Random file from `-random` |



## 📚 Examples

### Basic Scanning

```bash
# Run nmap on multiple targets
interlacex -tL targets.txt -c 'nmap -sV _target_ -oN _output_/_target_.txt' -o ./scans -threads 10

# Run with specific ports
interlacex -t example.com -p 80,443,8080 -c 'curl -I http://_target_:_port_'
```

### Using CIDR Notation

```bash
# Expand CIDR and run command on each IP
interlacex -t 192.168.1.0/24 -c 'ping -c 1 _target_' -threads 50
```

### Using Glob Notation

```bash
# Expand glob range
interlacex -t 192.168.1.* -c 'nmap -sP _target_'
```

### Using Dash Notation

```bash
# Expand dash range
interlacex -t 192.168.1.1-50 -c 'curl -I http://_target_'
```

### Silent Mode (Clean Output)

```bash
# Only show command output - perfect for piping
interlacex -tL targets.txt -c 'echo _target_' --silent | sort -u > unique_targets.txt
```

### Multiple Commands

Create a file `commands.txt`:
```
nikto --host _target_:_port_ > _output_/_target_-nikto.txt
sslscan _target_:_port_ > _output_/_target_-sslscan.txt
```

Run:
```bash
interlacex -t example.com -cL commands.txt -p 80,443 -o ./results
```

### Bug Bounty Recon

```bash
# Subfinder + httpx + nuclei pipeline
cat domains.txt | interlacex -c 'subfinder -d _target_ -silent' --silent | \
    httpx -silent | interlacex -c 'nuclei -u _target_ -silent' --silent
```

### Web Fuzzing

```bash
# Run ffuf on multiple targets
interlacex -tL live_hosts.txt -c 'ffuf -u _target_/FUZZ -w wordlist.txt -o _output_/_cleantarget_.json' -o ./ffuf_results -threads 5
```

### SSL/TLS Scanning

```bash
# Run testssl.sh on multiple hosts
interlacex -tL targets.txt -c 'testssl.sh _target_:443 > _output_/_target_-ssl.txt' -o ./ssl_scans -threads 3
```

### Port Scanning with Output

```bash
# Masscan + Nmap combo
interlacex -t 10.0.0.0/24 -c 'masscan _target_ -p1-65535 --rate=1000 -oL _output_/_target_-masscan.txt' -o ./scans -threads 10
```



## 🔧 Advanced Usage

### Blockers

Blockers prevent commands below them from running until all above commands complete:

```
mkdir -p _output_/_target_/
_blocker_
nmap _target_ -oN _output_/_target_/nmap.txt
nikto --host _target_ > _output_/_target_/nikto.txt
```

### Blocks

Blocks force sequential execution within them:

```
_block:setup_
mkdir -p _output_/_target_/
touch _output_/_target_/started.txt
_block:setup_
nmap _target_ -oN _output_/_target_/nmap.txt
```

### Exclusions

```bash
# Scan subnet but exclude specific IPs
interlacex -t 192.168.1.0/24 -e 192.168.1.1,192.168.1.254 -c 'nmap _target_'

# Exclude from file
interlacex -t 10.0.0.0/16 -eL exclusions.txt -c 'ping -c 1 _target_'
```

### Using Proxies

```bash
# Rotate through proxy list
interlacex -tL targets.txt -pL proxies.txt -c 'curl -x _proxy_ http://_target_'
```



## 📁 Example Files

### targets.txt
```
example.com
test.example.com
192.168.1.0/24
10.0.0.1-10
```

### commands.txt
```
nmap -sV _target_ -oN _output_/_target_-nmap.txt
nikto --host _target_ > _output_/_target_-nikto.txt
gobuster dir -u http://_target_ -w common.txt -o _output_/_target_-gobuster.txt
```



## 🔒 Output Modes Comparison

| Mode | Banner | Thread Info | Progress Bar | Command Output |
|------|--------|-------------|--------------|----------------|
| Default | ✅ | ✅ | ✅ | ✅ |
| `--no-bar` | ❌ | ✅ | ❌ | ✅ |
| `--silent` | ❌ | ❌ | ❌ | ✅ |
| `--quiet` / `-q` | ❌ | ❌ | ❌ | ❌ |



## 🙏 Credits

**Original Authors:**
- Michael Skelton ([@codingo_](https://twitter.com/codingo_))
- Sajeeb Lohani ([@sml555_](https://twitter.com/sml555_))

**Fork Maintainer:**
- 0xhunster

## 📄 License

GNU General Public License v3.0
