# sacVB: a sandbox for agentic coding on VirtualBox

![sacVB, sandbox for agentic coding on VirtualBox: a hooded robot with red eyes sits at a desk behind prison bars, its terminal answering `sudo: not found`, under a "World domination (pending approval)" poster: a disposable VM, rootless Podman and an egress allowlist](docs/images/README_banner.png)

**sacVB** — sandbox for agentic coding on VirtualBox —
is an Ansible collection, `tutner.agent_sandbox`, for a sandbox for agentic
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
- [Updating the collection](#updating-the-collection)
  - [What an update needs](#what-an-update-needs)
- [Configure](#configure)
- [Create the VM and the sandbox](#create-the-vm-and-the-sandbox)
- [Check the sandbox](#check-the-sandbox)
- [Snapshots and teardown](#snapshots-and-teardown)
- [Starting and stopping the VM](#starting-and-stopping-the-vm)
- [Tuning the VM](#tuning-the-vm)
- [Sessions](#sessions)
  - [The launcher](#the-launcher)
  - [Sessions that outlive the connection](#sessions-that-outlive-the-connection)
  - [From the controller](#from-the-controller)
  - [Autonomous mode](#autonomous-mode)
  - [Logging in](#logging-in)
  - [Getting a project in](#getting-a-project-in)
  - [Repository tokens](#repository-tokens)
  - [Claude Code's own sandbox](#claude-codes-own-sandbox)
  - [Agent Intercom](#agent-intercom)
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
| `agentbox` | The image (Debian, Node, a pinned Claude Code), Claude Code's managed settings, and the launcher `/usr/local/bin/agentbox`, the only supported way to start a session. With the playbook `git_token`, it also hands a project its [repository tokens](#repository-tokens). With links in the inventory, it also sets up the [Agent Intercom](#agent-intercom), so sessions can talk to each other. |

Every role checks what it set up before it finishes, so a run that passes
has been observed denying, not only configured to. The layers they build,
and why Debian 13 and rootless Podman rather than the host's own system or
Docker, are in [docs/design.md, "The layers"](docs/design.md#the-layers).
A [diagram](docs/images/architecture.svg) shows how they fit together.
An [interactive version](https://claude.ai/artifact/4NNqLqhHufJfLtWW1r5ue6)
explains each part when you click it, and sends a request through the
layers to show which one stops it.

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

You don't need an existing Ansible project. The collection is a package:
installed once, it can be used from any directory. Install a release, by
its tag:

```bash
ansible-galaxy collection install git+https://github.com/gernottutner-net/ansible-agent-sandbox.git,v0.5.0
```

A tag is the commit that passed the release tests, and is never moved.
Without `,v0.5.0`, you get `main`: what comes next, not tested as a
release, and still reporting the last release's version.

It goes into the first entry of Ansible's collections path, by default
`~/.ansible/collections/ansible_collections/tutner/agent_sandbox/`, for
your user only. `-p <dir>` installs it somewhere else; that directory must
then be on `collections_path` in `ansible.cfg`.
`ansible-galaxy collection list tutner.agent_sandbox` shows where it is and
which version.

Or pin the release in `requirements.yml`, for example in an Ansible project
you already have, and install it with
`ansible-galaxy collection install -r requirements.yml`:

```yaml
collections:
  - name: https://github.com/gernottutner-net/ansible-agent-sandbox.git
    type: git
    version: v0.5.0
```

## Updating the collection

A new release is installed the same way, over the old one:

1. Read the release's notes on GitHub, or its entry in
   [CHANGES.md](CHANGES.md): "Action needed on an existing install" says
   what to change in your files first, such as a new image tag.
2. Snapshot the VM, so you can go back:

   ```bash
   ansible-playbook tutner.agent_sandbox.snapshot -e snapshot_action=take -e snapshot_name=pre-update
   ```

3. Install the new version, pinned to its tag, or with the new `version:`
   in your `requirements.yml` and
   `ansible-galaxy collection install -r requirements.yml`:

   ```bash
   ansible-galaxy collection install git+https://github.com/gernottutner-net/ansible-agent-sandbox.git,v0.5.0
   ansible-galaxy collection list tutner.agent_sandbox     # shows the new version
   ```

4. Ask what the update needs, on the VM and on the controller
   ([below](#what-an-update-needs)), and change your files where it says:

   ```bash
   ansible-playbook tutner.agent_sandbox.update_check
   ```

5. See what it would change on the VM, then apply it:

   ```bash
   ansible-playbook tutner.agent_sandbox.provision
   ansible-playbook tutner.agent_sandbox.sandbox --check --diff
   ansible-playbook tutner.agent_sandbox.sandbox
   ```

From a Git URL, `ansible-galaxy` installs every time, also an older tag
over a newer one, so `--force` is not needed. It replaces the installed
collection as a whole: a change made by hand inside it is lost. Your
working directory is not touched: the inventory, `host_vars`,
`group_vars`, `ansible.cfg` and the snapshot state stay as they are.

To go back, install the previous tag the same way, and restore the
snapshot. `sandbox` warns when the installed collection is older than the
one that last applied the VM, and goes on.

### What an update needs

Everything the roles put on the VM reaches it with the next `sandbox` run:
the launcher, the managed settings, new packages. What no playbook run
changes is yours: your inventory, and the scripts from `examples/` you
copied to the controller. `update_check` says what an update means for
both, and changes nothing:

```bash
ansible-playbook tutner.agent_sandbox.update_check                        # report only
ansible-playbook tutner.agent_sandbox.update_check -e install_scripts=true
```

- **On the VM**, which release last applied each role. Every `sandbox`
  run records it in `/etc/agent-sandbox/deployed.json`, for the roles it
  ran: after `--tags agentbox`, only for `agentbox`. A VM that a release
  before 0.6.0 set up has no such record yet; one `sandbox` run writes it.
- **For every release since**: the playbooks to run, in order; whether
  the image recipe changed, so that `sandbox_image_tag` needs a new value,
  with yours and the new default; the new variables, each with whether
  your inventory sets it and what it does; and the controller scripts that
  are new or changed. It reads this from the collection's
  `meta/updates.yml`, which says what CHANGES.md says under "Action needed
  on an existing install".
- **In your inventory**, the variables `examples/` sets and yours does
  not. The roles have a default for each, so a missing one is not an
  error; it may be one you would want to set.
- **On the controller**, each script from `examples/`, such as
  [`agentbox-remote`](#from-the-controller): not installed, current, or
  different from the collection's copy. It looks on your `PATH` first,
  then in `agent_sandbox_bin_dir` (default `~/.local/bin`, settable in
  your inventory). With
  `-e install_scripts=true` it copies them there, keeping a copy that
  differs as a backup next to it, and warns when that directory is not on
  your `PATH`.

A VM that is off gets a line saying so; the controller's part runs all the
same. On `main`, the collection still reports the last release's version,
so `update_check` lists what the releases up to it need, not what `main`
changed since.

## Configure

The collection brings the playbooks and roles; what you supply is
configuration only. Copy the contents of `examples/` from this repository
into a working directory of your own; it is the whole working directory, no
playbooks of your own needed. Then adapt it:

- `inventory.yml`: the VM, in the group `agent_sandbox`.
- `host_vars/sandbox-vm.yml`: the VM's host-only address, its two MACs,
  its SSH key, and optionally its size.
- `group_vars/all.yml`: sudo for the `ansible` account cloud-init creates.
- `group_vars/agent_sandbox.yml`: the policy: the allowlist, the limits
  (memory, CPUs, processes), the image tag and Claude Code's version, and
  environment for Claude Code, which every command Claude runs can read: no
  credentials there.
- `ansible.cfg`: pipelining, so Ansible can become the sandbox user, and
  only the VM's own key offered. A commented-out `log_path` turns on a log
  file; Ansible writes none by default.

The VM knows only what a playbook wrote to it. A change to your inventory
does nothing on the VM until the playbook that reads it runs again, and a
session that is running keeps what it started with:

| You changed | Run | Then |
|---|---|---|
| `agentbox_git_tokens`, or a token in your credential helper | `git_token -e project=<project>` | start the project's session again |
| anything else in `group_vars/agent_sandbox.yml`: allowlist, limits, image, `agentbox_*`, `agentbox_peer_links` | `sandbox` | start the sessions again |
| `vm_memory_mb`, `vm_cpus` | `provision`, with the VM off | see [Tuning the VM](#tuning-the-vm) |

A link or a token that is in the inventory but missing from the VM shows as
a line the launcher does not print as the session starts
([The launcher](#the-launcher)).

Run every `ansible-playbook` command below from inside that directory:
Ansible reads `ansible.cfg` from the current directory, and through it
finds the inventory. Started anywhere else, it runs with another
`ansible.cfg` and inventory, or none.

## Create the VM and the sandbox

```bash
ansible-playbook tutner.agent_sandbox.provision    # the VM, until cloud-init is done
ansible-playbook tutner.agent_sandbox.sandbox      # the sandbox inside it
```

`provision` skips the creation of a VM that exists; if it is off, it
applies `vm_memory_mb` and `vm_cpus` and starts it. `sandbox`
takes the tags `podman`, `egress` and `agentbox`; a second run reports
`changed=0`, and `--check --diff` shows what a run would change.

## Check the sandbox

The roles check their own work on every run, but from the VM, not from
inside a container. These smoke tests check it from where a session sits.
Run them once after the first `sandbox` run, before the baseline snapshot,
and again after changing the allowlist or the policy. Nothing enforces
this; it's how you see the sandbox deny before you trust it.

Run them as `agent` on the VM (`ssh` in as `ansible`, then
`sudo -iu agent`). Containers get the proxy from Podman's
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

## Starting and stopping the VM

The VM does not start with the VirtualBox host: after a reboot of the
host, it is off. Start it with `provision` again:

```bash
ansible-playbook tutner.agent_sandbox.provision
```

For a VM that exists, it skips the creation, applies the memory and CPUs
from your variables if the VM is off (see [Tuning the VM](#tuning-the-vm)),
starts it headless, and returns once the guest answers over SSH and cloud-init reports
done. Its preflight and image check run too, so it needs the network for
Debian's `SHA512SUMS`; the cached image is not downloaded again.

Or with VirtualBox directly, then wait for the guest; the VM's name is its
inventory name, unless `vm_name` sets another:

```bash
VBoxManage startvm sandbox-vm --type headless
ansible-playbook tutner.agent_sandbox.wait
```

To stop it, shut the guest down cleanly, through its ACPI power button:

```bash
VBoxManage controlvm sandbox-vm acpipowerbutton
while VBoxManage list runningvms | grep -q '"sandbox-vm"'; do sleep 2; done
```

`acpipowerbutton` returns at once: it only presses the button. The guest
then stops its services and powers off on its own, which takes some
seconds, and minutes on a host that is swapping. The loop returns once
the VM is off. Only if the guest never gets there, power it off hard,
like pulling the plug:
`VBoxManage controlvm sandbox-vm poweroff`.

A shutdown or reboot of the guest clears every `session`
[repository token](#repository-tokens), which is kept on tmpfs.

## Tuning the VM

Two sizes matter: the VM's, set per VM in `host_vars/sandbox-vm.yml`, and
each session's, set in `group_vars/agent_sandbox.yml`.

| Variable | Default | Where | Takes effect |
|---|---|---|---|
| `vm_memory_mb` | `6144` | `host_vars` | next `provision` that finds the VM off |
| `vm_cpus` | `4` | `host_vars` | next `provision` that finds the VM off |
| `vm_disk_size` | `"40G"` | `host_vars` | only when the VM is created |
| `sandbox_memory` | `2g`, no swap | `group_vars` | next session, after `sandbox --tags agentbox` |
| `sandbox_cpus` | `1.5` | `group_vars` | next session, after `sandbox --tags agentbox` |
| `sandbox_pids_limit` | `256` | `group_vars` | next session, after `sandbox --tags agentbox` |

**The VM's memory and CPUs.** VirtualBox changes them only while the VM is
off, and `provision` never shuts a guest down for it. Change the value,
then:

```bash
VBoxManage controlvm sandbox-vm acpipowerbutton
while VBoxManage list runningvms | grep -q '"sandbox-vm"'; do sleep 2; done
ansible-playbook tutner.agent_sandbox.provision    # applies the values, starts the VM
VBoxManage showvminfo sandbox-vm --machinereadable | grep -E '^(memory|cpus)='
```

Run against a VM that is running, `provision` changes nothing and says
which values wait for the VM to be off. A snapshot records the memory and
CPUs the VM had when it was taken, and a `restore` brings them back;
`provision` applies the variables again the next time it finds the VM off.

**The session limits** are written into the launcher, not read when it
runs. Apply them with:

```bash
ansible-playbook tutner.agent_sandbox.sandbox --tags agentbox
```

A running session keeps the limits it started with.

**How big.** One session needs `sandbox_memory`, plus Squid and the guest
itself: about 4 GB for one session with the defaults. Each further session
at the same time needs another `sandbox_memory`. Details in
[docs/virtualbox.md](docs/virtualbox.md#adding-a-vm).

**What it costs the host.** A guest page, once used, stays in the host's
RAM until the VM stops: VirtualBox does not get it back when the guest
frees it. The guest also counts its file cache as free memory, while the
host does not. So the VirtualBox process grows towards `vm_memory_mb`
during a session, even while `free` or `htop` in the guest shows little in
use, and shrinks only when the VM is restarted. Give the VM what the host
can spare beside everything else it runs. If the host runs short, it
swaps, and the guest slows down with it: VirtualBox then logs `TM: Giving
up catch-up attempt` in the VM's `VBox.log`, because the guest's clock
falls behind.

**The disk** is grown once, when the VM is created. Changing
`vm_disk_size` later has no effect on that VM; for a bigger disk, create a
new VM.

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
  6 GB VM; about 240 MB each with Claude Code 2.1.323, on a 4 GB VM.
- Everything outside `/work` and Claude Code's state is gone when the
  session ends (`--rm`). A lost terminal ends the session too: on a
  dropped SSH connection the launcher stops the container. For a session
  that should outlive the connection, use `--tmux`: see
  [Sessions that outlive the connection](#sessions-that-outlive-the-connection).
- The run policy is rendered into the launcher, not read from the
  environment or the command line: `--cap-drop=ALL`,
  `no-new-privileges`, the memory, CPU and process limits, no swap, the
  read-only managed settings. No invocation can forget one.
- A session without `--auto` starts in Claude Code's manual mode: Claude
  asks before anything its sandbox does not cover. Claude Code's own
  default is now auto mode, where a classifier decides; the managed
  settings set manual mode instead. Shift+Tab switches a session to auto
  mode.

As it starts, the launcher prints what the session gets beyond the
defaults, one line each:

```text
agentbox: repository token for github.com (permanent)
agentbox: repository token for gitlab.example.org (session, deleted when it ends)
agentbox: linked session: sends to beta, telemetry on, confirm the channel dialog
```

No line, no token or link in this session. When one you expected is
missing:

- **A token:** `git_token -e project=<project>` has not run since the
  token went into `agentbox_git_tokens`, or a `session` token was used up
  by the session before, or cleared by a reboot of the VM. git then asks
  for a username on a clone of a private repository and on a push:
  nothing in the session can answer it.
- **The link:** `sandbox` has not run since the link went into
  `agentbox_peer_links`, so the launcher on the VM has no links; or the
  session is not a plain `agentbox <project>` on a terminal
  ([Agent Intercom](#agent-intercom)).

### Sessions that outlive the connection

```bash
agentbox --tmux <project>                     # start, or attach if it runs
agentbox --tmux --auto <project> -p '<task>'  # the same, for --auto
agentbox --list                               # the projects, and which run
```

`--tmux` starts the session inside a tmux session on the VM, named
`agentbox-<project>` (a `.` in the name becomes `+`), and attaches to it.
Detach with `Ctrl-b d`, or lose the connection: the session goes on. The
same `agentbox --tmux <project>` attaches to it again, from any login on
the VM. Everything else is as with a plain `agentbox <project>`: the same
container, limits, tokens and, for a project in a link, the same linked
session.

- **One session per project, either way.** `--tmux` on a project whose
  tmux session is there attaches, and refuses if you give it a command or
  `--auto`. On a project with a plain session running, it refuses, and so
  does a plain `agentbox <project>` while the tmux one runs.
- **`--list`** prints each project in `~/projects`, with `running` when its
  container is there and `tmux` when its tmux session is.
- **Ending one:** exit Claude, or, from outside,
  `tmux kill-session -t agentbox-<project>`. The launcher then stops the
  container and deletes a `session` token, as for a lost terminal.
- **The output goes with it.** When Claude exits, the tmux session closes,
  and what was on its screen is gone. For an `--auto -p` run, have the task
  write its result into a file in `/work`.
- `--tmux` needs a terminal: over SSH, `ssh -t`.
- The tmux server runs in a scope of `agent`'s own systemd instance, not in
  the SSH login it was started from, so logging out does not end it. A
  reboot of the VM does.

### From the controller

[`examples/agentbox-remote`](examples/agentbox-remote) runs the launcher
over SSH, so a session is one command on the controller. Install it into
`~/.local/bin`, or the directory `agent_sandbox_bin_dir` names, with
`ansible-playbook tutner.agent_sandbox.update_check -e install_scripts=true`;
the same command replaces it after an update
([What an update needs](#what-an-update-needs)). Or copy it into a
directory on your `PATH` yourself. Then:

```bash
agentbox-remote <project>                   # agentbox <project>, on the VM
agentbox-remote --tmux <project>            # start or reattach
agentbox-remote --tmux --auto <project> -p '<task>'
agentbox-remote --list
```

It takes the same arguments as the launcher and passes them on unchanged,
quotes and `$` included. `AGENTBOX_HOST` names the VM as `ssh` reaches it,
as the account Ansible uses: a `Host` from `~/.ssh/config`, or
`ansible@192.168.56.10`; the default is `sandbox-vm`. `AGENTBOX_USER` is
the sandbox account, `agent` unless `sandbox_user` says otherwise.

It does not use `sudo -i`, which hands the command to the sandbox account's
login shell: that shell would parse the arguments again and expand any
`$NAME` in a `-p` task. Typed by hand on the VM, `sudo -iu agent agentbox …`
does expand it; quote such a task for that shell too, or start the session
from `agent`'s own shell.

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

`-p` prints nothing until Claude is done. A long silence need not be a
hang: an overloaded API answers `529 Overloaded`, and Claude Code retries
quietly for a while before it gives up.

### Logging in

The first session in a project asks for the Claude login: open the URL it
prints in a browser and paste the code back. Then Claude Code asks whether
you trust the folder; its default answer is *No, exit*, so choose *Yes*. The login is kept per
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
hosts work, and there are no SSH keys in the sandbox. A private repository,
and a push to any repository, need a [repository token](#repository-tokens),
written to the VM before the session starts; the session's first lines
name it.

```bash
ansible-playbook tutner.agent_sandbox.git_token -e project=myproj   # on the controller, if it has a token
agentbox myproj bash
git clone https://github.com/<owner>/<repo>.git .      # inside, in /work
exit
agentbox myproj
```

### Repository tokens

A token lets git in a session clone a private repository, and push to any
repository. A project gets its own tokens, one per host, and each has a
lifetime:

- `session`: for the project's next session only. The launcher deletes it
  from the VM when that session ends. It is kept on tmpfs, so it never
  reaches the VM's disk or a snapshot, and a reboot clears it too.
- `permanent`: for every session of the project, until removed. Kept on
  the VM's disk, in `~agent/.agentbox-tokens/<project>/`, and so in every
  snapshot taken while it is there.

Either way, the token stays valid at GitHub or GitLab until it expires or
you revoke it there. Create it as narrow as the work allows: a GitHub
fine-grained token for the one repository, with *Contents* read, or read
and write to push, and an expiry; on GitLab, a project access token with
`read_repository`, or `write_repository` to push, and an expiry. Protect
the branches an agent must not push to on the remote; the sandbox does not
know about branches.

The tokens come from the controller's own git: the playbook asks
`git credential fill`, so whatever credential helper you use there
answers, whether it reads a password store, a keyring or `gh auth`. Your
inventory names where each token is, never the token:

```yaml
# host_vars/sandbox-vm.yml
agentbox_git_tokens:
  myproj:
    - url: https://github.com/<owner>/<repo>
      lifetime: session                 # or: permanent
      git_config:                       # optional: -c options for git credential fill,
        credential.<setting>: <value>   #   e.g. the one your helper picks the token by
```

`git credential fill` runs from `/`, so no repository's own settings
apply: a helper that picks the token by a per-repository setting gets it
from `git_config`. Check first that your helper answers, for example
`printf 'protocol=https\nhost=github.com\n\n' | git credential fill`,
from outside any repository; it prints the token, so not where others can
see it. The host must be on `egress_allowlist`; a self-hosted GitLab is
added there first.

Write the project's tokens to the VM, a `session` token just before the
session it is for, and remove them again:

```bash
ansible-playbook tutner.agent_sandbox.git_token -e project=myproj
ansible-playbook tutner.agent_sandbox.git_token -e project=myproj -e git_token_action=remove
```

Writing replaces what the project had, and is also how a token is rotated.
The `sandbox` playbook never touches tokens. In the session, git finds
them on its own, through a credential helper in the image, so the token
never ends up in `.git/config` or a remote URL; the launcher names each
token's host and lifetime as the session starts.

Do not count on Claude Code's sandbox to keep the commands Claude runs
from writing `.git/config`. In one release test `git push -u` recorded no
upstream, though it said so and exited 0; in the two after it, with the
same and a newer Claude Code, the upstream landed in `.git/config`. Why
it differs is not known ([docs/release-tests.md](docs/release-tests.md#what-it-found)).
So `.git/config`, like the rest of `/work`, is what Claude may have
written. Set up git configuration you want in `agentbox <project> bash`.

A token is readable by every command Claude runs: git is one of them, and
has to read it. Claude's Read tool can read it too: a deny rule for the
tool would hide it from git as well. So the token's scope is what limits
a misled agent, not its secrecy: a token
that can push can push the project anywhere it reaches. Why, and what was
weighed, is in [docs/design.md, "Repository tokens"](docs/design.md#repository-tokens).

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

No hook or mod loads unless it comes from the managed settings, which
define none: not the user's, not a project's or a plugin's, and not a mod
Claude writes. Such a mod would otherwise turn on without asking in
`--auto` and in auto mode, and run outside the sandbox, where it can read
the login.

Deny rules keep Claude's Read and Edit tools off the login and the
settings. Commands you type yourself at Claude Code's `!` prompt are not
sandboxed.

To see that a command Claude runs really is inside the sandbox, have it run
something slow (`sleep 60`) and look from a second shell as `agent`. The
image has no `ps`; `podman top` reads the processes from outside:

```bash
podman top agentbox-<project> pid ppid args | cut -c1-80
```

PID 1 is `/run/podman-init`, `claude` its child, and the command runs below
a `bwrap --new-session …` pair. `[bwrap]` in brackets would be a zombie;
the launcher's `--init` reaps them.

### Agent Intercom

Sessions that talk to each other. Off by default. With links in your
inventory, Claude in one session can talk to Claude in another, with nobody
typing:

```yaml
agentbox_peer_links:
  - { from: alpha, to: beta }
  - { from: beta, to: alpha }
```

Run `sandbox --tags agentbox`, and start both sessions, each in a terminal
of its own, leaving them open:

```bash
agentbox alpha
agentbox beta
```

Each prints that it is linked:

```text
agentbox: linked session: sends to beta, telemetry on, confirm the channel dialog
```

Without that line the session is not linked: run `sandbox` after every
change to the links; the inventory alone changes nothing on the VM. Then
Claude Code asks you to confirm a warning about development channels, at
every start: choose "I am using
this for local development". Then tell one session what you want, for
example to ask the session in `beta` something. It gets a tool `send`, and
the other wakes up by itself.

**Read this before you link two projects:**

- **A link means the two projects trust each other.** If one session is
  misled by something it read, it can steer the other, which holds that
  project's files and repository tokens. Nothing can filter that.
- **Telemetry is on in a linked session,** because Claude Code's channels
  do not work without it. Squid still denies the telemetry host it was
  seen trying; what goes to `api.anthropic.com` cannot be told.
- **Channels are a research preview,** so an update of Claude Code may
  break this. It was tested with Claude Code 2.1.323, the version in the
  example policy.
- **A project's own `.mcp.json` is off** in a linked session.

Worth knowing:

- Only plain `agentbox <project>` on a terminal is linked. `--auto`, `-p`
  and other commands are not.
- Sessions do not simply obey each other: a message is marked as not from
  the user, and one may decline work its own user did not ask for. Tell
  each session at its own prompt that it will work with the other.
- `agentbox_peer_budget` (40) limits the messages between two projects.
  When it is used up, both sessions are told, and nothing more gets through
  until you start one of them again. A message to a closed session is
  refused.
- Changing links restarts the broker, so linked sessions have to be started
  again.
- Everything sent is in the journal, as `ansible` on the VM:
  `sudo journalctl -u agentbox-peer`.

Remove the links and run the play again, and everything is gone.
[docs/design.md](docs/design.md#agent-intercom) has how
it works, what it costs, and what was tested.

## Egress

Everything `agent` sends goes through Squid, which allows only the hosts in
`egress_allowlist`. A direct connection past Squid is dropped by nftables,
and no DNS resolver is reachable. See what was refused:

```bash
sudo grep TCP_DENIED /var/log/squid/access.log | tail -20
```

To allow a host, first decide whether it should be reachable at all: every
entry is also a way out for data. Add it to `egress_allowlist`, prefer the
exact host over a leading dot, and apply it from your working directory:

```bash
ansible-playbook tutner.agent_sandbox.sandbox --tags egress,agentbox
```

Both tags, because Squid and Claude Code's sandbox each get the list.

`DISABLE_TELEMETRY=1` and `DISABLE_ERROR_REPORTING=1` in the example policy
keep Claude Code from trying its telemetry and error-reporting hosts, which
are not on the allowlist. `downloads.claude.ai` stays denied: Claude Code falls
back to cloning its plugin marketplace from GitHub, and updates come only
from an image rebuild.

## Updating Claude Code

The image holds a pinned Claude Code and never updates itself. Change both
values in `group_vars/agent_sandbox.yml`:

```yaml
sandbox_image_tag: "0.4.0-cc2.x.y"         # a new tag, never reuse one
agentbox_claude_code_version: "2.x.y"
```

Then apply them from your working directory:

```bash
ansible-playbook tutner.agent_sandbox.sandbox --tags agentbox
```

The new image is built beside the old one, and the next session started
with `agentbox` runs it. A VM has one image for all its projects, so
every project gets the new Claude Code; a session already running keeps
the old one until it ends. The run updates every VM in the group
`agent_sandbox` whose values come from `group_vars`; add `--limit <vm>`
to try one VM first.

The role refuses to rebuild an existing tag from a changed recipe, so a
forgotten tag bump fails loudly. Going back: set both values back; the old
image is still there.

The role only checks whether a tag is new; it never compares tags by
order, so the tag is a name, not a version the role reads. A tag that
starts with the collection's default tag and adds `-cc` and the Claude
Code version is recommended:

- `podman images`, run as `agent`, shows which Claude Code each old image
  holds, which is what you look for when going back.
- It cannot be confused with a later default of the collection, which
  names its own tags `X.Y.Z`.
- After a collection upgrade that changes the image, move the prefix
  along, as in `0.4.0-cc2.x.y`.
- Use `-`, not semver's `+`: image tags do not allow `+`.

A [diagram](docs/images/claude-code-image.svg) shows how Claude Code gets
into the image and into a session, and how an update replaces it.

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
- **keep a repository token from commands.** git is a command, so every
  command Claude runs can read the project's token; its scope is the
  limit ([Repository tokens](#repository-tokens)).
- **keep two linked projects apart.** That is what
  [a link](#agent-intercom) gives up: a misled session
  can steer the one it is linked to.
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
3. **Linked sessions with logins other than Pro.** Team, Enterprise and
   API-key logins probably need `channelsEnabled: true` in the managed
   settings for channels, which the collection does not set. Only a Pro
   login was tested.

## Licence

MIT, see [LICENSE](LICENSE).
