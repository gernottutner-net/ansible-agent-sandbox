# Changes

All notable changes to this repository are recorded here. Newest first at every
level.

## [Unreleased]

### 2026-10-30

#### Added

- The collection `tutner.agent_sandbox`, for VirtualBox only: the role `virtualbox_vm` and the playbooks `provision`, `wait`, `snapshot` and `destroy`, which create the Debian 13 VM from a checksum-verified cloud image with a cloud-init seed, snapshot it with one rolling slot plus a baseline, and tear it down; the roles `podman`, `egress_proxy` and `agentbox` and the playbook `sandbox`, which turn it into the sandbox. All taken from a private infrastructure repository where they run on a VirtualBox VM. Also `galaxy.yml`, `meta/runtime.yml` (ansible-core 2.17 or newer), an example inventory, host_vars, policy and `ansible.cfg` under `examples/`, a README that says up front it is for VirtualBox, `docs/virtualbox.md`, and the MIT licence.

#### Decisions

- gVisor is not part of the core: rootless `runsc` starts only with `--ignore-cgroups`, and then no limit binds. The launcher has no `--runtime=runsc` switch; gVisor is to come back as an experimental extension.
- VirtualBox is the only supported platform. The collection creates the VM it configures, and the docs assume VirtualBox throughout.
- No switch to turn the egress proxy off: the core promises default-deny egress.
- The generated snapshot state (`state/<host>-snapshot.yml`) goes next to the user's inventory, not into the installed collection (`snapshot_state_dir`).
