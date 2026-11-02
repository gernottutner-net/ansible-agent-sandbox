# Release tests

What is tested before a release, what the runs before `v0.1.0` covered
and found, and the first install of the release from GitHub. The [README](../README.md) says how to use the collection,
[docs/virtualbox.md](virtualbox.md) covers the VM, and
[docs/design.md](design.md) why the sandbox is built the way it is.

The runs ran on an Ubuntu 22.04 host with VirtualBox 7.0, against a Debian
13 guest, with Claude Code 2.1.284 in the image. Commits named here, such
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

### The steps

| # | Step | Passes when |
|---|---|---|
| 1 | `provision` | cloud-init is done; the play reports no failure |
| 2 | `sandbox`, first run | the image builds; the roles' own checks pass |
| 3 | `sandbox`, second run | `changed=0` |
| 4 | [Check the sandbox](../README.md#check-the-sandbox), as `agent` | every test gives the result its comment expects; `~/projects` and `~/.agentbox` are left empty |
| 5 | `snapshot` take `base` | the state file is next to the inventory, and the installed collection holds none |
| 6 | take `pre-session`, then restore `pre-session`, then restore `base`, with a marker file written before and one after `pre-session` | `ssh` right after each connects, with no `wait` between; after `pre-session` only the earlier marker is there, after `base` neither |
| 7 | `sandbox` afterwards | `changed=0` |
| 8 | `destroy --limit sandbox-vm -e destroy_confirm=yes`, on the running VM with its two snapshots | no VM, no registered disk or DVD, no machine folder, no build artefacts; the base image cache stays |

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

## Not covered yet

- Heavier work in two concurrent sessions, and whether Claude Code
  withholds `ANTHROPIC_API_KEY` from its commands by name; see the
  README's [Open questions](../README.md#open-questions).
- The upgrade test from one release of the collection to the next: there
  is no earlier release.
