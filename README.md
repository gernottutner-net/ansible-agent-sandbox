# A sandbox for agentic coding on VirtualBox

An Ansible collection, `tutner.agent_sandbox`, for a sandbox for agentic
coding with Claude Code **on VirtualBox**, end to end: it creates the
Debian 13 VM on your VirtualBox host, snapshots and destroys it, and turns
it into the sandbox: rootless Podman under a sudo-less account, default-deny
egress through Squid with nftables behind it, and Claude Code in a pinned
image with its strict inner sandbox switched on by managed settings no
session can loosen.

VirtualBox is the only platform it supports, and the only one it is tested
on: a Debian 13 guest under VirtualBox 7.0, on an Ubuntu 22.04 host.

> **The sandbox belongs in the disposable VM this collection creates, never
> on bare metal or on a machine you care about.** Against a kernel exploit
> from inside the container, the VM is the boundary: nothing in this
> collection replaces it. Snapshot the VM before a session you do not trust,
> and roll it back after.

---

## Contents

- [What you get](#what-you-get)
- [Requirements](#requirements)
- [Install](#install)
- [Configure](#configure)
- [Create the VM and the sandbox](#create-the-vm-and-the-sandbox)
- [Check the sandbox](#check-the-sandbox)
- [Snapshots and teardown](#snapshots-and-teardown)
- [Sessions](#sessions)
  - [The launcher](#the-launcher)
  - [Autonomous mode](#autonomous-mode)
  - [Logging in](#logging-in)
  - [Getting a project in](#getting-a-project-in)
  - [Claude Code's own sandbox](#claude-codes-own-sandbox)
- [Egress](#egress)
- [Updating Claude Code](#updating-claude-code)
- [What it protects, and what not](#what-it-protects-and-what-not)
- [Open questions](#open-questions)
- [Licence](#licence)

---

## What you get

Four roles. `virtualbox_vm` runs on the VirtualBox host, from the playbooks
`provision`, `wait`, `snapshot` and `destroy`. The other three configure the
guest over SSH, in this order, from the playbook `sandbox`.

| Role | What it does |
|---|---|
| `virtualbox_vm` | The VM from Debian's checksum-verified cloud image: a NAT and a host-only NIC with pinned MACs, a cloud-init seed with an `ansible` account and your key, headless start; snapshots with one rolling slot plus a baseline; teardown. Details in [docs/virtualbox.md](docs/virtualbox.md). |
| `podman` | Podman with crun and pasta; a sudo-less user `agent` with a pinned subuid range, lingering, and delegated cgroup v2 limits. Asserts no sudo rights and no overlapping ranges. |
| `egress_proxy` | Squid with a default-deny allowlist, and an nftables rule on `agent`'s uid that makes Squid the only way out. Probes an allowed host, a denied one and a bypass on every run. |
| `agentbox` | The image (Debian, Node, a pinned Claude Code), Claude Code's managed settings, and the launcher `/usr/local/bin/agentbox`, the only supported way to start a session. |

Every role checks what it set up before it finishes, so a run that passes
has been observed denying, not only configured to. The layers they build,
and why Debian 13 and rootless Podman rather than the host's own system or
Docker, are in [docs/design.md, "The layers"](docs/design.md#the-layers).

## Requirements

On the VirtualBox host, which is also where Ansible runs:

- VirtualBox 7.0 with `vboxdrv` loaded, and a host-only interface
  (`vboxnet0`, `192.168.56.1/24`).
- `qemu-img` and `cloud-localds`: `sudo apt install qemu-utils cloud-image-utils`.
- `ansible-core` 2.17 or newer.
- An SSH key pair for the VM.
- Room for the VM: 6 GB RAM, 4 CPUs and a 40 GB disk by default.

The provision playbook checks all of these before it touches anything,
including the KVM conflict of host kernels 6.8 and newer. Setting them up
is in [docs/virtualbox.md](docs/virtualbox.md#the-virtualbox-host).

The VM gets two NICs: NAT for the way out, and host-only for SSH and for
Squid, which cannot listen on the NAT address, because a pasta container
carries a copy of that one as its own.

## Install

```bash
ansible-galaxy collection install git+https://github.com/gernottutner-net/ansible-agent-sandbox.git
```

Or pin a release in `requirements.yml`:

```yaml
collections:
  - name: https://github.com/gernottutner-net/ansible-agent-sandbox.git
    type: git
    version: v0.1.0
```

## Configure

Copy `examples/` from this repository into a working directory and adapt
it:

- `inventory.yml`: the VM, in the group `agent_sandbox`.
- `host_vars/sandbox-vm.yml`: the VM's host-only address, its two MACs,
  its SSH key, and optionally its size.
- `group_vars/all.yml`: sudo for the `ansible` account cloud-init creates.
- `group_vars/agent_sandbox.yml`: the policy: the allowlist, the limits
  (memory, CPUs, processes), the image tag and Claude Code's version, and
  environment for Claude Code, which every command Claude runs can read: no
  credentials there.
- `ansible.cfg`: pipelining, so Ansible can become the sandbox user, and
  only the VM's own key offered.

## Create the VM and the sandbox

```bash
ansible-playbook tutner.agent_sandbox.provision    # the VM, until cloud-init is done
ansible-playbook tutner.agent_sandbox.sandbox      # the sandbox inside it
```

`provision` skips a VM that exists and starts it if it is off. `sandbox`
takes the tags `podman`, `egress` and `agentbox`; a second run reports
`changed=0`, and `--check --diff` shows what a run would change.

## Check the sandbox

The roles check their own work on every run. These smoke tests check it
once more from where a session sits, inside a container. Run them once
after the first `sandbox` run, as `agent` on the VM (`ssh` in as
`ansible`, then `sudo -iu agent`). Containers get the proxy from Podman's
`containers.conf`, as `$https_proxy`.

```bash
img=docker.io/library/debian:trixie-slim

# Limits bind: expect 2147483648
podman run --rm --memory=2g $img cat /sys/fs/cgroup/memory.max

# An allowlisted host works through the proxy: expect the package lists
podman run --rm $img apt-get update

# A host not on the list: expect Squid's "HTTP/1.1 403 Forbidden"
podman run --rm $img bash -c '
  p=${https_proxy#http://}; p=${p%/}
  exec 3<>/dev/tcp/${p%:*}/${p##*:}
  printf "CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n" >&3
  head -1 <&3'

# Bypassing the proxy: expect "Connection refused", never OPEN
podman run --rm $img bash -c 'timeout 10 bash -c "exec 3<>/dev/tcp/1.1.1.1/443" && echo OPEN'

# No resolver: expect no output, exit code 2
podman run --rm $img getent hosts deb.debian.org; echo $?

# The launcher: expect uid 1000 (dev), the limits from your policy
# (memory, pids, CPU quota), and the pinned Claude Code version
agentbox smoke bash -c 'id; cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/pids.max /sys/fs/cgroup/cpu.max; claude --version' < /dev/null
rmdir ~/projects/smoke ~/.agentbox/smoke
```

`debian:trixie-slim` has no `curl`, so the raw tests use bash's
`/dev/tcp`. The bypass test is the one that matters: a default-deny that
has never been observed denying anything is not a default-deny. The last
line removes the directories the launcher created for the project `smoke`,
so they do not end up in the baseline.

Then take the baseline snapshot, before the first session:

```bash
ansible-playbook tutner.agent_sandbox.snapshot -e snapshot_action=take -e snapshot_name=base
```

## Snapshots and teardown

```bash
ansible-playbook tutner.agent_sandbox.snapshot                                   # list
ansible-playbook tutner.agent_sandbox.snapshot -e snapshot_action=take -e snapshot_name=pre-session
ansible-playbook tutner.agent_sandbox.snapshot -e snapshot_action=restore -e snapshot_name=pre-session
ansible-playbook tutner.agent_sandbox.destroy                                    # asks first
```

`take` keeps the newest snapshot and the baseline, the root of the tree,
and merges the rest away; the guest is shut down for it, so no RAM state is
saved. `take` and `restore` restart a VM that was running, and return once
it answers over SSH again. `destroy` deletes the VM with all its disks and
snapshots. With more than one VM, add `--limit <vm>`. Details in
[docs/virtualbox.md](docs/virtualbox.md#snapshots).

## Sessions

### The launcher

As `agent` on the VM (`ssh` in as `ansible`, then `sudo -iu agent`):

```bash
agentbox <project>              # Claude Code in /work
agentbox <project> bash         # a shell instead, e.g. to clone first
```

- `<project>` is a plain name: letters, digits, `.`, `_`, `-`, starting
  with a letter or digit. The launcher creates `~/projects/<project>`
  (mounted at `/work`) and `~/.agentbox/<project>` (Claude Code's login and
  state) on first use.
- One session per project at a time: the container is named
  `agentbox-<project>`, and a second one is refused. Sessions in different
  projects run side by side; two at once, each cloning a repository and
  running `npm install`, peaked at about 310 MB each of their 2 GiB, on a
  6 GB VM.
- Everything outside `/work` and Claude Code's state is gone when the
  session ends (`--rm`).
- The run policy is rendered into the launcher, not read from the
  environment or the command line: `--cap-drop=ALL`,
  `no-new-privileges`, the memory, CPU and process limits, no swap, the
  read-only managed settings. No invocation can forget one.

### Autonomous mode

```bash
agentbox --auto <project>                   # no permission prompts
agentbox --auto <project> -p '<task>'       # unattended: runs the task, then exits
```

`--auto` starts Claude Code with `--dangerously-skip-permissions`; further
arguments go to `claude`. Claude asks nothing, so the boundary is what the
VM enforces: the container, Squid, the limits and Claude Code's strict
sandbox. `--auto` sessions get no claude.ai connectors
(`agentbox_auto_claude_env`).

For unattended runs: put the task in single quotes; add `< /dev/null` to
skip the wait for stdin; add `--verbose --output-format stream-json` and
redirect to a file to see which tools Claude called.

### Logging in

The first session in a project asks for the Claude login: open the URL it
prints in a browser and paste the code back. The login is kept per
project, so projects never see each other's login or transcripts.

Optional, an API key instead: create a Podman secret `anthropic_api_key` as
`agent`, and the launcher passes it on, as the environment variable
`ANTHROPIC_API_KEY`. Treat it as readable by every command Claude runs (see
[What it protects, and what not](#what-it-protects-and-what-not)): a key of
its own, with a spending limit.

```bash
read -rs t && printf %s "$t" | podman secret create anthropic_api_key - && unset t
```

### Getting a project in

Clone inside the session, over HTTPS through the proxy. Only allowlisted
hosts work, and there are no SSH keys in the sandbox.

```bash
agentbox myproj bash
git clone https://github.com/<owner>/<repo>.git .      # inside, in /work
exit
agentbox myproj
```

### Claude Code's own sandbox

Always on, in every session and both modes, set by managed settings that
the launcher mounts read-only. They rank above every other settings file,
so neither `/sandbox` nor a project's `.claude/settings*.json` can switch
it off or widen it. For the commands Claude runs:

- they run inside the sandbox without a prompt, and cannot be retried
  outside it;
- they write only in `/work`, temp directories and the paths in
  `agentbox_sandbox_allow_write`, never to Claude Code's settings or the
  project's `.claude/`;
- they cannot read the login;
- they reach only the hosts on `egress_allowlist`, the same list as Squid.

Deny rules keep Claude's Read and Edit tools off the login and the
settings. Commands you type yourself at Claude Code's `!` prompt are not
sandboxed.

## Egress

Everything `agent` sends goes through Squid, which allows only the hosts in
`egress_allowlist`. A direct connection past Squid is dropped by nftables,
and no DNS resolver is reachable. See what was refused:

```bash
sudo grep TCP_DENIED /var/log/squid/access.log | tail -20
```

To allow a host, first decide whether it should be reachable at all: every
entry is also a way out for data. Add it to `egress_allowlist`, prefer the
exact host over a leading dot, and apply with `--tags egress,agentbox`:
both, because Squid and Claude Code's sandbox each get the list.

`DISABLE_TELEMETRY=1` and `DISABLE_ERROR_REPORTING=1` in the example policy
keep Claude Code from trying its telemetry and error-reporting hosts, which
are not on the allowlist. `downloads.claude.ai` stays denied: Claude Code falls
back to cloning its plugin marketplace from GitHub, and updates come only
from an image rebuild.

## Updating Claude Code

The image holds a pinned Claude Code and never updates itself. Change both
values and apply with `--tags agentbox`:

```yaml
sandbox_image_tag: "0.2.0"                 # a new tag, never reuse one
agentbox_claude_code_version: "2.x.y"
```

The role refuses to rebuild an existing tag from a changed recipe, so a
forgotten tag bump fails loudly. Going back: set both values back; the old
image is still there.

## What it protects, and what not

It keeps a session away from the controller's SSH keys, from other
projects and their logins, and from the account Ansible uses; an escape
from the container lands in a sudo-less account. It does not:

- **stop a kernel exploit.** The container runs on the VM's kernel; the VM
  is the boundary.
- **keep the login unreadable to an escape.** The Claude login is
  long-lived, good for the whole account, and kept in plain files under
  `~/.agentbox/<project>`. After a suspect session: log the sandbox's
  sessions out on claude.ai, delete the project's state directory, and
  restore the VM's snapshot.
- **keep the session's environment from the commands Claude runs.** Every
  command inherits it: whatever is in `agentbox_claude_env` or
  `agentbox_auto_claude_env`, and the API key if there is one, is a
  `printenv` away. Command lines are readable too, through the container's
  `/proc`, Claude's prompt among them. What commands cannot read is another
  process's environment, nor the login, which Claude Code's sandbox denies
  them as a file. So a credential never goes into the environment or onto a
  command line.
- **prevent leaks to allowed hosts.** The allowlist says which
  organisations the agent may talk to, not what it may say: a gist on
  github.com is as reachable as the rest of github.com.

Why each layer is built the way it is, the findings behind it, and the
decisions it rests on are in [docs/design.md](docs/design.md). What was
tested before a release, and what the tests found, is in
[docs/release-tests.md](docs/release-tests.md).

## Open questions

Not yet tested, and not claimed:

1. **Heavier work in two concurrent sessions.** Two sessions doing a clone
   and `npm install` fit with room to spare; builds and test suites were
   not measured.
2. **`ANTHROPIC_API_KEY` withheld by name.** The environment was tested with a
   variable of another name; whether Claude Code keeps its API key variable
   from its commands is not known. Assume it does not.

## Licence

MIT, see [LICENSE](LICENSE).
