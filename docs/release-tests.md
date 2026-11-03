# Release tests

What is tested before a release, what the runs before `v0.1.0` covered
and found, the first install of that release from GitHub, and the release
tests of `v0.2.0` and `v0.3.0`. The [README](../README.md) says how to use the collection,
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

Every playbook passes `--syntax-check` first. A release that changes a
role an existing install runs also gets the
[upgrade test](#upgrade-of-an-existing-install): `sandbox --check --diff`
on a VM built from the previous release, which should show exactly the
changes the release's CHANGES.md lists, and `changed=0` once applied.

A release that changes Claude Code's version, the managed settings or the
launcher also repeats the [known unknowns](design.md#how-they-were-tested)
session: its answers hold for the version they were tested on.

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

## Not covered yet

- Heavier work in two concurrent sessions, and whether Claude Code
  withholds `ANTHROPIC_API_KEY` from its commands by name; see the
  README's [Open questions](../README.md#open-questions).
- Repository tokens: a push to a protected branch, which tests the remote,
  not the collection; `SIGINT` and `SIGTERM` to the launcher on the VM,
  tested only against a stand-in `podman`; a self-hosted GitLab in a
  release test, tested only by hand
  ([docs/design.md, "What was tested"](design.md#what-was-tested)).
- `--check --diff` showing an image rebuild: finding 3 of the
  [release test of v0.2.0](#findings), not fixed.
- Why Claude could write `.git/config` in the release test of `v0.3.0`
  and not in that of `v0.2.0`: [observation 1](#observations).
