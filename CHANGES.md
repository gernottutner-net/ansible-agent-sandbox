# Changes

All notable changes to this repository are recorded here. Newest first at every
level.

## [Unreleased]

### 2026-10-31

#### Added

- README: new section "Check the sandbox", listed in the table of contents: the smoke tests to run once as `agent` after the first `sandbox` run and before the baseline snapshot. They check that the memory limit binds, an allowlisted host works through the proxy, a host not on the list gets Squid's 403, a direct connection past the proxy is refused, no resolver answers, and the launcher runs as uid 1000 with the policy's limits and the pinned Claude Code. The proxy address is read from `$https_proxy`, which Podman's `containers.conf` hands to every container. The step to take the baseline moved there from "Create the VM and the sandbox", and `docs/virtualbox.md` says to take it after the smoke tests.

#### Changed

- `snapshot`: `take` and `restore` return only once a VM they restarted answers over SSH again. Before, the playbook ended while the guest was still booting, and the next `ssh` was refused. The role records which VMs it started (`_snapshot_started_vm`), and a second play in the playbook runs `wait_for_connection` for those alone, within `vm_boot_timeout`; a VM that was off, and the actions `list` and `delete`, are not waited for. The README and `docs/virtualbox.md` say so.

- `virtualbox_vm`: the snapshot state file is written to `snapshot_state_dir`, next to the inventory, as documented. `tasks/snapshot.yml` still built its path from `playbook_dir`, so with the installed collection it landed inside the collection, under `playbooks/state/`, and a reinstall would lose the recorded baseline.
- `examples/group_vars/agent_sandbox.yml`: `production.cloudfront.docker.com` added to `egress_allowlist`. Docker Hub now serves image blobs from there, and without it the first image build fails: Squid answers 403 on the pull of `debian:trixie-slim`.

### 2026-10-30

#### Added

- The collection `tutner.agent_sandbox`, for VirtualBox only: the role `virtualbox_vm` and the playbooks `provision`, `wait`, `snapshot` and `destroy`, which create the Debian 13 VM from a checksum-verified cloud image with a cloud-init seed, snapshot it with one rolling slot plus a baseline, and tear it down; the roles `podman`, `egress_proxy` and `agentbox` and the playbook `sandbox`, which turn it into the sandbox. All taken from a private infrastructure repository where they run on a VirtualBox VM. Also `galaxy.yml`, `meta/runtime.yml` (ansible-core 2.17 or newer), an example inventory, host_vars, policy and `ansible.cfg` under `examples/`, a README that says up front it is for VirtualBox, `docs/virtualbox.md`, and the MIT licence.

#### Decisions

- gVisor is not part of the core: rootless `runsc` starts only with `--ignore-cgroups`, and then no limit binds. The launcher has no `--runtime=runsc` switch; gVisor is to come back as an experimental extension.
- VirtualBox is the only supported platform. The collection creates the VM it configures, and the docs assume VirtualBox throughout.
- No switch to turn the egress proxy off: the core promises default-deny egress.
- The generated snapshot state (`state/<host>-snapshot.yml`) goes next to the user's inventory, not into the installed collection (`snapshot_state_dir`).
