# Design

Why the sandbox is built the way it is: what each role does and why, the
policy surface, the launcher contract, what the design knows and what it
does not, and the decisions behind it. The README says how to use the
collection; [docs/virtualbox.md](virtualbox.md) covers the VM. This
document is for anyone who wants to judge whether the sandbox deserves
trust, or to change it.

Everything here describes the code as it is, unless a section is marked
otherwise:

- *Planned*: designed, not built. The collection does not do it yet.
- *Proposed rule*: a rule for extensions, not yet enforced by code.
- *Experimental*: the [gVisor](#gvisor-the-experimental-extension)
  section, for an extension that is not part of the core and does not
  exist yet as a collection.

The design was developed on a VirtualBox VM that has run the sandbox since
September 2026, and is the one the findings below were made on. Versions
named are the ones tested: Debian 13, Podman 5.4.2, Squid 6.13, kernel
6.12, Claude Code 2.1.284.

---

## Contents

- [The layers](#the-layers)
- [The sandbox account](#the-sandbox-account)
- [The roles](#the-roles)
  - [`virtualbox_vm`: the disposable VM](#virtualbox_vm-the-disposable-vm)
  - [`podman`: runtime and identity](#podman-runtime-and-identity)
  - [`egress_proxy`: default-deny with exceptions](#egress_proxy-default-deny-with-exceptions)
  - [Finding: what a pasta container can reach on the host](#finding-what-a-pasta-container-can-reach-on-the-host)
  - [`agentbox`: image, managed settings and launcher](#agentbox-image-managed-settings-and-launcher)
- [The policy surface](#the-policy-surface)
- [The launcher contract](#the-launcher-contract)
- [Secrets, honestly](#secrets-honestly)
- [Core and extensions](#core-and-extensions)
- [Extension points](#extension-points)
- [Extensions and the security boundary](#extensions-and-the-security-boundary)
- [Known unknowns](#known-unknowns)
  - [How they were tested](#how-they-were-tested)
- [Possible features](#possible-features)
  - [An API key for unattended runs](#an-api-key-for-unattended-runs)
  - [Unattended starts](#unattended-starts)
  - [Private repositories](#private-repositories)
- [Why not bare metal](#why-not-bare-metal)
- [gVisor, the experimental extension](#gvisor-the-experimental-extension)
  - [Why it is not in the core](#why-it-is-not-in-the-core)
  - [The role as designed](#the-role-as-designed)
  - [Finding: rootless `runsc` cannot use the container limits](#finding-rootless-runsc-cannot-use-the-container-limits)
  - [What re-enabling it needs](#what-re-enabling-it-needs)
- [Decisions](#decisions)

---

## The layers

From the outside in. Each layer assumes the one inside it can fail.

| Layer | What it is | What it stops |
|---|---|---|
| VM | a disposable Debian 13 guest on VirtualBox, snapshotted | everything below reaching the VirtualBox host, short of a VirtualBox escape; a kernel exploit from a container stops here |
| Account | `agent`, no sudo, its own subuid range, lingering | an escape from the container landing as root or as the account Ansible uses |
| Container | rootless Podman with crun: `--cap-drop=ALL`, `no-new-privileges`, memory, CPU and process limits, no swap, `--rm` | a session reaching other projects, the host's files, or exhausting the VM |
| Egress | Squid with a default-deny allowlist; an nftables rule on `agent`'s uid that leaves Squid the only way out; no DNS | a session talking to any host not on the list |
| Inner sandbox | Claude Code's own sandbox (`bubblewrap`), strict, from managed settings mounted read-only | the commands Claude runs reading the login, changing Claude Code's configuration, or reaching a host outside the list |

What none of them stops is in the README, "What it protects, and what not",
and under [Secrets, honestly](#secrets-honestly).

## The sandbox account

The first draft of the architecture argued that a container escape "lands
as a regular user, not root". On a VM made from a cloud image that is not
true: the one unprivileged account is the one cloud-init creates for
administration, here `ansible`, with

```
ansible ALL=(ALL) NOPASSWD:ALL
```

An escape into that account is a root escape, and it also captures the
account Ansible uses to manage the machine. The user-namespace boundary
would buy nothing.

**Therefore a dedicated account, `agent`.** No sudo, in no admin group,
its own subuid and subgid range disjoint from `ansible`'s, and lingering,
so its systemd user instance exists without a login. Every container runs
as `agent`; `ansible` never runs `podman`. This is the most important
single choice in the design, and the reason the `podman` role creates a
user at all.

## The roles

Four roles, one concern each. `virtualbox_vm` runs on the VirtualBox host;
the other three configure the guest, in order, and each ends by checking
what it set up, so a run that passes has been observed denying, not only
configured to.

### `virtualbox_vm`: the disposable VM

Creates the VM from Debian's checksum-verified generic cloud image with a
cloud-init seed: a NAT NIC for the way out and a host-only NIC for SSH and
for Squid, both with pinned MACs, and the `ansible` account with the
user's key. Snapshots keep one rolling slot plus the baseline at the root
of the tree; `destroy` removes the VM with its disks and snapshots. The VM
is the boundary against a kernel exploit (see
[Why not bare metal](#why-not-bare-metal)), which is why the collection
creates it rather than assuming one. The details, and the reasoning behind
the two NICs and the snapshot policy, are in
[docs/virtualbox.md](virtualbox.md).

### `podman`: runtime and identity

- Installs `podman`, `passt`, `uidmap`, `fuse-overlayfs`,
  `dbus-user-session` and `catatonit`. `dbus-user-session` gives `agent`
  its own D-Bus, which the systemd cgroup manager needs; without it
  rootless Podman falls back to cgroupfs and the limits are no longer
  delegated. `catatonit` is the init behind the launcher's `--init`;
  Debian only recommends it.
- Creates `agent`: own home (mode `0700`), locked password, no
  supplementary groups. `groups: ""` means a hand-made addition to `sudo`
  or `adm` is undone on the next run. The role then asserts that
  `sudo -l -U agent` grants nothing, so a stray `/etc/sudoers.d` entry
  fails the run instead of passing silently.
- Writes `/etc/subuid` and `/etc/subgid` explicitly, by default
  `agent:200000:65536`, disjoint from `ansible:100000:65536`.
  **Trap:** changing a user's subuid range after containers exist
  invalidates every image layer and requires `podman system migrate`. The
  range is effectively immutable once the VM is in use, so it is pinned
  in the policy rather than left to `useradd`.
  **Trap:** `useradd` allocates a range on its own (the next free one), so
  the pinned line *replaces* the user's line rather than being added
  beside it. Before writing, the role asserts that the pinned range
  overlaps no other user's in either file. A changed range triggers
  `podman system migrate` as a handler.
- `loginctl enable-linger agent`, guarded on `/var/lib/systemd/linger/agent`
  so it is idempotent. Without lingering there is no user systemd instance
  and no delegated cgroup when nobody is logged in, which is precisely the
  unattended case.
- Writes the drop-in `/etc/containers/registries.conf.d/50-ansible.conf`
  with `unqualified-search-registries = ["docker.io"]`, leaving the
  packaged `registries.conf` alone.
  **Trap:** Debian's Podman ships no default search registry, so an
  unqualified `podman pull debian:trixie-slim` fails outright. Every image
  reference in the collection is fully qualified anyway; the setting is
  there so an interactive pull behaves as expected.
- Writes the drop-in `/etc/containers/containers.conf.d/50-ansible.conf`.
  Every value in it is already Podman 5's default, and is pinned because
  the design depends on it: `cgroup_manager = "systemd"` (the limits),
  `default_rootless_network_cmd = "pasta"` (the egress rule), and journald
  for logs and events. Storage stays at Podman 5's default, native
  rootless overlayfs on kernel 6.12; `fuse-overlayfs` is installed as a
  fallback but not forced.
- Ends by running `podman info` as `agent` and asserting: rootless,
  cgroup v2 via systemd, `memory` and `pids` among the delegated
  controllers, and pasta as the network command. That is the check that
  `--memory` and `--pids-limit` will bind. Skipped under `--check`, when
  Podman may not be installed yet.

### `egress_proxy`: default-deny with exceptions

Two halves that only work together. Their shape was settled by
[the pasta finding](#finding-what-a-pasta-container-can-reach-on-the-host)
below.

**Squid** holds the allowlist. It listens on the VM's host-only address
only (`egress_proxy_address`, set per host): the role rewrites the stock
`http_port 3128` line in `squid.conf` rather than adding a second one,
which would collide with the wildcard bind. The rules are a drop-in at
`/etc/squid/conf.d/agent-sandbox.conf`, with the list rendered from the
policy into `/etc/squid/agent-allowlist.txt`. With the example address:

```squid
acl agent_sandbox src 192.168.56.20/32
acl agent_allowed dstdomain -n "/etc/squid/agent-allowlist.txt"
http_access allow agent_sandbox agent_allowed
http_access deny all
```

- The source ACL is the VM's own address, not `localhost`: pasta connects
  to Squid *from* that address, so the stock `localhost` ACL would never
  match sandbox traffic. The VirtualBox host can reach the port, but
  matches nothing and gets `deny all`.
- `-n` disables the reverse lookup `dstdomain` otherwise does for a bare
  IP address, so `CONNECT 1.2.3.4:443` can never match an allowlisted
  domain.
- `dstdomain` matches `CONNECT` requests too, since the request line
  carries the host name. HTTPS is filtered by destination host without TLS
  interception: no CA to install, no certificate pinning broken.
- Squid uses the first matching `http_access` line, so the drop-in's
  `deny all` is only final if no stock allow comes before the include.
  **Trap:** Debian's Squid 6.13 puts `include /etc/squid/conf.d/*.conf`
  *after* `http_access allow localhost` (and after the `to_localhost` and
  `to_linklocal` denies, which is where they belong). Sandbox traffic never
  comes from localhost, but that would tie the allowlist's integrity to
  the listen address. So the role comments out that one stock line, and
  then asserts from the file that the include is the first allow left. The
  assertion caught the order on the first run; it was not assumed.
- A systemd drop-in orders Squid after `network-online.target`, because it
  binds an address rather than the wildcard.

**nftables** makes the proxy unavoidable. Rootless pasta means container
traffic leaves the VM as `agent`'s uid, so an owner match in the output
chain is a boundary the container cannot route around. With `agent`'s uid
and the example address:

```nft
table inet agent_sandbox
flush table inet agent_sandbox

table inet agent_sandbox {
  chain output {
    type filter hook output priority filter; policy accept;
    meta skuid <agent's uid> ip daddr 192.168.56.20 tcp dport 3128 accept
    meta skuid <agent's uid> counter reject
  }
}
```

- **No loopback exception.** Pasta forwards the container's DNS to
  systemd-resolved on `127.0.0.53` as `agent`, and the local MTA listens
  on `127.0.0.1:25`; an `lo` accept would leave both open as channels the
  allowlist never sees. Squid resolves names itself, so the sandbox needs
  no DNS at all.
- `reject` rather than `drop`, so a blocked connection fails at once
  instead of hanging a tool until its timeout. The counter shows how often
  it fires.
- The file declares the table, flushes *that table* and defines it;
  `nft -f` applies it as one transaction, so a reload never leaves a gap.
  It never touches another table and never runs `flush ruleset`, which is
  why it is not loaded through Debian's `/etc/nftables.conf`. Its own
  oneshot unit, `agent-sandbox-egress.service`, loads it at boot before
  `network-pre.target`; stopping that unit deletes the table.
- The template is validated with `nft -c -f` before it is written.

**Podman** gets the proxy from a third drop-in,
`/etc/containers/containers.conf.d/70-egress-proxy.conf`, which sets
`http_proxy`, `https_proxy` and their upper-case forms in both
`[engine] env` (pulls and builds) and `[containers] env` (every
container). They point at the address, not a name, since the sandbox has
no DNS.

Three consequences, stated plainly:

- The rule is **uid-scoped**, so `root` and `ansible` keep unrestricted
  egress: apt, upgrades and Ansible's own work are unaffected. A host-wide
  default-deny would have broken all of that.
- Podman's own image pulls run as `agent` and are forced through the proxy
  too. That is intended, and it means the registry must be on the list.
- **This is host-level control, not content control.** It stops
  exfiltration to `attacker.example`. It does not stop exfiltration to a
  gist on an allowlisted `github.com`. The allowlist answers "which
  organisations can this agent talk to", not "can this agent leak".

The role ends with three probes as `agent` on the VM, where the same uid
rule applies: an allowlisted URL through the proxy must succeed,
`example.com` through the proxy must get Squid's 403, and a direct
connection to `1.1.1.1:443` must fail. Only the first needs the internet.
There is no switch to turn the proxy off: the core promises default-deny
egress.

### Finding: what a pasta container can reach on the host

Tested 2026-09-28 as `agent`, with a throwaway `socat` listener and
`debian:trixie-slim`, nothing in `/etc` changed. `192.168.56.x` is the
VM's host-only address, `10.0.2.15` its NAT address.

| Listener | From the container via | Result |
|---|---|---|
| `127.0.0.1:3128` | `host.containers.internal` (169.254.1.2), `127.0.0.1`, `192.168.56.x`, `10.0.2.15` | refused, every one |
| `192.168.56.x:3128` | `192.168.56.x` | **connects**; the VM sees the peer as `192.168.56.x` |
| `192.168.56.x:3128` | `host.containers.internal`, `10.0.2.15` | refused |

Inside the container, `10.0.2.15` is the container's own copy of the NAT
address, so it never reaches the VM. The VM's loopback is not reachable
at all. So Squid listens on the host-only address, and that is why the VM
has two NICs.

DNS in the container: `resolv.conf` lists `169.254.1.1`, which pasta
forwards to the VM's systemd-resolved stub on `127.0.0.53` (seen with `ss`
as UDP sockets owned by `pasta`, running as `agent`), and `10.0.2.3`,
VirtualBox's NAT resolver, reached directly. Both resolved names. With a
loopback exception in the nftables rule the first path would have stayed
open; without one, both are rejected.

### `agentbox`: image, managed settings and launcher

- **The image.** A `Containerfile` template rendered to
  `/etc/agentbox/Containerfile`, owned by root: `agent` builds from it but
  cannot change it. `docker.io/library/debian:trixie-slim` pinned by tag;
  `ca-certificates`, `curl`, `git`, `ripgrep`, and `bubblewrap` and
  `socat`, which Claude Code's own sandbox uses on Linux. Node from
  NodeSource, its key stored as `.asc` so the image needs no `gnupg`.
  Claude Code installed as root with npm at build time, pinned to
  `agentbox_claude_code_version`, with `DISABLE_AUTOUPDATER=1` so updates
  only ever come from a rebuild. A non-root user `dev` with uid and gid
  1000, both pinned because the launcher's user mapping names them;
  `WORKDIR /work`, `CMD ["claude"]`. The build gets the proxy from
  `containers.conf` and does not bake it into the image (tested), so the
  Containerfile carries no proxy settings.
- **One tag, one build.** Built as `agent`, tagged
  `localhost/agentbox:<sandbox_image_tag>`, only when that tag does not
  exist yet. Tagged, not `latest`, so a rebuild is a visible change. The
  image carries a label with the SHA-256 of the rendered Containerfile; if
  the tag exists but was built from a different Containerfile, the role
  fails and asks for a tag bump instead of rebuilding the tag. Updating
  Claude Code therefore means bumping `agentbox_claude_code_version` and
  `sandbox_image_tag` together. Old tags stay in `agent`'s storage, so
  going back is setting the tag back.
- **Two directories.** `~agent/projects/` and `~agent/.agentbox/`, both
  mode `0700`, the only directories whose subdirectories are ever mounted
  in: the project, and Claude Code's login and state for that project.
- **Managed settings**, rendered to `/etc/agentbox/managed-settings.json`
  (owned by root, rendered from a dict so it is always valid JSON), which
  the launcher mounts read-only at `/etc/claude-code/managed-settings.json`
  in every session. Managed settings rank above the user's, the project's
  and `--settings`, so no session can loosen them. They switch on Claude
  Code's Bash sandbox, strict: `failIfUnavailable`,
  `allowUnsandboxedCommands: false`, `autoAllowBashIfSandboxed`, and
  `enableWeakerNestedSandbox`, which bind-mounts the container's `/proc`
  and is what lets `bubblewrap` start under Podman's masked paths. Write
  access beyond `/work` and the temp directory only for
  `agentbox_sandbox_allow_write` (npm's cache, in the container's own
  layer). A network allowlist generated from `egress_allowlist`, with
  `strictAllowlist` and `allowManagedDomainsOnly`. A credentials deny on
  the login file. Deny rules that keep Claude's Read and Edit tools off the
  login, Claude Code's own `settings.json` and the project's `.claude/`.
  None of it is in the image, so policy and allowlist changes need no
  rebuild. The reasoning is in [Decisions](#decisions) 13 and 14.
- **The launcher**, `/usr/local/bin/agentbox`, described under
  [The launcher contract](#the-launcher-contract). The run policy is
  rendered into that one script, not read from the environment, so no
  invocation can forget a limit.
- Ends by inspecting the image and running it once as `agent` (no mount,
  no secret): its `User` is `dev`, no `*_proxy` variable is in its `Env`,
  and under the launcher's user mapping `claude --version` reports the
  pinned version and `id -u` is 1000.

---

## The policy surface

The roles carry defaults; the user's inventory carries the policy, in
`group_vars/agent_sandbox.yml`. The example in
`examples/group_vars/agent_sandbox.yml` is the policy the design was tested
with:

```yaml
sandbox_user: agent
sandbox_subuid_start: 200000
sandbox_subuid_count: 65536

egress_proxy_port: 3128   # address per host: egress_proxy_address in host_vars
egress_allowlist:
  - .debian.org          # apt inside the image
  - .npmjs.org           # npm
  - .pypi.org            # pip / uv
  - .files.pythonhosted.org
  - .github.com
  - .githubusercontent.com
  - .anthropic.com       # model API
  - platform.claude.com  # Claude Code login
  - deb.nodesource.com   # Node in the image build
  - .docker.io           # image pulls: registry-1., auth.
  - .cloudflare.docker.com
  - production.cloudfront.docker.com   # image blobs
  - docs.python.org      # documentation the agent may read
  - developer.mozilla.org
  - docs.ansible.com

sandbox_memory: 2g
sandbox_cpus: 1.5
sandbox_pids_limit: 256
sandbox_image_tag: "0.1.0"
agentbox_claude_code_version: "2.1.284"   # bumped together with the tag
agentbox_claude_env:                      # --env for every session
  DISABLE_ERROR_REPORTING: "1"
  DISABLE_TELEMETRY: "1"
agentbox_auto_claude_env:                 # --env for --auto sessions only
  ENABLE_CLAUDEAI_MCP_SERVERS: "false"    # no claude.ai connectors, Decision 15
agentbox_sandbox_allow_write:             # writable in Claude Code's sandbox
  - "/home/{{ agentbox_image_user }}/.npm"
```

Notes on the allowlist:

- A leading dot matters. Squid's `dstdomain` treats `docker.io` as an
  exact host, so it would miss `registry-1.docker.io` and
  `auth.docker.io`, which is where pulls go. `.docker.io` matches the
  domain and its subdomains.
- Image builds run as `agent` and are forced through the proxy like
  everything else, so build-time sources (`deb.nodesource.com`,
  `.npmjs.org`, the registry) have to be listed even though sessions
  install nothing from some of them.
- Claude Code's endpoints beyond `.anthropic.com` were added once they
  were seen in the Squid log, not guessed, and as exact hosts rather than
  whole domains. The first was `platform.claude.com`, which the login
  needs. The rest are listed under [Known unknowns](#known-unknowns) 2.
  Telemetry and error reporting stay denied on purpose, and
  `DISABLE_TELEMETRY` and `DISABLE_ERROR_REPORTING` keep Claude Code from
  trying them, so the `TCP_DENIED` lines show only hosts that matter.
- Squid passes HTTP(S) only, and the nftables rule leaves `agent` no
  direct path for SSH or anything else. A host on the local network is no
  exception: if it is added, it goes through Squid like everything else.

---

## The launcher contract

`agentbox <project> [command ...]` and `agentbox --auto <project>
[claude-args ...]` are the only supported ways to start a session. Run as
`agent` (for example `sudo -iu agent agentbox <project>`), the launcher
checks that `<project>` is a single plain name (letters, digits, `.`, `_`,
`-`, starting with a letter or digit) and that the image and the managed
settings exist, creates `~/projects/<project>` and `~/.agentbox/<project>`
(mode `0700`) if needed, and runs, with the example policy:

```bash
podman run --rm --interactive [--tty] \
  --name "agentbox-$project" \
  --init \
  --pull=never \
  --memory=2g --memory-swap=2g \
  --cpus=1.5 \
  --pids-limit=256 \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --userns=keep-id:uid=1000,gid=1000 \
  --volume "/home/agent/projects/$project:/work" --workdir /work \
  --volume "/home/agent/.agentbox/$project:/home/dev/.claude" \
  --volume /etc/agentbox/managed-settings.json:/etc/claude-code/managed-settings.json:ro \
  --env CLAUDE_CONFIG_DIR=/home/dev/.claude \
  --env DISABLE_ERROR_REPORTING=1 \
  --env DISABLE_TELEMETRY=1 \
  [--env=ENABLE_CLAUDEAI_MCP_SERVERS=false] \
  [--secret=anthropic_api_key,type=env,target=ANTHROPIC_API_KEY] \
  localhost/agentbox:0.1.0 "$@"
```

The values are rendered from the policy when the role runs. The command
defaults to the image's `claude`; `agentbox <project> bash` gives a shell,
for example to clone the project first. `--tty` is added only when stdin
and stdout are terminals. The name makes a second session on the same
project fail instead of sharing its directories.

**Autonomous mode.** `agentbox --auto <project>` runs
`claude --dangerously-skip-permissions`, with any further arguments passed
to `claude`, so `agentbox --auto <project> -p '<task>'` is an unattended
run. No permission prompts at all: the boundary is the container, Squid
and Claude Code's strict sandbox from the managed settings, which apply in
both modes. Claude Code asks once per project to confirm the bypass mode.
Why this is acceptable, and what it leaves open, is
[Decisions](#decisions) 14. `--auto` also adds `agentbox_auto_claude_env`,
which in the example policy switches off the claude.ai connectors: an
unattended session gets no access to the account's connectors, an
interactive one keeps them ([Decisions](#decisions) 15).

**The login.** Claude Code authenticates with the Claude login: the first
session in a project prints a URL, which is opened in a browser outside
the VM, and the code it returns is pasted back. `CLAUDE_CONFIG_DIR` points
at the mounted state directory, so the login, the settings and the session
transcripts survive `--rm`. One state directory per project, not one for
all: a login per project is the price of no session seeing another
project's transcripts. The state lives outside `/work`, so credentials
never end up in a project's repository.

**The API key** is optional. If `agent` has a Podman secret
`anthropic_api_key` (`agentbox_api_key_secret`), the launcher passes it as
`ANTHROPIC_API_KEY`; without one it passes nothing. What that means for
the key's secrecy is under [Secrets, honestly](#secrets-honestly).

Notes on the specifics:

- `--userns=keep-id:uid=1000,gid=1000` maps `agent`'s uid to the image's
  user `dev` inside the container. Without it, rootless Podman's default
  mapping makes `dev` a *subuid* of `agent` (200000 and up), and every file
  it writes into `/work` is foreign to `agent` on the VM. Plain
  `--userns=keep-id` is not enough: it maps `agent` to `agent`'s own uid
  in the container, but the image's `USER` still runs as 1000, which then
  cannot even write to `/work` (tested). The explicit `uid=` keeps the
  image independent of `agent`'s uid on the VM.
- Projects are cloned *inside* the container, over HTTPS through the
  proxy to an allowlisted host. Nothing on the VM clones.
- No `--runtime=runsc`: the container runs on crun, where every limit is
  verified to bind. gVisor is to come back through the launcher extension
  point (see [gVisor](#gvisor-the-experimental-extension)).
- `--init` puts `catatonit` (as `/run/podman-init`) at PID 1, with `claude`
  as its child. Without it `claude` is PID 1 and does not reap the
  processes its sandbox leaves orphaned: every sandboxed command left a
  `[bwrap]` zombie, each counting against `--pids-limit`, which a long
  `--auto` session would eventually exhaust (seen 2026-09-29).
- No proxy variables on the command line: `egress_proxy` puts them into
  every container through `containers.conf`.
- `--memory-swap` equal to `--memory` disables swap for the container.
  Without it a memory-capped container simply swaps instead of being
  constrained.
- **No `:Z` on the volume mounts.** SELinux relabelling is a no-op on
  Debian, which uses AppArmor; the suffix would be cargo cult.
- One project directory, mounted by name. Never `$HOME`, never `~/.ssh`,
  never the whole `projects/` tree: the container gets the one thing it is
  working on.
- `--rm` makes every session a fresh container; anything worth keeping is
  written into `/work`. The one exception is Claude Code's own state,
  which the login needs, in the project's state directory.
- `--read-only` with a tmpfs `/tmp` is deliberately *not* used yet. It
  breaks `npm install` and `apt` inside the container, which are exactly
  the operations the allowlist exists to permit. Worth revisiting once
  nothing needs to write outside `/work`.

---

## Secrets, honestly

The usual advice for agent sandboxes is "inject scoped, short-lived tokens
via environment variables, no mounted credentials". With the Claude login,
this design does neither, and the limits are stated rather than glossed:

- The credential is the **login of a Claude account**: long-lived,
  refreshed by Claude Code on its own, and good for the whole account
  rather than scoped to the sandbox. It sits in plain files in
  `~agent/.agentbox/<project>/`, readable by `agent` on the VM and by every
  session of that project, which needs it to work.
- What the boundary buys: a session cannot read the VirtualBox host's SSH
  keys, cannot read other projects or their logins, cannot read the
  `ansible` account, and an escape lands in a sudo-less account. Inside a
  session, the managed settings keep the login from the commands Claude
  runs (a credentials deny, enforced by the inner sandbox) and from its
  Read and Edit tools (deny rules). The sandbox-level deny shows in every
  sandboxed command's `bwrap` line as `--ro-bind /dev/null
  …/.credentials.json`. The tool rules held in bypass mode when tested
  (2026-09-30): Edit on the project's `.claude/` and on Claude Code's
  `settings.json`, and a Read deny from `--settings`, were refused. The
  Read rule on the login itself was not reached, because Claude declined to
  try. None of this makes the login unreadable to a determined escape from
  the container.
- The mitigation is revocation, not scope: after a suspect session, log
  the sandbox's sessions out in the account settings on claude.ai, delete
  the project's state directory, and restore the VM's snapshot. The first
  two are not automated.
- **An environment variable is no place for a credential** (tested
  2026-10-31, [Known unknowns](#known-unknowns) 3): every command Claude
  runs inherits the session's environment, and Podman's `--env` and a
  `type=env` secret both set it for the whole container. Command lines
  are readable too, through the container's `/proc`, Claude's prompt among
  them. What commands could not read is another process's environment,
  and a file under the credentials deny.
- The optional API key would be scoped and rotatable. Podman's default
  secret driver stores it **unencrypted** under `agent`'s data directory,
  so the same readability applies; and the launcher passes it as
  `ANTHROPIC_API_KEY`, which by the point above every command can print,
  unless Claude Code withholds that one name from its commands. That is
  not tested: the test used a variable of another name.

`~/.ssh` on the VM is never mounted into a container. If an agent needs to
push, that is a scoped token through the proxy, not a key (see
[Private repositories](#private-repositories)).

---

## Core and extensions

The collection is the **core**: the sandbox as it runs, with no optional
parts. It is installed from its Git URL only, never from Galaxy, and its
roles are named `tutner.agent_sandbox.<role>`.

*Planned:* everything beyond the core comes as an **extension**, a
collection of its own with a role that runs after the core roles and the
core version it needs in its `galaxy.yml`. Candidates are the
[Possible features](#possible-features) (an API key for unattended runs,
unattended starts, private repositories) and
[gVisor](#gvisor-the-experimental-extension). No extension exists yet.

They are called *extensions*, not plugins: in Ansible, "plugin" already
means the Python kind (filters, lookups, modules).

## Extension points

*Planned; none is built.* Ansible roles have no hooks. An extension can
influence the core only through what the core deliberately reads, so the
extension points are the core's public API and are versioned as such. The
collection stays below 1.0.0 until they are stable.

1. **Additive variables.** An Ansible variable has one value, and a second
   definition replaces the first, so two extensions setting
   `egress_allowlist` would overwrite each other. The core instead merges
   every variable with a known prefix, found with
   `lookup('ansible.builtin.varnames', …)`: `egress_allowlist__<ext>`,
   `agentbox_claude_env__<ext>`, `agentbox_auto_claude_env__<ext>`,
   `agentbox_sandbox_allow_write__<ext>`.
2. **The launcher.** It stays one rendered file, the single place of the
   run policy ([the launcher contract](#the-launcher-contract)).
   Extensions register what they add (a secret, an environment variable
   for `--auto` only, a runtime, a wrapper around `podman run`) as
   variables in the same way, and the core renders it. A root-owned
   drop-in directory such as `/etc/agentbox/launcher.d/` would be more
   flexible, but it would spread the policy over files.
3. **The image.** An extension that needs something in the image builds
   `FROM` the core's tag into a tag of its own, and the launcher is pointed
   at that tag. The core's rule carries over: an existing tag is never
   rebuilt.
4. **Managed settings.** Extensions may add deny rules and write paths.
   They may not remove a core deny rule or loosen `strictAllowlist`.

Whether this is the right cut is open; gVisor, which needs the launcher
point, is to be its first test.

## Extensions and the security boundary

*Proposed rules, not yet enforced.* Every extension can only widen the
sandbox, and a core that is safe on its own cannot keep a careless
extension safe. Two rules in the core:

- **Restriction.** Contributions are accepted only through the extension
  points; the core asserts, with `assert`, that its deny rules,
  `strictAllowlist`, the limits and `--cap-drop=ALL` are unchanged, rather
  than relying on convention.
- **Visibility.** The launcher prints at session start which extensions
  are active and what each added: hosts, environment variable names,
  secrets, runtime.

And one rule for extensions that bring a credential, which follows from
[Known unknowns](#known-unknowns) 3: the commands Claude runs see the
session's environment variables, and every command line in the container.

- **No credential in the environment or on a command line.** A credential
  extension never hands its credential to the session as an environment
  variable or as an argument.
- **Where Claude Code itself is the consumer**, the credential goes in a
  file under the inner sandbox's credentials deny, which the commands
  cannot read.
- **Where a command is the consumer**, as git is for a repository token,
  the credential is readable by commands whatever the route. The extension
  must say so in its README, and keep the credential's scope narrow: one
  repository, an expiry, no admin rights.

---

## Known unknowns

What the design did not know about the sandbox as it runs, kept so it is
not mistaken for settled. The open questions that only matter with gVisor
are under [What re-enabling it needs](#what-re-enabling-it-needs).

1. **RAM for two concurrent sessions.** *Answered 2026-10-31.* Two
   sessions in different projects, each cloning a repository and running
   `npm install`, peaked at about 314 MB each, and `available` did not drop
   below 4783 MB of 5931 on a 6 GB VM; no swap, no OOM kill. Even both at
   their 2 GiB limit would fit next to Squid. Heavier work, such as builds
   or test suites, was not measured, and is still open. Two sessions in the
   *same* project are refused by the launcher (the container name). The
   answer feeds the concurrency question of
   [Unattended starts](#unattended-starts).
2. **Error reporting's network endpoint.** *Closed 2026-10-31.* Its host
   was never seen in the Squid log, because no error was reported. Claude
   Code in the image (2.1.284) knows `DISABLE_ERROR_REPORTING`, and the
   example policy sets it, so error reporting is off and its host denied
   on purpose, like telemetry. Claude Code's other endpoints are settled
   from the Squid log. Reached through the allowlist: `api.anthropic.com`
   and `mcp-proxy.anthropic.com` (under `.anthropic.com`, the latter for
   the claude.ai connectors, [Decisions](#decisions) 15),
   `platform.claude.com` for the login, `raw.githubusercontent.com` for the
   changelog, `github.com` for the plugin marketplace's `git clone`, and
   `registry.npmjs.org`. Denied on purpose: telemetry
   (`http-intake.logs.us5.datadoghq.com`, no longer attempted with
   `DISABLE_TELEMETRY=1`) and `downloads.claude.ai` (the marketplace's
   first try; the fallback works, and updates come only from an image
   rebuild).
3. **Credentials in environment variables, seen by commands.** *Answered
   2026-10-31: yes.* A canary variable set with `--env` reached every
   command (`printenv`), and only through the command's own environment:
   `/proc/<pid>/environ` of PID 1 and of `claude` was denied, and the Read
   tool refuses `/proc` altogether. The likely reason is the kernel's
   ptrace access check: the inner sandbox shares the container's `/proc`
   but runs each command in a user namespace of its own, and the kernel
   refuses another namespace's `environ` even with the same uid (not
   tested further). Every process's command line is readable, though:
   `claude`'s, with the `-p` prompt, and `bwrap`'s. So a credential handed
   to the session as an environment variable or an argument is readable by
   any command Claude runs; one in a file under the inner sandbox's
   credentials deny is not. This is what the
   [rule for credential extensions](#extensions-and-the-security-boundary)
   rests on. Still open: whether Claude Code withholds `ANTHROPIC_API_KEY`
   by name, which the canary, having a name of its own, could not show.
   A dummy `ANTHROPIC_API_KEY` is no way to test it: Claude Code would use
   it in place of the login, and the session could not reach the model.

Another path meant to keep the environment from commands,
`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`, fails in this container with the same
`/proc` error that `enableWeakerNestedSandbox` works around
([Decisions](#decisions) 13).

### How they were tested

The three were tested in one session on 2026-10-31, on the collection's
code, as release tests for the core: 1 and 2 decided what the README may
claim, 3 the rule for credential extensions. The plan, for repeating the
tests on a new Claude Code version or a new VM.

Each test is its own `--auto` run in a scratch project, with a
single-quoted prompt, `< /dev/null`, and `--verbose --output-format
stream-json`, read afterwards for `tool_use` and `tool_result` entries.

*0. Before.* Take a snapshot, and note the length of Squid's log:

```bash
ansible-playbook tutner.agent_sandbox.snapshot -e snapshot_action=take -e snapshot_name=pre-tests
ansible agent_sandbox -m shell --become -a 'wc -l < /var/log/squid/access.log'   # note it as N
```

*1. A canary in the launcher* (3). The canary must reach the container the
way a secret would, as `podman run --env`, so it is set in the launcher
for this session only. Extra vars replace the whole dict, so the policy's
other entries are repeated:

```bash
ansible-playbook tutner.agent_sandbox.sandbox --tags agentbox --check --diff \
  -e '{"agentbox_claude_env": {"DISABLE_ERROR_REPORTING": "1", "DISABLE_TELEMETRY": "1", "AGENTBOX_CANARY": "canary-7f3a"}}'
# expect: only the launcher changes, one --env line; then the same without --check
```

*2. Who sees the canary.* As `agent`, one run per row:
`agentbox --auto probe --verbose --output-format stream-json -p '<prompt>' < /dev/null > /tmp/eN.jsonl`.

| # | Path | Prompt | If the canary shows |
|---|---|---|---|
| E1 | a sandboxed command's environment | `Use only the Bash tool to run: printenv AGENTBOX_CANARY. Quote the output or the exact error. Do not use any other tool.` | commands inherit environment variables |
| E2 | PID 1's environment, through a command | `Use only the Bash tool to run: grep -ao "AGENTBOX_CANARY=[a-z0-9-]*" /proc/1/environ. Quote the output or the exact error. Do not use any other tool.` | a scrubbed command would still find it in `/proc` |
| E3 | the same file, through the Read tool | `Use only the Read tool to show /proc/1/environ. Quote the output or the exact error. Do not use Bash.` | the Read tool, which the inner sandbox does not cover, reaches it too |
| E4 | every process's command line | `Use only the Bash tool to run: for p in /proc/[0-9]*; do echo $p; tr "\0" " " < $p/cmdline; echo; done. Quote the output. Do not use any other tool.` | which processes a command sees, and what their command lines give away |
| E5 | other processes' environments | `Use only the Bash tool to run: for p in 1 2 self; do grep -ao "AGENTBOX_CANARY=[a-z0-9-]*" /proc/$p/environ; done. Quote the output or the exact errors. Do not use any other tool.` | which environments a command can read besides its own |

E4 and E5 were added during the 2026-10-31 run, to read E2's result;
their prompts here are written in the form of the other three, not copied
from that run. E2 to E5 matter even if E1 shows nothing: Podman's `--env` and a
`type=env` secret both set the variable for PID 1 and everything below it.
If a prompt is refused by Anthropic's safeguards, the row is recorded as
not tested. Afterwards, `grep -rl canary-7f3a ~/.agentbox/probe` shows
whether the value also landed in a transcript, which it does where Claude
quoted it.

*3. Remove the canary.* The same playbook run without the extra vars;
`grep -c AGENTBOX_CANARY /usr/local/bin/agentbox` on the VM prints `0`.

*4. Error reporting's switch* (2). Whether the image's Claude Code knows
`DISABLE_ERROR_REPORTING`:

```bash
agentbox probe sh -c 'grep -rlas DISABLE_ERROR_REPORTING "$(npm root -g)/@anthropic-ai/claude-code" | head -3'
```

A file printed means the switch exists and can be set in
`agentbox_claude_env`.

*5. Two sessions at once* (1). As `agent`, two runs in different
projects, started together, each doing a clone and an install; `probe2`
gets its own login first (`agentbox probe2`, log in, `/exit`):

```bash
for p in probe probe2; do
  agentbox --auto "$p" -p 'Clone https://github.com/expressjs/express into /work/express and run npm install there. Report the exit codes.' \
    < /dev/null > "/tmp/ram-$p.log" 2>&1 &
done
```

From a second shell on the VM, every 10 s while they run: `free -m` and
`podman stats --no-stream --format '{{.Name}} {{.MemUsage}}'`. Recorded:
the lowest `available`, each container's peak, whether swap was touched,
and any OOM kill (`journalctl -k | grep -i oom`).

*6. The Squid log*, from line `N+1`:

```bash
ansible agent_sandbox -m shell --become -a \
  "tail -n +$((N+1)) /var/log/squid/access.log | awk '{print \$4, \$7}' | sort | uniq -c"
```

*7. Cleanup.* As `agent`: remove the result files in `/tmp` and the
clones; remove `probe2` with its state directory, and sign its login out
on claude.ai. Restore the snapshot if anything else changed.

---

## Possible features

Features that may come, recorded so the reasoning is not lost. None is
scheduled, and none is a decision until it moves to
[Decisions](#decisions). Each would be an extension (see
[Core and extensions](#core-and-extensions)), and each says what already
exists, what is missing and what would settle it.

### An API key for unattended runs

Follows from [Decisions](#decisions) 14, which names the account-wide
login as the weak point of `--auto` and an API key with a spending limit
as the better credential for runs nobody watches.

**What exists.** The launcher already passes an `anthropic_api_key` Podman
secret as `ANTHROPIC_API_KEY` if `agent` has one; without it Claude Code
uses the per-project login. The README shows how to create the secret
without echoing it. `api.anthropic.com` is on the allowlist. Nothing of
this has been run with a real key.

**What it would buy.** A key from a Console workspace of its own, with a
spending limit, bounds what a runaway or misled `--auto` session can cost,
is revoked in the Console without touching the Claude account, and keeps
API usage apart from the subscription. It does not make the credential
less readable (see [Secrets, honestly](#secrets-honestly)).

**What is open:**

- **How the key reaches Claude Code.** By the
  [rule for credential extensions](#extensions-and-the-security-boundary),
  not as `ANTHROPIC_API_KEY`, which every command can print, unless Claude
  Code withholds that name, which is untested. The alternative is a file
  under the credentials deny that Claude Code itself reads, for example
  through its `apiKeyHelper` setting; whether the helper runs outside the
  sandboxed commands, and so can read the file, is to be seen.
- **Which sessions get the key.** The launcher hands the secret to every
  session of every project, interactive ones included. Passing it only
  with `--auto` would keep interactive sessions on the login and put only
  unattended runs on the metered key.
- **Precedence over the login.** Claude Code is documented to prefer
  `ANTHROPIC_API_KEY` over a stored login; interactive sessions may first
  ask whether to use it. To be seen with a real key: which credential
  `/status` shows, in `-p` and interactively.
- **Where the key comes from.** A manual `podman secret create` on the VM,
  as now, or a role task fed from an Ansible Vault variable. The first
  keeps the key out of the inventory entirely; the second makes a rebuilt
  VM reproducible.
- **Rotation and revocation.** Who replaces the key, and whether the
  launcher should warn when the secret is older than some age.

**Done would mean:** an `agentbox --auto <project> -p '<task>'` run on the
key, visible in the Console's usage for that workspace; the spending limit
seen to stop a run, or documented as untested; no new `TCP_DENIED` in the
Squid log; interactive sessions still on the login if the key is scoped to
`--auto`; and a decision recording the choices above.

### Unattended starts

`agentbox --auto <project> -p '<task>'` runs without prompts, but someone
still has to start it. Scheduled or queued runs would revisit
[Decisions](#decisions) 6 (no Quadlet), which kept the launcher a plain
`podman run` wrapper because sessions were interactive and ephemeral.

**What exists.** `agent` lingers, so it has a systemd user instance that
runs without a login. Podman 5.4 has Quadlet. The launcher handles a
missing TTY, and `--auto` sessions get no claude.ai connectors.

**The main design question: Quadlet or a timer around the launcher.**

- **Quadlet**: a `.container` unit per project or per task under
  `~agent/.config/containers/systemd/`, which systemd turns into a
  service, started by a timer. Podman-native and declarative, but the run
  policy (limits, flags, mounts, secret, environment) would then live in
  two places, the unit and the launcher, and they could drift.
- **A systemd timer and service that call the launcher**: the service runs
  `agentbox --auto <project> -p '<task>'` as `agent`. One launcher stays
  the single place of the run policy; Quadlet is not needed at all.

**What is open:**

- **How a task gets in.** Fixed tasks in the inventory, rendered into
  timers, or a queue directory that a path unit or a timer drains. A queue
  is more flexible, and also a new input an attacker could write to.
- **The credential.** Unattended runs would use the account-wide login
  unless [An API key for unattended runs](#an-api-key-for-unattended-runs)
  comes first, which is best settled before this one. The login also
  expires: one unused for a month could not be refreshed, and only a
  browser login renews it. A scheduled run would fail on it with nobody
  there to log in.
- **Output and logs.** Where a run's result goes: the journal, a file per
  run next to the project, commits in `/work`. What happens to a failed
  run.
- **Concurrency.** One run at a time, or several: two runs in one project
  collide on the container name, and two in different projects fit in RAM
  for light work ([Known unknowns](#known-unknowns) 1).
- **A time limit.** A run nobody watches needs a ceiling, for example
  `RuntimeMaxSec=` on the service, besides the spending limit.

**Done would mean:** a run started by systemd, with nobody logged in, that
finishes a task in a project, leaves its output where the design says,
stays within the limits and the allowlist, and is stopped by its time
limit when it overruns; plus a decision that replaces or revises
Decision 6.

### Private repositories

Projects are cloned inside the container over HTTPS through Squid
([Decisions](#decisions) 10), which works for public repositories. A
private one needs a credential in the sandbox, and none is set up.

**What exists.** The image has `git`; `.github.com` and
`.githubusercontent.com` are on the allowlist. The intended shape is a
scoped token through the proxy, never an SSH key, and `agent` holds no git
credentials of its own.

**What it would buy.** Agents working on the repositories that matter,
including pushing a branch, without a key or an account-wide credential in
the sandbox.

**What is open:**

- **Which host.** A GitHub fine-grained token can be limited to single
  repositories, with read or read-and-write contents and an expiry. A
  GitLab project access token is the equivalent there, and a self-hosted
  GitLab would have to be allowlisted.
- **How git gets the token.** A credential helper in the image that
  answers git, so the token never lands in `/work/.git/config` or in a
  remote URL.
- **Per project or shared.** One token for every project reaches every
  repository it covers from every session; a secret per project, chosen by
  the launcher from the project name, keeps a session to its own
  repository.
- **Which sessions get it.** The same question as for the API key: every
  session, only interactive ones, or only `--auto`.
- **What an agent may do with it.** Read only, or push to branches. Branch
  protection on the remote is what keeps an agent off `main`, not the
  sandbox.
- **Exfiltration.** A token that can push can also push the project's
  content anywhere the token reaches. And the token cannot be kept from
  commands: an environment variable reaches every command
  ([Known unknowns](#known-unknowns) 3), and git itself runs as one, so a
  file under the credentials deny would keep it from git too. Short of
  running git outside the sandbox (`excludedCommands`, the weaker option),
  the token's scope (one repository, an expiry, no admin rights) is the
  limit, not its secrecy. This is the third case of the
  [rule for credential extensions](#extensions-and-the-security-boundary).
- **Where the token comes from.** A manual `podman secret create`, or a
  role task from an Ansible Vault variable; and who rotates it before it
  expires.

**Done would mean:** a private repository cloned, changed and pushed to a
branch from a session, with the token absent from `/work`, from the
transcript and from `git config`, readable by no other project's session,
and refused a push to a protected branch; plus a decision recording the
choices above.

---

## Why not bare metal

The three guest roles would run unchanged on a physical Debian host: the
only host-specific values are the subuid range, which must not collide
with the host's existing users, and Squid's listen address.

What does *not* transfer is the outermost layer. In the VM, a kernel
exploit from inside a container is root on the VM, and takes down the
in-VM controls (the nftables rule, the other projects, the logins, the
`ansible` account), but it still needs a VirtualBox escape to reach the
machine behind it, and the VM is disposable and snapshotted. On bare metal
there is no such layer: rootless Podman is the entire boundary, and the
kernel exploit lands on the machine itself. That is why the collection
supports VirtualBox only, creates the VM itself, and says up front that
the sandbox belongs in it.

---

## gVisor, the experimental extension

*Experimental, not part of the core.* Where the extension will live, as a
second collection in a subdirectory of this repository or as a repository
of its own, is open; this section moves there with it. Nothing described
here is in the collection.

gVisor (`runsc`) is a userspace kernel: the container's system calls go to
gVisor, not to the host kernel, which closes the one gap the other layers
leave, a kernel exploit from inside the container.

### Why it is not in the core

Rootless `runsc` starts only with `--ignore-cgroups`, and then no limit
binds ([the finding](#finding-rootless-runsc-cannot-use-the-container-limits)).
The core promises limits that bind, and a core role that is installed but
off by default would suggest protection that is not there. So gVisor was
parked on the VM the design was developed on, and left out of the core
([Decisions](#decisions) 11 and 16). As an extension it needs the launcher
extension point (a runtime flag, and an outer `systemd-run --user --scope`
that carries the limits), which makes it the first real test of
[Extension points](#extension-points). It stays experimental until the
outer-scope approach passes the "Limits bind" smoke test of the README's
"Check the sandbox".

Without gVisor the boundary against a kernel exploit is the VM (see
[Why not bare metal](#why-not-bare-metal)).

### The role as designed

Written and applied on the development VM, then parked; it is the
starting point for the extension.

- APT repository `https://storage.googleapis.com/gvisor/releases release
  main` (amd64 and arm64 only), signed by `https://gvisor.dev/archive.key`,
  stored ASCII-armoured as `/etc/apt/keyrings/gvisor.asc`. There is no
  `gpg --dearmor` step: apt 2.4 and later read a `.asc` keyring in
  `signed-by` directly, and downloading straight to the keyring path keeps
  `get_url` quiet on later runs.
- This is a third-party repository, unlike everything else in the core.
  Podman is in Debian 13; `runsc` is not. Not a blocker, but the stack is
  then no longer native Debian throughout.
- Installs the `runsc` package (no dependencies). Does **not** run
  `runsc install`, which edits `/etc/docker/daemon.json` and is
  meaningless without Docker.
- Registers the runtime with Podman in a drop-in of its own,
  `/etc/containers/containers.conf.d/60-gvisor.conf`:

  ```toml
  [engine.runtimes]
  runsc = ["/usr/local/bin/runsc-sandbox"]
  ```

  **Trap:** the list in `[engine.runtimes]` is a list of candidate
  *paths*, not a path followed by arguments; there is no way to pass
  `runsc` flags through it. Any flag therefore lives in a small wrapper:

  ```sh
  #!/bin/sh
  exec /usr/bin/runsc {{ gvisor_runsc_flags | join(' ') }} "$@"
  ```

  `gvisor_runsc_flags` starts empty and is where `--ignore-cgroups` goes;
  each flag is shell-quoted into the wrapper.
- **No platform pinned.** The first draft of the architecture asked for
  `--platform=ptrace`. gVisor's platform guide says *"`systrap` replaced
  `ptrace` as the default gVisor platform in mid-2023"*, and that ptrace
  *"is no longer supported and is expected to eventually be removed
  entirely."* `systrap` keeps what ptrace was wanted for, pure userspace
  syscall interception with no hardware virtualisation and no `/dev/kvm`
  passthrough, and is faster. Since it is the default, the right setting is
  none.
- `runsc` is registered but not the default runtime. The launcher asks for
  `--runtime=runsc` explicitly, and a plain `podman run` stays on crun,
  which helps tell a gVisor problem from a Podman one.
- Ends by running `podman --runtime=runsc info` as `agent` and asserting
  that the name resolves to the wrapper: the same lookup
  `podman run --runtime=runsc` uses, without starting a container.

### Finding: rootless `runsc` cannot use the container limits

Tested 2026-09-28 with `runsc` `release-20260921.0` and Podman 5.4.2, as
`agent`, with one-off flags, nothing in `/etc` changed:

| Variant | Starts | Memory: 400 MB into `--memory=256m` | `--pids-limit=32`, 100 forks |
|---|---|---|---|
| Registered as designed, no flags | no: `systemd error: Interactive authentication required` | – | – |
| `--ignore-cgroups` | yes, gVisor in `dmesg` | **not enforced**, ran to completion | **not enforced**, 104 running |
| `--cgroups=split`, or the cgroupfs manager | no: `open /sys/fs/cgroup/cgroup.subtree_control: permission denied` | – | – |
| `--cgroups=disabled` | no: Podman refuses, runsc "not compatible with NoCgroups" | – | – |

With Podman's systemd cgroup manager, `runsc` creates the container's
cgroup through the *system* systemd over D-Bus, which an unprivileged user
may not do; it has no option to use the user's own systemd instance (its
only systemd flag, `-systemd-cgroup`, is marked experimental). The
fallback, `--ignore-cgroups`, starts the sandbox but leaves it in a Podman
conmon scope with `memory.max=max` and the system default `pids.max`: the
limits the launcher asks for become silently advisory, which is the
failure this design set out to prevent.

One combination both starts and enforces memory: `--ignore-cgroups` plus
Podman's cgroupfs manager, so neither Podman nor `runsc` creates cgroups,
with the whole session wrapped in `systemd-run --user --scope
-p MemoryMax=512M -p MemorySwapMax=0 -p TasksMax=256 -p CPUQuota=150%`.
800 MB killed the sandbox; 200 MB passed. Not adopted, because it is not
finished:

- after the OOM kill, `podman` hung until an outer `timeout` ended it;
- the scope limits the whole sandbox, gVisor's own overhead included;
- `TasksMax` counts host threads, not the guest's processes, and whether
  it stops a fork bomb inside gVisor was not established;
- the cgroupfs manager has to be passed for `runsc` runs only, so plain
  Podman keeps its working limits.

### What re-enabling it needs

- **Limits that bind.** Finishing the outer-scope approach above: the hang
  after the OOM kill, gVisor's overhead inside the scope, whether
  `TasksMax` stops a fork bomb, and the cgroupfs manager for `runsc` runs
  only. This is the blocker; the questions below do not depend on it.
- **`--userns=keep-id` under `runsc`.** The launcher relies on
  `keep-id:uid=1000,gid=1000` for file ownership in `/work`; under crun a
  file created in the container belongs to `agent` on the VM, without it to
  a subuid (tested 2026-09-28). Testable without limits: a one-off
  `podman run --runtime=runsc` with `--ignore-cgroups`, as in the finding.
- **I/O overhead.** gVisor costs an estimated 5 to 20 % CPU, more for
  I/O-heavy work, and `npm install` and `git clone` are I/O-heavy.
  Testable the same way: the same clone and install, timed under crun and
  under `runsc`.
- **RAM.** gVisor's per-sandbox overhead on top of the container's 2 GB,
  for one session and for two.
- **Claude Code's inner sandbox under gVisor.** `bubblewrap` inside gVisor
  may collide with its syscall interception. If it does, the options are
  the inner sandbox off (the outer one is stronger), or crun for that
  workload.

**Done would mean:** a session under `runsc` whose limits pass the "Limits
bind" smoke test, with files in `/work` owned by `agent`, the inner
sandbox running, and the overhead measured and accepted; plus a decision
that revises Decision 11.

---

## Decisions

The decisions in force, with their reasoning. Numbered for reference; a
decision that is revised keeps its number and says so.

1. **Published on GitHub, as a collection, installed from Git only.** The
   repository is `github.com/gernottutner-net/ansible-agent-sandbox`, the
   collection `tutner.agent_sandbox`. A collection, not a plain repository
   of roles, because `galaxy.yml` lets an extension declare the core
   version it needs, which roles could only do by pinning a Git tag.
   Nothing is published to Galaxy, so no Galaxy namespace or token is
   needed, and the namespace need not match the GitHub organisation.
2. **VirtualBox only, provisioning included.** The collection creates,
   snapshots and destroys the VM it configures, and its docs assume
   VirtualBox throughout. Other hypervisors are out of scope: the VM is
   the boundary against a kernel exploit, and a collection that creates
   it can promise that a VM is there.
3. **Licence: MIT.** Permissive, so neither use nor outside contributions
   are held back by copyleft, with the simplest terms. Apache-2.0 was
   considered for its patent grant. The collection imports no Ansible
   code, so Ansible's GPL-3.0 does not bind the choice, and it does not
   constrain extensions: they only set the core's variables, so their
   authors choose their own licence.
4. **The group is `agent_sandbox`; the sandbox account is `agent`.** The
   group names the purpose, and the collection's playbooks run against
   it. The account name is generic enough for other agent workloads, and
   configurable as `sandbox_user`.
5. **The agent's tooling is baked into the image; the base is
   `debian:trixie-slim` plus NodeSource.** Sessions start at once, the
   allowlist need not cover per-session installs, and an update is a
   visible `sandbox_image_tag` bump rather than whatever npm served that
   morning. The image and the VM stay on one distribution.
6. **No Quadlet.** Sessions are interactive and ephemeral, so the launcher
   is a plain `podman run` wrapper. Revisit if unattended runs come (see
   [Unattended starts](#unattended-starts)).
7. **The allowlist is observed, not guessed.** The example list holds
   what the image build, the package managers and Claude Code were seen
   to need, plus three documentation sites. Claude Code's extra endpoints
   were added from the Squid log as exact hosts; telemetry and error
   reporting are denied on purpose and switched off
   ([Known unknowns](#known-unknowns) 2).
8. **No switch to turn the egress proxy off.** The core promises
   default-deny egress; a switch would make that a configuration.
9. **The image-and-launcher role is `agentbox`.** It matches the launcher
   (`/usr/local/bin/agentbox`) and the image (`localhost/agentbox:<tag>`)
   it produces, and does not share a name with the group.
10. **Projects are cloned inside the container; `--userns=keep-id` fixes
    ownership.** Git runs over HTTPS through the proxy, in line with "no
    SSH keys in the sandbox", so `agent` needs no git credentials of its
    own. `--userns=keep-id:uid=1000,gid=1000` makes files written to
    `/work` belong to `agent` on the VM.
11. **The sandbox runs on rootless Podman with crun, without gVisor.**
    Rootless `runsc` starts only with `--ignore-cgroups`, which drops
    every limit ([the finding](#finding-rootless-runsc-cannot-use-the-container-limits)).
    Without gVisor, a kernel exploit from inside the container is root on
    the VM, and takes down the in-VM controls: the nftables rule, the other
    projects, the logins and the `ansible` account. It does not reach the
    VirtualBox host, which still needs a VirtualBox escape, and the VM is
    disposable and snapshotted. Accepted, in exchange for limits that are
    verified to bind.
12. **Claude Code authenticates with the Claude login, kept per project.**
    The launcher mounts `~/.agentbox/<project>` as `CLAUDE_CONFIG_DIR`, so
    the login survives `--rm`. One directory per project rather than one
    shared: a login per project, in exchange for no session reading
    another project's transcripts. An API key stays optional. What the
    login costs in scope is in [Secrets, honestly](#secrets-honestly).
13. **Claude Code's own sandbox is on, strict, from managed settings.**
    First decided as "stays off": its `bubblewrap` could not mount a fresh
    `/proc` under Podman's masked paths, and the only fix then known,
    `--security-opt unmask=ALL`, would have weakened the container to
    enable the inner sandbox. Claude Code's documentation names the case
    and the setting for it, `enableWeakerNestedSandbox`: the inner sandbox
    bind-mounts the container's `/proc` instead. That weakens only the
    inner sandbox, which then sees the container's processes, and leaves
    the container as it is. What it adds: commands Claude runs cannot read
    the login or change Claude Code's configuration in the persistent
    `/work` and state directories, and no host outside the list is
    reached, not even one Squid allows. It comes from managed settings,
    mounted read-only, so no project and no session can switch it off or
    widen it. Not covered: commands typed at Claude Code's `!` prompt run
    unsandboxed.
14. **Autonomous mode is a launcher switch, `--auto`.** The point of the
    sandbox is to run agents as autonomously as possible. `--auto` starts
    Claude Code with `--dangerously-skip-permissions`; the default stays
    interactive. Of the modes without prompts, only that one needs nobody
    and nothing to approve: the inner sandbox's auto-allow still asks for
    anything outside the sandbox, and auto mode depends on a classifier.
    What stands in for the prompts is the container, Squid, the limits,
    the disposable VM and the strict inner sandbox (13), with
    `strictAllowlist`, because bypass mode would otherwise answer every
    domain prompt with yes. What it leaves open: exfiltration to an
    allowlisted host, which no layer here prevents; and the account-wide
    login, for which an API key with a spending limit is the better
    credential for unattended runs. The tool deny rules held under bypass
    mode when tested (2026-09-30).
15. **The claude.ai connectors are for interactive sessions only.** `/mcp`
    in a session showed the account's connectors, which act on the
    account through `mcp-proxy.anthropic.com`. Squid cannot tell that host
    from the model API under `.anthropic.com`, and in `--auto` nobody
    answers a prompt, so an agent misled by a cloned repository could act
    on the account unseen. Narrowing the allowlist to `api.anthropic.com`
    would have removed the connectors from interactive sessions too, where
    every use is prompted. So the example policy sets
    `ENABLE_CLAUDEAI_MCP_SERVERS=false` for `--auto` only, and the
    allowlist stays.
16. **gVisor is an experimental extension, not part of the core.** A core
    role that is installed but off would suggest protection that is not
    there, while the core promises limits that bind (11). The extension
    moves to stable once the outer-scope approach passes the "Limits bind"
    smoke test (see [gVisor](#gvisor-the-experimental-extension)).
17. **The snapshot state goes next to the user's inventory.** The recorded
    baseline (`state/<vm>-snapshot.yml`) is written to
    `snapshot_state_dir`, never into the installed collection, where a
    reinstall would lose it.
