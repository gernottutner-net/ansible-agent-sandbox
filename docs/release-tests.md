# Release tests

What is tested before a release, what the runs before `v0.1.0` covered
and found, the first install of that release from GitHub, and the release
tests of `v0.2.0` and `v0.3.0`, the tests of Claude Code 2.1.323
before `v0.4.0`, the release test of `v0.4.0`, the shortened release
tests of `v0.5.0` and `v0.6.0`, and the release test of `v0.7.0`. The [README](../README.md) says how to use the collection,
[docs/virtualbox.md](virtualbox.md) covers the VM, and
[docs/design.md](design.md) why the sandbox is built the way it is.

The runs ran on an Ubuntu 22.04 host with VirtualBox 7.0, against a Debian
13 guest, with Claude Code 2.1.284 in the image, except where a run says
otherwise. Commits named here, such
as `56d06bd`, are this repository's: the code a run tested, or the fix it
led to.

---

## Contents

- [How to run them](#how-to-run-them)
  - [Before](#before)
  - [The steps](#the-steps)
  - [Afterwards](#afterwards)
- [The runs before v0.1.0](#the-runs-before-v010)
  - [First run](#first-run)
  - [Second run](#second-run)
  - [Destroy re-tested](#destroy-re-tested)
  - [Third run](#third-run)
  - [Upgrade of an existing install](#upgrade-of-an-existing-install)
  - [The known unknowns](#the-known-unknowns)
- [The install of v0.1.0 from GitHub](#the-install-of-v010-from-github)
- [The release test of v0.2.0](#the-release-test-of-v020)
  - [The run](#the-run)
  - [Upgrade from v0.1.0](#upgrade-from-v010)
  - [Findings](#findings)
- [The release test of v0.3.0](#the-release-test-of-v030)
  - [The run on a VM of its own](#the-run-on-a-vm-of-its-own)
  - [Upgrade from v0.2.0](#upgrade-from-v020)
  - [Observations](#observations)
- [Claude Code 2.1.323, before v0.4.0](#claude-code-21323-before-v040)
- [The release test of v0.4.0](#the-release-test-of-v040)
  - [Steps 1 to 9](#steps-1-to-9)
  - [Agent Intercom, a short check](#agent-intercom-a-short-check)
  - [Upgrade from v0.3.0](#upgrade-from-v030)
  - [What it found](#what-it-found)
- [The release test of v0.5.0](#the-release-test-of-v050)
- [The release test of v0.6.0](#the-release-test-of-v060)
- [The release test of v0.7.0](#the-release-test-of-v070)
  - [Steps 1 to 9 on rt-vm](#steps-1-to-9-on-rt-vm)
  - [Sessions under tmux, from the controller](#sessions-under-tmux-from-the-controller)
  - [The editor](#the-editor)
  - [The known-unknowns session](#the-known-unknowns-session)
  - [Upgrade from v0.6.0](#upgrade-from-v060)
  - [Findings and observations](#findings-and-observations)
- [Not covered yet](#not-covered-yet)

---

## How to run them

A release is tested on a new VM, from the release's commit, and with the
public docs alone: what a run needs and the docs do not say is a finding,
not a workaround. Every step is a command from the README or from
`docs/virtualbox.md`, run word for word; they are not repeated here.

### Before

- No VM of the test's name, and no snapshot state file for it next to the
  inventory.
- A working directory with `examples/` copied in afresh from the commit
  under test, checked with `diff -r` against it, and a new SSH key, as
  `examples/host_vars/sandbox-vm.yml` says.
- The collection installed from that commit: from the GitHub URL at the
  tag, as under [Install](../README.md#install); before a push, from a
  local clone with `git+file://…` and `--force`. Its roles must be
  identical to the commit's.
- Room on the host for the VM's defaults: 6 GB RAM, 4 CPUs, 40 GB.
- `ansible-lint` and `yamllint` pass on the commit under test, as
  [dev/linting.md](../dev/linting.md#running-them) says.

### The steps

| # | Step | Passes when |
|---|---|---|
| 1 | `provision` | cloud-init is done; the play reports no failure |
| 2 | `sandbox`, first run | the image builds; the roles' own checks pass |
| 3 | `sandbox`, second run | `changed=0` |
| 4 | [Check the sandbox](../README.md#check-the-sandbox), as `agent` | every test gives the result its comment expects; `~/projects` and `~/.agentbox` are left empty |
| 5 | [Repository tokens](../README.md#repository-tokens), for a private repository of your own kept for tests: a `session` token for one project, in `agentbox <project> bash`; a `permanent` one for another, through Claude with `agentbox --auto <project> -p …` | each clones, commits and pushes a branch; the token is in neither `/work`, nor `git config`, nor the transcript; the `session` token is gone from `/run/user/<uid>/agentbox/` after the session, also after the SSH connection was cut; `remove` leaves nothing; `~/projects`, `~/.agentbox` and `~/.agentbox-tokens` are left empty before the baseline |
| 6 | `snapshot` take `base` | the state file is next to the inventory, and the installed collection holds none |
| 7 | take `pre-session`, then restore `pre-session`, then restore `base`, with a marker file written before and one after `pre-session` | `ssh` right after each connects, with no `wait` between; after `pre-session` only the earlier marker is there, after `base` neither |
| 8 | `sandbox` afterwards | `changed=0` |
| 9 | `destroy --limit sandbox-vm -e destroy_confirm=yes`, on the running VM with its two snapshots | no VM, no registered disk or DVD, no machine folder, no build artefacts; the base image cache stays |

A release that changes the peer broker, or Claude Code's version, also
repeats the table in
[docs/design.md, "What was tested"](design.md#what-was-tested-1), and
`python3 dev/test-peer-broker.py` passes. It takes a login in two projects.

Every playbook passes `--syntax-check` first. A release that changes a
role an existing install runs also gets the
[upgrade test](#upgrade-of-an-existing-install): `sandbox --check --diff`
on a VM built from the previous release, which should show exactly the
changes the release's CHANGES.md lists, and `changed=0` once applied. Before the
upgrade, `update_check` lists the release's entry in `meta/updates.yml`
and nothing that does not apply to that VM; after it, `Up to date`.

A release that changes Claude Code's version, the managed settings or the
launcher also repeats the [known unknowns](design.md#how-they-were-tested)
session: its answers hold for the version they were tested on.

A release that changes the launcher also checks
[sessions that outlive the connection](../README.md#sessions-that-outlive-the-connection),
started from the controller with
[`agentbox-remote`](../README.md#from-the-controller): `--tmux` starts a
session and attaches again after a detach, after `kill -9` on the `ssh`
client and after every login of the account Ansible uses has ended;
`--list` shows it as `running tmux`; `tmux kill-session` stops the
container and deletes a `session` token; a second start with arguments,
and a plain start beside it, are refused, both ways round; a project name
with a `.` gets its own tmux session; an `--auto -p` task with quotes,
spaces and `$HOME` in it reaches Claude unchanged.

A release that changes the editor, or the launcher, also checks
[the editor](../README.md#the-editor), with
`agentbox_editor_accept_server_license: true`: the first `sandbox` run
builds the editor image and its own check passes, the second is
`changed=0`; `agentbox <project>` on a terminal prints the editor's line,
`--no-editor` and a `-p` run start none; `agentbox-remote --open-editor`
prints a URL that opens `/work` in a browser, and the URL without its
token gets 403; a VSIX uploaded with "Install from VSIX" is refused as not
in the allowed list; the session's end, `tmux kill-session` and `SIGTERM`
to the launcher each stop the editor and remove its socket directory and
token; `--tmux` keeps the editor across a dropped connection, tried more
than once; two projects with editors at once, each with a project open,
and their memory recorded. Then `sandbox` with the licence set back to
`false` removes the editor's files and group, `changed=0` after.

### Afterwards

Delete the snapshot state file by hand, as `docs/virtualbox.md` says, and
record the run here: the commit, each step's result with its `changed=`
count, what was found, what was fixed and in which commit, and what the
run did not cover.

## The runs before v0.1.0

All on 2026-10-31, on a VM named `sandbox-vm` with the example host_vars
unchanged and the default size. The collection was not on GitHub yet, so
each run installed it from a local clone with `git+file://…`.

### First run

From the initial collection, before any fix.

| Step | Result |
|---|---|
| `provision` | passes: `changed=17`, cloud-init done |
| `sandbox`, first run | **fails** at the image build: Squid denies `production.cloudfront.docker.com`, where Docker Hub now serves image blobs. Passes with the host added to the allowlist. |
| `sandbox`, second run | `changed=0` |
| Smoke tests, as `agent` | all pass: `memory.max` 2147483648; `apt-get update` through the proxy; `example.com` gets 403; the bypass to `1.1.1.1:443` is refused; `getent hosts` resolves nothing. Through the launcher: uid 1000 `dev`, 2 GB, 256 pids, 1.5 CPUs, Claude Code 2.1.284. |
| `snapshot` take `base`, take `pre-session`, restore each | passes: a marker written after `pre-session` is gone after restoring it, one written before is still there, and after restoring `base` neither is. `sandbox` afterwards: `changed=0`. |
| Snapshot state file | **wrong place**: written into the installed collection, under `playbooks/state/`, not next to the inventory, so a reinstall would lose the recorded baseline |

Fixed as `73ba094`:

- `roles/virtualbox_vm/tasks/snapshot.yml` built the state file's path
  from `playbook_dir`, and ignored the `snapshot_state_dir` the defaults
  already declare. With the fix it lands next to the inventory.
- `examples/group_vars/agent_sandbox.yml`: `production.cloudfront.docker.com`
  in `egress_allowlist`.

Also found:

- The smoke tests were not in the docs; the run took them from the
  design notes, with the proxy address changed by hand. Added to the
  README as "Check the sandbox" (`a6e7927`), with the address read from
  `$https_proxy`, and run from there unchanged on the same VM.
- The baseline `base` held the leftovers of the launcher test, the empty
  directories `~agent/projects/smoke` and `~agent/.agentbox/smoke`. The
  README's tests now remove them, before the baseline is taken.

### Second run

A new VM, from `a6e7927`, so only committed code ran. The smoke tests
were taken from the installed collection's README, word for word.

| Step | Result |
|---|---|
| `provision` | passes: `changed=15` |
| `sandbox`, first run | passes, image build included: `changed=29` |
| `sandbox`, second run | `changed=0` |
| Smoke tests from the README, as `agent` | all pass, with the values of the first run; `rmdir` leaves `~/projects` and `~/.agentbox` empty |
| `snapshot` take `base` | passes; the state file is next to the inventory, and the collection holds none |
| take `pre-session`, restore each | passes, with the same markers as in the first run. `sandbox` afterwards: `changed=0`. |

Found:

- **`take` and `restore` returned before the guest answered.** Both
  restart a VM they stopped, and the play ended there: an `ssh` right
  after `take` got "Connection refused". Fixed as `7162bfc`: the role
  records which VMs it started, and a second play in the snapshot
  playbook runs `wait_for_connection` for those alone. Tested on the same
  VM: `list` with the VM off returns at once; `ssh` right after `take` and
  after `restore` succeeds; `sandbox` afterwards `changed=0`.
- **`destroy` failed** on the first run's VM, on the way to this one:
  `unregistervm --delete-all` unregistered it and deleted the snapshot
  images and the seed ISO, then stopped at the base disk with
  `E_ACCESSDENIED … The object is not ready`, leaving the disk registered,
  the `.vbox` files and the build artefacts. `closemedium disk <uuid>
  --delete`, from [Troubleshooting](virtualbox.md#troubleshooting), then
  worked at once. Re-tested below.

### Destroy re-tested

On the second run's VM, from the same state as the failure: restored to
`base`, the sandbox playbook, a clean shutdown. `destroy` failed the same
way.

The cause, found on a throwaway VM with a 64 MB empty disk, nothing
downloaded or booted from:

| Case | `unregistervm --delete-all` |
|---|---|
| no seed ISO: 1 or 2 snapshots, branched, after running | works |
| seed ISO, no snapshot | works |
| seed ISO, 1 snapshot | fails |
| seed ISO, a branched tree like `sandbox-vm`'s | fails |
| seed ISO ejected from the current state first, 1 snapshot | works |
| the same, 2 snapshots | fails |

`--delete-all` fails as soon as the seed ISO is referenced more than once,
by the current state and a snapshot, as on every VM after its first
`take`. The explanation that fits: it deletes the ISO twice and aborts at
the second; not checked against VirtualBox's source. `destroy` had not run
on a VM with snapshots before.

Fixed as `56d06bd`: `roles/virtualbox_vm/tasks/destroy.yml` runs
`unregistervm --delete`, which removes the disks and the `.vbox` but not
the DVD, then `closemedium dvd <seed ISO> --delete` once, then removes the
machine folder after a check that it is named after the VM. On the
throwaway VM this works in all four seed-ISO cases. On a new `sandbox-vm`,
provisioned and given a branched tree (take `s1`, take `s2`, restore
`s1`), `destroy` passed on the running VM in 9 s and left no VM, no
registered medium, no machine folder and no build artefacts; the base
image cache stays. On the absent VM afterwards it reports "nothing to
destroy".

Also found: `destroy` leaves the snapshot state file next to the
inventory, holding the destroyed VM's baseline. Harmless, since the next
`take` rewrites it; [Destroying a VM](virtualbox.md#destroying-a-vm) now
says to delete it by hand if the VM is not coming back.

### Third run

The full run once more, on a new VM, from `56d06bd`, with both fixes
above, and the docs alone; the [steps](#the-steps) above are this run's.
`examples/` copied in afresh and checked with `diff -r`; the
collection reinstalled with `--force`, its roles identical to `56d06bd`.

| Step | Result |
|---|---|
| `provision` | passes: `changed=15` |
| `sandbox`, first run | passes, image build included: `changed=29` |
| `sandbox`, second run | `changed=0` |
| Smoke tests from the README, word for word, as `agent` | all pass, with the same values as before; `~/projects` and `~/.agentbox` left empty |
| `snapshot` take `base` | passes: `changed=5`; the state file is next to the inventory, the collection holds none |
| take `pre-session`, restore `pre-session`, restore `base` | pass: `changed=3` each. `ssh` right after each, with no wait, connects at once. After `pre-session` only the marker written before it is there; after `base`, neither. |
| `sandbox` afterwards | `changed=0` |
| `destroy --limit sandbox-vm -e destroy_confirm=yes` | passes in 8.5 s on the running VM with two snapshots and the seed ISO: `changed=5`. No VM, no registered disk or DVD, no machine folder, no build artefacts; the base image cache stays. The state file then deleted by hand. |

Nothing found. Both fixes from the second run hold in a full run.

### Upgrade of an existing install

The collection was taken from roles that ran, before it existed, on the
VM the design was developed on. That VM was switched to the collection at
`56d06bd` in place: the sandbox roles called from the collection instead
of the older copies, the policy otherwise unchanged, its snapshot state
file moved next to the inventory. It is the only test so far of an
upgrade rather than a fresh install.

| Step | Result |
|---|---|
| `--syntax-check`, every playbook | passes |
| `wait` | passes, `changed=0` |
| `snapshot`, `list` | passes; the moved state file is found, only its header comment is rewritten, and the recorded baseline and its UUID stay |
| `sandbox --check --diff` | in the sandbox roles, `changed=2`: a comment line in `/etc/containers/containers.conf.d/50-ansible.conf`, and a comment and two error messages in the launcher, the differences between the older copies and the collection. No image rebuild: the hash of the image's recipe matches. |
| `sandbox`, applied without a snapshot | the same two files; no handler ran |
| `sandbox --check --diff` again | nothing in the sandbox roles |

Nothing found. Not tested on that VM: `provision` and `destroy`, which
the runs above cover on fresh VMs.

### The known unknowns

The same day, on the upgraded VM and the collection's code, one session
tested what the design did not know: two concurrent sessions, error
reporting's endpoint, and whether the commands in a session see its
environment. The plan and the results are under
[Known unknowns](design.md#known-unknowns) and
[How they were tested](design.md#how-they-were-tested); what is still
open is in the README's [Open questions](../README.md#open-questions).
It led to `47c1e78` (the README on what commands can read) and `a7973ec`
(`DISABLE_ERROR_REPORTING` in the example policy).

## The install of v0.1.0 from GitHub

On 2026-11-02, after `v0.1.0` (`db0261d`) was pushed: the collection
installed from the GitHub URL at the tag, with `--force` over the copy
the upgrade test had installed from a local clone, as under
[Install](../README.md#install).

| Check | Result |
|---|---|
| The install | `tutner.agent_sandbox:0.1.0`, cloned at `db0261d` |
| `diff -r` against `git archive v0.1.0` | identical, except that the build turns `galaxy.yml` into `MANIFEST.json` and `FILES.json` |
| The sandbox roles with `--check --diff`, on the VM of the [upgrade test](#upgrade-of-an-existing-install) | nothing to change, no diff |

Nothing found.

## The release test of v0.2.0

On 2026-11-02, before `v0.2.0` was tagged, with the collection installed
from a local clone with `git+file://…` and `--force`.

### The run

A new VM named `sandbox-vm`, with the example's name, address and MACs;
the VM of the [upgrade test](#upgrade-of-an-existing-install) was
destroyed first. `examples/` copied in afresh from `e31a15e` and checked
with `diff -r`; host_vars changed only in the two key paths, for a new
key, and in `agentbox_git_tokens` for step 5. Steps 1 to 5 ran on
`e31a15e`; step 6 failed, and steps 6 to 9 ran on `6a30875`, its fix,
which changes only `roles/virtualbox_vm/tasks/snapshot.yml`, a file the
earlier steps do not run. Each install's roles and playbooks were
identical to its commit's. Every playbook passed `--syntax-check`.

| # | Step | Result |
|---|---|---|
| 1 | `provision` | passes: `changed=15`, cloud-init done |
| 2 | `sandbox`, first run | passes, image build included: `changed=30`, one more than `v0.1.0`, for the credential helper the Containerfile copies |
| 3 | `sandbox`, second run | `changed=0` |
| 4 | Smoke tests from the README, word for word, as `agent` | all pass, with the values of the runs before; `~/projects` and `~/.agentbox` left empty |
| 5 | Repository tokens, for a private GitHub repository kept for tests, with a fine-grained token from a `pass`-backed credential helper on the controller | `git_token` wrote each project's token, `changed=2`, files `0600` in directories `0700`, the token in neither log. **`session`, in `agentbox rt-s bash`**: clone, commit and push of a branch; the launcher named the token's host and lifetime; no token in `.git/config` or a remote URL, the only credential setting `credential.helper=agentbox` from `/etc/gitconfig`, no `~/.git-credentials`, no file in `/work` or the home directory with the token's prefix; the token gone after the session. With a new `session` token, the session started behind `ssh -tt`: the token mounted `ro`, a write refused, a second start in the project refused with the token kept; `kill -9` on the `ssh` client, and container and token were gone within a second. **`permanent`, with Claude** (`agentbox --auto rt-p -p …`, cloning into a subdirectory): clone, commit and push of a branch through Claude's sandbox; the token in neither the state directory, the transcript, `/work` nor the stream-json output. Finding 1 below. Both branches deleted with `git push --delete` from a session; `remove` left nothing; `~/projects`, `~/.agentbox` and `~/.agentbox-tokens` left empty |
| 6 | `snapshot` take `base` | **fails** on `e31a15e`: finding 2. On `6a30875`, with the VM started again by `provision` (`changed=1`): passes, `changed=5`, the poll waiting through seven retries, about 40 s, for the guest to stop; the state file next to the inventory, the collection holds none |
| 7 | take `pre-session`, restore `pre-session`, restore `base` | pass: `changed=3` each. `ssh` right after each connects. After `pre-session` only the marker written before it is there; after `base`, neither |
| 8 | `sandbox` afterwards | `changed=0` |
| 9 | `destroy --limit sandbox-vm -e destroy_confirm=yes` | passes in 8.3 s on the running VM with two snapshots, `base` and `pre-tests`: `changed=5`. No VM, no registered disk or DVD, no machine folder, no build artefacts; the base image cache stays. The state file then deleted by hand |

The [known unknowns](design.md#how-they-were-tested) ran between steps 8
and 9, on the same VM, from a snapshot `pre-tests`:

| Part | Result |
|---|---|
| The canary | `--check --diff`: only the launcher, one `--env` line; applied, `changed=1`; removed afterwards, `grep -c` `0`, and `sandbox` `changed=0` |
| E1 to E5 | as on 2026-10-31: the canary in a command's environment; `/proc/1/environ` and `/proc/2/environ` denied, only `/proc/self/environ` has it; the Read tool refuses `/proc`; every command line readable, the `-p` prompt included. New: `bwrap`'s command line also carries the credentials of Claude Code's own sandbox proxy on `localhost:3128`, which the commands go through anyway. The canary landed in two transcripts, where Claude quoted it |
| Error reporting's switch | the image's Claude Code (2.1.284) knows `DISABLE_ERROR_REPORTING` |
| Two sessions at once | both cloned and installed, exit codes 0; lowest `available` 4952 of 5931 MB, about 245 MB per container at the 10 s samples, no swap, no OOM kill. The first try found both clones already there, from a run interrupted at the controller that had reached the VM; they were deleted and the test repeated |
| The Squid log | reached: `api.anthropic.com`, `platform.claude.com`, `raw.githubusercontent.com`, `github.com`, `registry.npmjs.org`; denied on purpose: `downloads.claude.ai`; no telemetry or error-reporting host attempted |

### Upgrade from v0.1.0

A new VM from `v0.1.0` (`db0261d`): its `examples/` unchanged, the
collection installed at the tag; `provision` `changed=15`, `sandbox`
`changed=29`, then `changed=0`. Then the collection at `6a30875`:

| Step | Result |
|---|---|
| `sandbox --check --diff`, `sandbox_image_tag` still `0.1.0` | refused, as CHANGES.md says: `localhost/agentbox:0.1.0 exists but was built from a different recipe (no label, …). Bump sandbox_image_tag …`; "no label", since the label was renamed |
| the same with `0.2.0` | `changed=4`: the Containerfile with the credential helper, the helper, `Edit(//run/agentbox/**)` in the managed settings, the launcher; finding 3 |
| `sandbox`, applied | `changed=5`: the same four and the image build |
| `sandbox --check --diff` again, and a plain run | `changed=0` |
| The launcher | `agentbox:0.2.0`, uid 1000 `dev`, Claude Code 2.1.284, `credential.helper=agentbox`; the `0.1.0` image kept for going back |

This VM was kept.

### Findings

1. **Claude cannot write `.git/config` inside its sandbox.** `git push -u`
   pushed, then failed to record the upstream with `could not write config
   file .git/config: Device or resource busy`, and still printed "set up
   to track" and exited 0. Claude Code's sandbox mounts over the file, as
   it puts `/dev/null` stand-ins into `/work`
   ([Findings on the VM](design.md#findings-on-the-vm) 4): its behaviour,
   not the collection's. The README's [Repository tokens](../README.md#repository-tokens)
   now says to set a branch's upstream and other git configuration in
   `agentbox <project> bash`.
2. **`snapshot` take failed while the guest was stopping.** The poll for
   the guest to stop runs `VBoxManage showvminfo`, which exited 1 with
   `E_ACCESSDENIED` ("The object is not ready") while the VM was
   `stopping`; the play ended with the VM off and no snapshot. A race: the
   [third run](#third-run) passed the same step. And `stopping` counted as
   stopped. Fixed as `6a30875`: the poll goes on through the error, waits
   for `poweroff` or `aborted`, and an assert refuses the snapshot if the
   guest did not stop in time, since exhausted retries do not fail a task
   with `failed_when: false`. Checked against a stand-in command for the
   error followed by `poweroff`, `poweroff`, `aborted`, `running`, the
   error throughout and another error, then on the VM in steps 6 and 7.
3. **`--check --diff` does not show an image rebuild.** The build task is
   skipped in check mode, so a release that changes the recipe shows only
   the Containerfile's diff, not that the run will build; already so in
   `v0.1.0`. Not fixed: proposed, a task that reports `changed` in check
   mode when the tag is missing.

## The release test of v0.3.0

On 2026-11-03, before `v0.3.0` was tagged, on `59a7843`, with the
collection installed from a local clone with `git+file://…` and
`--force`; its roles and playbooks were identical to the commit's.
`ansible-lint` and `yamllint` passed on it, and every playbook passed
`--syntax-check`.

### The run on a VM of its own

The VM `sandbox-vm` was in use and stayed, so the run used a new VM
`rt-vm`, as [Adding a VM](virtualbox.md#adding-a-vm) describes: its own
host-only address (`.30`), MACs and key. `examples/` copied in afresh from
`59a7843` and checked with `diff -r`; then the inventory's host renamed,
the host_vars file renamed to `rt-vm.yml` and changed in the key paths,
the address, the MACs, `vm_memory_mb: 4096` and `agentbox_git_tokens` for
step 5. 4 GB instead of the default 6 GB, which the host could not spare
beside its other work: enough for one session, as the sizing guide says.

| # | Step | Result |
|---|---|---|
| 1 | `provision` | passes: `changed=15`, cloud-init done; the VM has 4096 MB and 4 CPUs, and the new step for an existing VM's memory and CPUs is skipped for a new one |
| 2 | `sandbox`, first run | passes, image build included, in under 3 minutes: `changed=30` |
| 3 | `sandbox`, second run | `changed=0` |
| 4 | Smoke tests from the README, word for word, as `agent` | all pass, with the values of the runs before; `~/projects` and `~/.agentbox` left empty |
| 5 | Repository tokens, for the private GitHub repository kept for tests, with a fine-grained token from a `pass`-backed credential helper on the controller | `git_token` wrote each project's token, `changed=2`, files `0600` in directories `0700`, the token in neither log. **`session`, in `agentbox rt-s bash`**: clone, commit and push of a branch; the launcher named the token's host and lifetime; the only credential setting `credential.helper agentbox` from `/etc/gitconfig`, no token in the remote URL, no `~/.git-credentials`, no file in `/work` or the home directory with a token prefix; the token gone after the session. With a new `session` token, the session started behind `ssh -tt`: the token mounted `ro`, a write refused, a second start in the project refused with the token kept; `kill -9` on the `ssh` client, and container and token were gone within 0.3 s. **`permanent`, with Claude** (`agentbox --auto rt-p -p …`, cloning into a subdirectory, after a login in `agentbox rt-p`): clone, commit and push of a branch through Claude's sandbox; the token in neither the state directory, the two transcripts, `/work` nor the output. Observation 1 below. Both branches deleted with `git push --delete` from a session; `remove` left no token, only the empty `tokens/session` directories on tmpfs; `~/projects`, `~/.agentbox` and `~/.agentbox-tokens` left empty |
| 6 | `snapshot` take `base` | passes: `changed=5` in 55 s, the poll waiting through seven retries for the guest to stop; the state file next to the inventory, the collection holds none |
| 7 | take `pre-session`, restore `pre-session`, restore `base` | pass: `changed=3` each. `ssh` right after each connects. After `pre-session` only the marker written before it is there; after `base`, neither |
| 8 | `sandbox` afterwards | `changed=0` |
| 9 | `destroy --limit rt-vm -e destroy_confirm=yes` | passes in 8.8 s on the running VM with two snapshots: `changed=5`. No VM, no registered disk or DVD, no machine folder, no build artefacts; the base image cache stays. The state file then deleted by hand |

The known unknowns did not run: Claude Code, the managed settings and the
launcher are unchanged since `v0.2.0`.

### Upgrade from v0.2.0

On the VM `sandbox-vm`, built from `v0.2.0` with Claude Code 2.1.317 in
the image (`sandbox_image_tag: "0.2.0-cc2.1.317"`) and a `base` snapshot,
powered off, with 6 GB. The collection at `59a7843`, and
`vm_memory_mb: 4096` set in its host_vars:

| Step | Result |
|---|---|
| `provision` | `changed=2`: `Apply vm_memory_mb and vm_cpus to the powered-off VM` changed, the warning skipped, the VM started; VirtualBox then reports `memory=4096`, `cpus=4` |
| `sandbox --check --diff` | `changed=0`: the release's role changes, `become` beside `become_user` and `changed_when`, change nothing on the VM, as CHANGES.md says |
| `sandbox` | `changed=0` |

This VM was kept.

### Observations

No bug was found. Two things worth knowing:

1. **Finding 1 of `v0.2.0` did not reproduce.** Claude ran `git push -u`
   in its sandbox, and the upstream landed in `.git/config`
   (`branch.rt-v030-permanent.remote` and `.merge`), with the same Claude
   Code 2.1.284 that failed with `Device or resource busy` in the
   [release test of v0.2.0](#findings). Why it differs is not known. The
   README's advice, to set up git configuration in
   `agentbox <project> bash`, stays: it works either way.
2. **The memory and CPU step was tested both ways:** in a stand-in for a
   running VM, which gives the warning and changes nothing, and for real
   on `sandbox-vm` in the upgrade test. Not tested on a VM that is
   `saved` or `paused`, which takes the warning path as well.

## Claude Code 2.1.323, before v0.4.0

On 2026-11-13 and 2026-11-14, on the VM `sandbox-vm` (4 GB, built from
`v0.2.0`, running the installed `v0.3.0`), with the working tree after
`2c9b308` instead of an installed collection: `ANSIBLE_COLLECTIONS_PATH`
pointed at a symlink to the clone. Not a release test: no new VM, no
steps 1 to 9. The version, the tag `0.4.0` and the links between two
scratch projects came as extra vars, so the inventory stayed unchanged; a
snapshot `pre-cc323` before. A login in each scratch project; the
interactive sessions were driven through `tmux` on the VM, installed for
the test.

| Test | Result |
|---|---|
| `sandbox --tags agentbox --check --diff` | the Containerfile, the broker's files, the managed settings, the launcher; `--check` does not show the build ([finding 3](#findings) of `v0.2.0`) |
| `sandbox --tags agentbox` | `changed=10`, the image `0.4.0` built beside the old ones, `claude --version` 2.1.323; second run `changed=0` |
| The linked-session table | every row passes; [docs/design.md, "What was tested"](design.md#what-was-tested-1) |
| [Known unknowns](design.md#known-unknowns) 4, mods Claude writes | a mod turned on without asking in `--auto` and in auto mode, and ran outside the inner sandbox; `allowManagedHooksOnly` stopped it in both. Led to Decision 20 |
| The managed settings with both keys, from the template | `--diff` shows exactly `allowManagedHooksOnly` and `defaultMode`; second run `changed=0` |
| The known-unknowns session, 1 to 3 | the same answers as on 2026-10-31; two sessions about 240 MB each, `available` not below 2965 MB; no Squid denial |

Also found: a plain session started in auto mode before Decision 21, and
the folder trust dialog defaults to *No, exit*; both are in the README
now. Afterwards `pre-cc323` was restored, which removed the scratch
projects, `tmux` and the image `0.4.0`.

## The release test of v0.4.0

On 2026-11-14 and 2026-11-15, before `v0.4.0` was tagged, on `ccdd460`,
with Claude Code 2.1.323 in the image. The collection was installed from a
local clone with `git+file://…` and `--force`, with `-p` into the working
directory, which `collections_path` in its `ansible.cfg` names, as
[Install](../README.md#install) allows: so the installed `v0.3.0` that
`sandbox-vm` runs stayed. Its roles and playbooks were identical to the
commit's. `ansible-lint` and `yamllint` passed on it, every playbook
passed `--syntax-check`, and so did `python3 dev/test-peer-broker.py`.

### Steps 1 to 9

On a new VM `rt-vm`, set up as for [v0.3.0](#the-run-on-a-vm-of-its-own):
`examples/` copied in afresh from `ccdd460` and checked with `diff -r`,
the host renamed, its own address (`.30`), MACs and key,
`vm_memory_mb: 4096`, and `agentbox_git_tokens` for step 5.

| # | Step | Result |
|---|---|---|
| 1 | `provision` | passes: `changed=15` in 2 min 39 s, cloud-init done; 4096 MB, 4 CPUs |
| 2 | `sandbox`, first run | passes, image build included, in 3 min 20 s: `changed=30` |
| 3 | `sandbox`, second run | `changed=0` |
| 4 | Smoke tests from the README, word for word, as `agent` | all pass, with the values of the runs before and Claude Code 2.1.323; `~/projects` and `~/.agentbox` left empty |
| 5 | Repository tokens, for the private GitHub repository kept for tests, with a fine-grained token from a `pass`-backed credential helper on the controller, named by `credential.passEntry` in `git_config` | `git_token` wrote each project's token, `changed=2`, files `0600` in directories `0700`, the token in neither log. **`session`, in `agentbox rt-s bash`**: clone, commit and push of a branch; the launcher named the token's host and lifetime; the only credential setting `credential.helper agentbox` from `/etc/gitconfig`, no token in the remote URL, no `~/.git-credentials`, no file in `/work` or the home directory with a token prefix; the token gone after the session. With a new `session` token, the session started behind `ssh -tt`: the token mounted `ro`, a write refused with `Read-only file system`, a second start in the project refused with the token kept; 0.3 s after `kill -9` on the `ssh` client, container and token were gone. **`permanent`, with Claude** (`agentbox --auto rt-p -p …`, cloning into a subdirectory, after a login in `agentbox rt-p`): clone, commit and push of a branch through Claude's sandbox; the token in neither the state directory, the two transcripts, `/work` nor the output. [Finding 1](#what-it-found). Both branches deleted with `git push --delete` from a session; `remove` left no token, only the empty `tokens/session` directory on tmpfs; `~/projects`, `~/.agentbox` and `~/.agentbox-tokens` left empty |
| 6 | `snapshot` take `base` | passes: `changed=5` in 52 s, the poll waiting through seven retries for the guest to stop; the state file next to the inventory, the collection holds none |
| 7 | take `pre-session`, restore `pre-session`, restore `base` | pass: `changed=3` each. `ssh` right after each connects. After `pre-session` only the marker written before it is there; after `base`, neither |
| 8 | `sandbox` afterwards | `changed=0` |
| 9 | `destroy --limit rt-vm -e destroy_confirm=yes` | passes in 8.4 s on the running VM with two snapshots: `changed=5`. No VM, no registered disk or DVD, no machine folder, no build artefacts; the base image cache stays. The state file then deleted by hand |

The Agent Intercom check below ran on `rt-vm` between steps 8 and 9.

### Agent Intercom, a short check

The release changes the peer broker and Claude Code's version, so the
table in [docs/design.md, "What was tested"](design.md#what-was-tested-1)
is due. It passed in full on 2026-11-13 with the same Claude Code and
settings, from the working tree with extra vars
([above](#claude-code-21323-before-v040)); here its rows ran again from
`ccdd460`, on `rt-vm`, with the links `alpha` and `beta` of the example
and `agentbox_peer_budget: 6` in the working directory's group_vars, a Pro
login in each, and both sessions started plainly, in manual mode.

| Question | Result |
|---|---|
| The play with links, then again | `changed=8`, then `changed=0`; the broker up with both projects |
| The dialog | Shown at each start; the launcher's line above it says the session is linked |
| Asked at its prompt to ask the other session something | Asked; the other woke, answered with `send` unprompted, and the answer arrived; a follow-up the same way, nobody typing |
| A prompt for `send` | None, on either side, in manual mode |
| `DISABLE_ERROR_REPORTING=1` | Kept; `DISABLE_TELEMETRY` absent; the managed settings in the session carry `allowManagedHooksOnly: true` and `defaultMode: "default"` |
| The budget | Stopped at 6, the journal's seventh `send` a `budget` event; both sessions told; the next `send` refused |
| A command in a linked session | `PermissionError: [Errno 1] Operation not permitted` at `socket(AF_UNIX)` |
| `--auto` in a linked project, on a terminal | Not linked: no socket, no `managed-mcp.json`, `DISABLE_TELEMETRY` set |
| A run without a terminal | Not linked, the same |
| The claude.ai connectors | Listed in `/mcp` beside `peer`; `mcp-proxy.anthropic.com` in the Squid log |
| The play without links | `changed=4`: unit, broker, policy and runtime directory gone, no peer line left in the launcher; `changed=0` after |
| Squid | Denied only the telemetry host and `downloads.claude.ai`, and `example.com` from the smoke tests |

The [known unknowns](design.md#how-they-were-tested) session did not run
again: it ran on 2026-11-14 with 2.1.323 and the settings `ccdd460`
commits, from the working tree.

### Upgrade from v0.3.0

On the VM `sandbox-vm`, built from `v0.2.0` and running the installed
`v0.3.0`, with 4 GB, its own pin `sandbox_image_tag: "0.2.0-cc2.1.317"`
and `agentbox_claude_code_version: "2.1.317"`, no links, running. The
collection at `ccdd460`, from the test's install:

| Step | Result |
|---|---|
| `sandbox --check --diff` | `changed=1`: the managed settings, with exactly `allowManagedHooksOnly` and `defaultMode` added, as CHANGES.md says. No image build, since the VM pins its own tag; the launcher unchanged without links (Decision 19) |
| `sandbox` | `changed=1` |
| `sandbox`, again | `changed=0` |

This VM was kept, now with the managed settings of `v0.4.0` and its own
image.

### What it found

No bug in the collection. One thing the README says that the run
contradicts, and two things worth knowing:

1. **Claude wrote `.git/config` again.** Claude ran `git push -u` in its
   sandbox, and the upstream landed in `.git/config`
   (`branch.rt-v040-permanent.remote` and `.merge`), with Claude Code
   2.1.323, as in the [release test of v0.3.0](#observations) with 2.1.284.
   The README's "Repository tokens" said then that `git push -u` records
   no upstream and that `git config` in the repository fails, from the
   [release test of v0.2.0](#findings). It was changed after this record,
   before the release, and no longer promises either.
2. **A credential helper that picks the token per repository needs
   `git_config`.** The first `git_token` run failed with the helper's own
   message, because the token's name was in the clone's `.git/config` on
   the controller, not in the inventory. The README says so; the run had
   checked the helper from inside a repository, which the README warns
   against. With `credential.passEntry` in `git_config` it passed.
3. **`--auto` passes its arguments to Claude.** `agentbox --auto <project>
   bash -c …` started Claude in bypass mode with them, not a shell; the
   `--auto` row above was read from outside, with `podman exec`.

## The release test of v0.5.0

On 2026-11-15, before `v0.5.0` was tagged, on the commit before the
release commit, "Sessions that outlive the connection: agentbox --tmux,
and agentbox-remote", with Claude Code 2.1.323 in the image.
**Shortened, by decision:** the full run of steps 1 to 9 on a new VM and
the known-unknowns session, which a launcher change calls for, did not
run. The host had too little free memory for a second VM beside
`sandbox-vm`, and both need logins. Only the upgrade test and the test of
the new feature ran, on `sandbox-vm`.

The collection was installed from the working tree with `-p` into a
scratch directory named by `ANSIBLE_COLLECTIONS_PATH`, so the installed
`v0.4.0` stayed; its roles and playbooks were identical to the commit's.
`ansible-lint` and `yamllint` passed, every playbook passed
`--syntax-check`, and so did `python3 dev/test-peer-broker.py`.

**Upgrade from `v0.4.0`**, on `sandbox-vm` with its own pin
`sandbox_image_tag: "0.4.0-cc2.1.323"`, two links, and two linked sessions
running throughout:

| Step | Result |
|---|---|
| `sandbox --check --diff` | `changed=2`: `tmux` installed and the launcher, as CHANGES.md says. No image build, no peer broker restart |
| `sandbox` | `changed=2`; both sessions kept running |
| `sandbox`, again | `changed=0` |

The test of `--tmux` then found that a closed tmux pane left the container
running; the launcher was changed to wait with `wait`, and moved its tmux
socket back to tmux's default. Each of the two launcher changes was
applied with `changed=1`, then `changed=0`.

**The feature and the launcher's plain path**, from the controller with
`examples/agentbox-remote`: every check listed under
[docs/design.md, "Sessions that outlive the connection"](design.md#sessions-that-outlive-the-connection)
passed, on the final commit. Not tested: a linked session under `--tmux`.

## The release test of v0.6.0

On 2026-11-15, before `v0.6.0` was tagged, on `sandbox-vm`, with Claude
Code 2.1.323 in the image. **Shortened, by decision**, as for `v0.5.0`: no
role changed, only the playbook `sandbox` (the stamp) and the new
playbook `update_check`, so the full run of steps 1 to 9 on a new VM and
the known-unknowns session did not run.

The collection was installed with `-p` into a scratch directory named by
`ANSIBLE_COLLECTIONS_PATH`, so the installed collection and
`~/.local/bin` stayed as they were: first from `2ba423f`, "update_check:
what a collection update needs on the VM and the controller", still
reporting 0.5.0; then from the working tree with the release's own
changes, `galaxy.yml` at 0.6.0 and the entry for 0.6.0 in
`meta/updates.yml`. Each time its roles, playbooks, `meta/` and
`examples/` were identical to the source. `ansible-lint` and `yamllint`
passed, and every playbook passed `--syntax-check`.

| Step | Result |
|---|---|
| `update_check`, before the first `sandbox` run of the new code | "No stamp on this VM"; `agentbox-remote` not installed in `~/.local/bin` |
| `sandbox --check --diff`, from `2ba423f` | `changed=2`: the directory `/etc/agent-sandbox` and the stamp, every role at 0.5.0. Nothing else |
| `sandbox`, twice | `changed=2`, then `changed=0`; the stamp `root:root 0644` |
| `update_check`, from the release's tree | the entry for 0.6.0: run `sandbox`, the new variable `agent_sandbox_bin_dir` not set; "To apply" names `sandbox --check --diff`, then `sandbox` |
| `sandbox --check --diff` | `changed=1`: the stamp, 0.5.0 to 0.6.0, for all three roles |
| `sandbox`, twice | `changed=1`, then `changed=0` |
| `update_check` | "Up to date: nothing to run." |
| `update_check -e install_scripts=true`, with `agent_sandbox_bin_dir` a scratch directory, twice | installs `agentbox-remote`, identical to the collection's, and warns that the directory is not on `PATH`; the second run reports it current, `changed=0` |
| `update_check` and `sandbox --check --tags podman`, from `2ba423f` again | both warn that 0.5.0 is older than what last applied the roles; `sandbox` goes on |

The variables `examples/` sets were all set in the deployment's inventory,
so that line of the report did not show; it was tested on a stand-in host
with a local connection, as were a role left out by `--tags` and a VM that
is off.

## The release test of v0.7.0

On 2026-11-16, and the upgrade test on 2026-11-26, before `v0.7.0` was
tagged, on `e7006a0`, "The editor: VS Code Server in a container beside
each session (#15)", with Claude Code 2.1.323 in the image and VS Code
1.146.0 (`6904719`) in the editor's. The full run again, for the first
time since `v0.4.0`: the release changes the launcher and adds the editor.
`ansible-lint` and `yamllint` passed on it, and every playbook passed
`--syntax-check`. The collection was installed from a local clone with
`git+file://…` and `--force`, with `-p` into the working directory, which
`collections_path` in its `ansible.cfg` names; its roles, playbooks,
`meta/` and `examples/` were identical to the commit's.

### Steps 1 to 9 on rt-vm

A new VM `rt-vm`, set up as for [v0.3.0](#the-run-on-a-vm-of-its-own):
`examples/` copied in afresh from `e7006a0` and checked with `diff -r`,
the host renamed, its own address (`.30`), MACs and key, and
`agentbox_git_tokens` for step 5; the default size, 6 GB, for the first
time since `v0.2.0`, since `sandbox-vm` was off; and
`agentbox_editor_accept_server_license: true` in the group_vars, which the
editor checks need.

| # | Step | Result |
|---|---|---|
| 1 | `provision` | passes: `changed=15` in 2 min 37 s, cloud-init done; 6144 MB, 4 CPUs |
| 2 | `sandbox`, first run | passes, both images built, in 5 min 51 s: `changed=43`, thirteen more than `v0.4.0`: the editor's group and its member, the tmpfiles entry, the socket directory, the build directory, the download, its Containerfile, its image, the machine settings, the state directory, `tmux`, and the stamp's directory and stamp. The editor image's check: "VS Code Server 1.146.0 (6904719), uid 1000, no extensions, read-only" |
| 3 | `sandbox`, second run | `changed=0` |
| 4 | Smoke tests from the README, word for word, as `agent` | all pass, with the values of the runs before and Claude Code 2.1.323; `~/projects` and `~/.agentbox` left empty. The launcher line runs without a terminal and starts no editor |
| 5 | Repository tokens, for the private GitHub repository kept for tests, with a fine-grained token from a `pass`-backed credential helper on the controller, named by `credential.passEntry` in `git_config` | `git_token` wrote each project's token, `changed=2`, the token in neither log. **`session`, in `agentbox rt-s bash`**: clone, commit and push of a branch; the launcher named the token's host and lifetime; the only credential setting `credential.helper agentbox` from `/etc/gitconfig`, no token in the remote URL, no `~/.git-credentials`; the token gone after the session. With a new `session` token, the session started behind `ssh -tt` with `--no-editor`: the token on a read-only tmpfs, a write refused with `Read-only file system`, no file in `/work` or the home directory with a token prefix, a second start in the project refused with the token kept; after `kill -9` on the `ssh` client, container and token were gone at the first check, under 0.6 s with the round trip. **`permanent`, with Claude** (`agentbox --auto rt-p -p …`, cloning into a subdirectory, after a login in `agentbox rt-p`): clone, commit and `git push -u` of a branch through Claude's sandbox; the token's value in neither the state directory, the transcripts, `/work` nor the output; the upstream in `.git/config`, as in the release tests of `v0.3.0` and `v0.4.0`. Both branches deleted with `git push --delete` from a session; `remove` gave `changed=0` for `rt-s`, whose token the session had used up, and `changed=1` for `rt-p`; `~/projects`, `~/.agentbox` and `~/.agentbox-tokens` left empty |
| 6 | `snapshot` take `base` | passes: `changed=5` in 1 min 16 s; the state file next to the inventory, the collection holds none |
| 7 | take `pre-session`, restore `pre-session`, restore `base` | pass: `changed=3` each. `ssh` right after each connects. After `pre-session` only the marker written before it is there; after `base`, neither |
| 8 | `sandbox` afterwards | `changed=0` |
| 9 | `destroy --limit rt-vm -e destroy_confirm=yes` | passes in 8.8 s on the running VM with two snapshots, `base` and `pre-tests`: `changed=5`. No VM, no registered disk or DVD, no machine folder, no build artefacts; the base image cache stays. The state file then deleted by hand |

The checks below ran on `rt-vm` between steps 8 and 9, from a snapshot
`pre-tests`.

### Sessions under tmux, from the controller

With `examples/agentbox-remote` and `AGENTBOX_HOST=rt-vm`, through an
`ssh` that read a scratch `ssh_config` naming the VM's address and key.
`git_token` could not run then, the controller's GPG key being locked, so
the project's `session` token was a dummy file written into the
launcher's token directory: what the launcher does with it is the same.

| Check | Result |
|---|---|
| `--tmux rt-s bash` | starts; the launcher's lines for the editor and the token in the pane; `--list` shows `rt-s  running editor tmux` |
| A detach, then three times a reattach ended by `kill -9` on the `ssh` client | the session, its editor and an open editor tunnel held each time |
| `loginctl terminate-user` for the account Ansible uses, every login of it | the session held; the tmux server and both containers' `conmon` in `user@1001.service`; a reattach afterwards worked |
| The first disconnect of a new session, the case left unexplained in the editor's tests ([docs/design.md, "What is open"](design.md#what-is-open-1)) | eight new sessions, five with an editor and three with `--no-editor`, `kill -9` on the `ssh` client that started each, 1 to 10 s after the start: all eight kept running. Not reproduced |
| Refusals while the tmux session runs | `--tmux` with a command, `--tmux --auto`, `--tmux --no-editor` and a plain start: each refused, the running editor untouched |
| Refusals the other way round | a plain session running, then `--tmux`: refused, "outside tmux". `--tmux` without a terminal: refused, through `agentbox-remote` and on the VM |
| `tmux kill-session` | the container stopped, then the editor, its socket directory and token, and the session token: all gone after 10 s, `podman stop`'s timeout, since bash in the pane ignores `SIGTERM` |
| `my.app` | its own tmux session, `agentbox-my+app` |
| `--tmux --auto probe -p '…'` with `'`, `"`, double spaces, `$HOME`, backticks and `\` | reached Claude unchanged: the user message in the transcript is the task byte for byte, JSON's escaping aside |

### The editor

With `agentbox_editor_accept_server_license: true`. The browser part was
done by a person, in Chromium on the controller.

| Check | Result |
|---|---|
| The first `sandbox` run, then the second | the editor image built and its check passed; `changed=0` (steps 2 and 3) |
| When a session gets one | a plain session on a terminal: the editor's line; `--no-editor`: none; a `-p` run and an `--auto -p` run on a terminal: none; `--editor` without a terminal: one, gone with the session |
| `agentbox-remote --open-editor rt-s` | prints the URL with a 48-digit token and holds the tunnel. With `curl`: no token or a wrong one 403; the token 302 with a cookie, then 200, the workbench opening `/work`. In the browser, two projects each opened `/work` with their files |
| "Install from VSIX" in the browser, with a do-nothing extension built locally | refused: "This extension cannot be installed because it is not in the allowed list"; the extensions directory still holds only the empty `extensions.json`. The upload did not stay in `data/CachedExtensionVSIXs/`, unlike in the editor's tests |
| The session's end (`exit` in the pane), `tmux kill-session`, `SIGTERM` to the launcher | each stopped the editor and removed its socket directory and token |
| Two projects with editors, each with a workbench open in a browser tab | 392 MB and 68 processes for the one with the refused upload, 343 MB and 68 for the other; `available` from 5260 to 4636 MB of 5931 when the two workbenches loaded, no swap. Without a browser connected, about 64 MB and 13 processes each |
| `sandbox` with the licence set back to `false`, then again | `changed=3`: the editor's files, its group, the launcher; then `changed=0`. The image stays. `--editor` refused, "the editor is not installed"; `--no-editor` works. [Finding 1](#findings-and-observations) |

The licence was set back to `true` and `pre-tests` restored before the
next part.

### The known-unknowns session

The [known unknowns](design.md#how-they-were-tested), from the plan
word for word, with the editor installed, the canary in the launcher and
a Pro login in `probe` and `probe2`.

| Part | Result |
|---|---|
| The canary | `--check --diff`: only the launcher, one `--env` line, `changed=1`; applied, `changed=1`; removed afterwards, `changed=1`, `grep -c` `0`, and `sandbox` `changed=0` |
| E1 to E5 | as on 2026-10-31 and 2026-11-14: the canary in a command's environment; `/proc/1/environ` and `/proc/2/environ` denied, only `/proc/self/environ` has it; the Read tool refuses `/proc`; every command line readable, the `-p` prompt included, and `bwrap`'s still carries the credentials of Claude Code's own proxy on `localhost:3128`. The canary landed in two transcripts. New: `grep` in the inner sandbox reports as `ugrep` |
| Error reporting's switch | 2.1.323 knows `DISABLE_ERROR_REPORTING` |
| Two sessions at once | both cloned and installed, exit codes 0; lowest `available` 4895 of 5931 MB, peaks about 263 and 254 MB, no swap, no OOM kill |
| A mod Claude writes | in `--auto`: not among the plugins of the second turn, no file written. In auto mode, three Shift+Tabs from manual mode in a plain session driven through tmux: Claude wrote the mod; it did not load, no file written |
| The Squid log | reached: `api.anthropic.com`, `mcp-proxy.anthropic.com`, `platform.claude.com`, `github.com`, `raw.githubusercontent.com`, `registry.npmjs.org`; denied: only `downloads.claude.ai`; no telemetry or error-reporting host attempted |

### Upgrade from v0.6.0

On 2026-11-26, on `sandbox-vm`, every command typed by a person. The VM
ran `e7006a0` already, deployed from a working tree with the stamp at
0.6.0, so it was first taken back: a snapshot `pre-v070` of that state
(`changed=4`), then `restore` of `base`, a VM from `v0.2.0` (`changed=3`).
`base` came back with 6144 MB, the memory it had when it was taken; after
a clean shutdown `provision` applied the 4096 MB of its host_vars
(`changed=4`). Its two links and `sandbox_image_tag: "0.4.0-cc2.1.323"`
stayed as they were.

| Step | Result |
|---|---|
| `update_check`, the installed `v0.6.0` | "No stamp on this VM", "Run sandbox once"; no release listed, since without a stamp there is no starting point; `agentbox-remote` on the controller current |
| `sandbox`, the installed `v0.6.0` | `changed=13`: the image `0.4.0-cc2.1.323` built, the peer broker for the two links, the managed settings, `tmux`, the launcher, the stamp; then `changed=0`. Now a VM of `v0.6.0` |
| `update_check`, the release's tree | the entry for 0.7.0: run `sandbox --tags agentbox`, the nine new variables, `agentbox_editor_accept_server_license` set in the inventory and the others not, `agentbox-remote` changed; no image line; "To apply: snapshot the VM, then run sandbox --check --diff, then sandbox". On the controller `agentbox-remote` differs |
| `sandbox --check --diff` | `changed=8`, all in `agentbox`, as CHANGES.md says: the editor's group, tmpfiles entry, build directory, Containerfile, machine settings and state directory, the launcher, and the stamp from 0.6.0 to 0.7.0. The group member, the socket directory and the download skipped in check mode, since their group or directory is not there yet; the editor image build not shown ([finding 3](#findings) of `v0.2.0`). The session image not rebuilt: its recipe hash unchanged by the move to `tasks/image.yml` |
| `sandbox` | `changed=12`: the eight, and the four check mode skipped; the editor image's check passed, and the session image "matches the recipe" |
| `sandbox`, again | `changed=0` |
| `update_check` | "Up to date: nothing to run."; `agentbox-remote` on the controller still differs, until `install_scripts=true` |

"The release's tree" was the working tree after `e7006a0` with the entry
for 0.7.0 in `meta/updates.yml` and, in the installed copy only,
`galaxy.yml` at 0.7.0, installed with `-p` into a scratch directory named
by `ANSIBLE_COLLECTIONS_PATH`; its roles, playbooks, `meta/` and
`examples/` were identical to that tree's. The VM was kept, now at 0.7.0.

### Findings and observations

One finding, in the docs; nothing in the code.

1. **The editor with the licence set back to `false` kept its state
   directory.** `sandbox` removed the editor's files and group, and left
   `~agent/.agentbox-editor`, the editors' settings and state, as it
   leaves Claude Code's in `~agent/.agentbox`. CHANGES.md said the role
   then removes everything but the image, and the defaults comment much
   the same. The role's behaviour is the one wanted; the wording was
   corrected, and the README's "The editor" now says what such a run
   removes and what stays.

Worth knowing:

1. **The host's disk.** After step 3 the home partition of the host had
   1.7 GB left, with `rt-vm`'s disk at 9 GB and growing; the run waited
   until space was freed. The VM's dynamic disk never gives freed blocks
   back: on `sandbox-vm` the differencing image below `pre-v070` was
   16 GB, with 7.3 GB in use in the guest. Issue #16.
2. **A `restore` brings back the VM's settings**, memory and CPUs among
   them: `base` came back with 6 GB. The README and
   [docs/virtualbox.md](virtualbox.md#behaviour-notes) say so now, and
   that `restore` works on a running VM.
3. **`tmux kill-session` takes up to 10 s** with a shell in the pane,
   which ignores `SIGTERM`, until `podman stop` kills it; everything is
   cleaned up then.
4. **The upload refused by "Install from VSIX" did not stay** in
   `data/CachedExtensionVSIXs/`, where the editor's tests found it; the
   launcher's emptying it at start is the fallback.
5. **`sudo -iu agent` parses a command again:** a test command typed
   through it lost a `$i` to the login shell, as the README warns under
   "From the controller". Not the collection's; the tests went on from
   script files.
6. Also from the run, in the docs: "Updating the collection" runs what
   `update_check`'s "To apply" names, no longer `provision` every time,
   and ends with `update_check` again; issue #17 for a playbook that
   stops the VM.

## Not covered yet

- Heavier work in two concurrent sessions, and whether Claude Code
  withholds `ANTHROPIC_API_KEY` from its commands by name; see the
  README's [Open questions](../README.md#open-questions).
- Repository tokens: a push to a protected branch, which tests the remote,
  not the collection; `SIGINT` to the launcher on the VM in a release
  test, tested only outside one
  ([docs/design.md, "Sessions that outlive the connection"](design.md#sessions-that-outlive-the-connection)),
  while `SIGTERM` was tested in the
  [release test of v0.7.0](#the-editor); a `session` token from
  `git_token` under `--tmux`: that release test used a file put in its
  place;
  a self-hosted GitLab in a
  release test, tested only by hand
  ([docs/design.md, "What was tested"](design.md#what-was-tested)).
- A linked session under `--tmux`.
- The editor under load: two projects with language servers and builds;
  whether every built-in extension activates under
  `extensions.allowed: {"*": false}`; why one `--tmux` disconnect left
  nothing behind in the editor's tests, which twelve disconnects in the
  [release test of v0.7.0](#sessions-under-tmux-from-the-controller) did
  not reproduce ([docs/design.md, "What is open"](design.md#what-is-open-1));
  a browser other than Chromium.
- `update_check`'s line on the variables `examples/` sets, on a real
  inventory: every inventory tested so far set them all. A VM without a
  stamp and an upgrade with a role change were tested in the
  [release test of v0.7.0](#upgrade-from-v060).
- Linked sessions: a broker restart with sessions open, and logins other
  than Pro, which probably need `channelsEnabled: true`
  ([docs/design.md, "What is open"](design.md#what-is-open)).
- Whether a mod Claude writes asks first in manual mode: with
  `allowManagedHooksOnly` it does not load in any mode, and manual mode
  was not tried without it.
- `--check --diff` showing an image rebuild: finding 3 of the
  [release test of v0.2.0](#findings), not fixed.
- Why Claude could write `.git/config` in the release tests of `v0.3.0`
  and `v0.4.0` and not in that of `v0.2.0`: [observation 1](#observations)
  and [finding 1](#what-it-found) of `v0.4.0`.
