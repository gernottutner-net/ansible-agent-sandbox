# The VirtualBox VM

How the collection creates, snapshots and destroys the sandbox VM, with the
`virtualbox_vm` role and the playbooks `provision`, `wait`, `snapshot` and
`destroy`. All of them run on the VirtualBox host itself; the sandbox roles
then configure the guest over SSH.

---

## Contents

- [The VirtualBox host](#the-virtualbox-host)
- [Provisioning](#provisioning)
- [Waiting for the guest](#waiting-for-the-guest)
- [Adding a VM](#adding-a-vm)
- [Snapshots](#snapshots)
  - [Retention: one rolling snapshot plus the baseline](#retention-one-rolling-snapshot-plus-the-baseline)
  - [No saved RAM state](#no-saved-ram-state)
  - [Re-baselining](#re-baselining)
  - [Behaviour notes](#behaviour-notes)
- [Destroying a VM](#destroying-a-vm)
- [Why two NICs](#why-two-nics)
- [VirtualBox 7.0 specifics](#virtualbox-70-specifics)
- [KVM conflict](#kvm-conflict)
- [Troubleshooting](#troubleshooting)

---

## The VirtualBox host

Developed and tested on an Ubuntu 22.04 host with VirtualBox 7.0.26. Needed
there, and checked by the provision playbook before it touches anything:

- VirtualBox 7.0, with the `vboxdrv` module loaded. The collection never
  installs or upgrades VirtualBox.
- `qemu-img` and `cloud-localds`:

  ```bash
  sudo apt install qemu-utils cloud-image-utils
  ```

- A host-only interface, `vboxnet0` by default (`vm_hostonly_interface`),
  usually at `192.168.56.1/24` with a DHCP pool `.101–.254`:

  ```bash
  VBoxManage hostonlyif create
  VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1 --netmask 255.255.255.0
  ```

  Static VM addresses must stay below `.101`, or they collide with the DHCP
  pool; the playbook warns if one does not.
- KVM must not hold the virtualization extensions, see
  [KVM conflict](#kvm-conflict).
- An SSH key pair for the VM. Its public half is injected by cloud-init;
  passphrase-less is fine when the key opens only this VM.

## Provisioning

```bash
ansible-playbook tutner.agent_sandbox.provision --limit sandbox-vm
```

Per run, on the VirtualBox host:

- **Preflight:** every targeted VM names its MACs, its host-only address and
  its key; `VBoxManage`, `qemu-img` and `cloud-localds` exist; `vboxdrv` is
  loaded; the host-only interface exists; MACs are unique; KVM is not
  holding virtualization.
- **Image:** `debian-13-generic-amd64.qcow2` is downloaded once into
  `~/.cache/ansible-vbox-images/`, verified against Debian's published
  `SHA512SUMS`. It is shared by every VM and treated as immutable.
- **Per VM:** the image is copied, grown with `qemu-img resize` while it is
  still qcow2, and converted to a `monolithicSparse` VMDK. `user-data`,
  `meta-data` and `network-config` are rendered from the host's variables
  into a cloud-init seed ISO. Then `createvm`, `modifyvm`, `storagectl`,
  `storageattach` and `startvm --type headless`.
- **Idempotent:** an existing VM is detected with `showvminfo` and its
  creation skipped. An existing but powered-off VM is started.
- **Atomic:** the slow, fallible work (download, resize, convert, seed ISO)
  happens in a scratch directory before `createvm` runs, and the
  registration that follows is wrapped in `block`/`rescue`. A failure
  partway unregisters the VM and removes its artefacts, rather than leaving
  a registered VM without a disk that every later run would skip as
  "already exists". If you ever find one, delete it and re-run:

  ```bash
  VBoxManage unregistervm <name> --delete-all
  ```

The guest gets an `ansible` account with passwordless sudo and your key,
root locked, password logins off, and the root filesystem grown to
`vm_disk_size`. Everything else is the sandbox playbook's job.

## Waiting for the guest

`tutner.agent_sandbox.wait` runs at the end of `provision`, and on its own:

1. TCP/22 accepts connections: the guest booted and claimed its static
   address.
2. `cloud-init status --wait`, then a marker file: the `ansible` user, its
   sudo rule and its key exist.

SSH answering does **not** mean cloud-init has finished. The sandbox
playbook run in that window fails with permission errors.

`snapshot` waits too, with only the first of the two: after `take` or
`restore` has restarted a VM, it returns once Ansible can reach the guest
over SSH. A restored guest has been seeded already.

## Adding a VM

Add it to `agent_sandbox` in `inventory.yml`, and give it a host_vars file
like `examples/host_vars/sandbox-vm.yml` with its own `vm_hostonly_ip`, MACs
(12 hex digits, no separators, unique across VMs) and key. Anything left out
falls back to `roles/virtualbox_vm/defaults/main.yml`: 6 GB RAM, 4 CPUs, a
40 GB disk. Then:

```bash
ansible-playbook tutner.agent_sandbox.provision --limit <name>
ansible-playbook tutner.agent_sandbox.sandbox --limit <name>
```

## Snapshots

A snapshot freezes the VM's disk at a moment; restoring throws away
everything since. It is a whole-machine undo, not a backup: it lives on the
same disk as the VM.

For the sandbox, it is the cheap way back after a session you do not trust:

```bash
# Before the session
ansible-playbook tutner.agent_sandbox.snapshot --limit sandbox-vm \
  -e snapshot_action=take -e snapshot_name=pre-session

# After it, back to the state before
ansible-playbook tutner.agent_sandbox.snapshot --limit sandbox-vm \
  -e snapshot_action=restore -e snapshot_name=pre-session
```

Actions: `list` (the default), `take`, `restore`, `delete`,
`restorecurrent`.

### Retention: one rolling snapshot plus the baseline

`take` does not accumulate. The defaults:

```yaml
snapshot_prune: true
snapshot_keep: 1
snapshot_pinned: []          # extra names to keep; normally empty
snapshot_pin_root: true
```

After every `take`, the chain is pruned to the newest snapshot plus the
**baseline**, the root of the snapshot tree. Pruning runs after the new
snapshot exists, so there is never a moment without a restore point. The
first snapshot you take is the baseline; take it right after the sandbox
playbook has run on a fresh VM and the
[smoke tests](../README.md#check-the-sandbox) have passed.

The baseline is protected twice:

- by **position** (`snapshot_pin_root`): whatever is the root, whatever it
  is called;
- by **name**: its name is recorded in a generated file,
  `state/<host>-snapshot.yml` next to your inventory
  (`snapshot_state_dir`), loaded at the start of every run and rewritten at
  the end. It changes only on a re-baseline, so it can be kept in Git, and
  it regenerates itself if deleted.

Deleting a snapshot is a **disk merge**, not a metadata edit: VirtualBox
folds the differencing image into its neighbour. Don't interrupt it.

### No saved RAM state

A snapshot of a **running** VM writes a `.sav` with the guest's whole
working set: 1.3 GB for a 6 GB guest, against 163 MB for the disk delta
beside it. For a rollback point that is pure overhead. So
`snapshot_poweroff: true` shuts the guest down cleanly (`acpipowerbutton`)
first, takes the snapshot of the stopped VM, and restarts it if it had been
running, waiting until the guest answers over SSH. `snapshot_poweroff:
false` keeps the RAM state and uses `--live`.

### Re-baselining

The rolling snapshot is a delta from the baseline and only grows. Now and
then, collapse the chain to today's known-good state:

```bash
# 1. Take the NEW baseline first. The old one survives, still the root.
ansible-playbook tutner.agent_sandbox.snapshot --limit sandbox-vm \
  -e snapshot_action=take -e snapshot_name=base-2026-11

# 2. Then drop the old baseline. Its image merges into the chain.
ansible-playbook tutner.agent_sandbox.snapshot --limit sandbox-vm \
  -e snapshot_action=delete -e snapshot_name=<old baseline>
```

Take before delete: delete first, and the rolling snapshot becomes the root
and un-prunable.

A description with spaces needs the JSON form of `-e`, because
`-e key="two words"` passes only `two`:

```bash
-e '{"snapshot_description": "baseline after the upgrade to Claude Code 2.x"}'
```

For the original pristine state, don't re-baseline: `destroy`, then
`provision` and `sandbox`, rebuild it in minutes.

### Behaviour notes

- `take` without `snapshot_name` generates `auto-YYYYmmdd-HHMMSS`.
- `restore` and `delete` need an explicit `snapshot_name`.
- `restore` powers a running VM off first and restarts it afterwards.
- Both `take` and `restore` return only once a VM they restarted answers
  over SSH again, within `vm_boot_timeout` (300 s by default). A VM that
  was off stays off and is not waited for.
- After a restore, Ansible's fact cache may still describe the newer state.
  If anything looks inconsistent, clear it (`.ansible_facts` or whatever
  your `ansible.cfg` names).

## Destroying a VM

```bash
ansible-playbook tutner.agent_sandbox.destroy --limit sandbox-vm
```

Powers the VM off, then `unregistervm --delete` removes it with all its
disks and snapshots, `closemedium` deletes the seed ISO, and the machine
folder and the build artefacts go last. It asks before each VM (skip with
`-e destroy_confirm=yes`) and refuses to run on more than one VM without
`-e destroy_all=yes`. The cached base image is kept, and so is the
snapshot state file next to your inventory: delete
`state/<host>-snapshot.yml` by hand if the VM is not coming back.

## Why two NICs

- **NIC1, NAT:** the way out (apt, npm, the model API). Always `10.0.2.15`
  inside VirtualBox's per-VM NAT, so DHCP.
- **NIC2, host-only:** a static address for SSH from the host, and the
  address Squid listens on. No gateway, on purpose: a second default route
  would race with NAT's.

The sandbox needs both: a pasta container carries a copy of the NAT
address as its own, so Squid cannot listen there, and it cannot reach the
VM's loopback either. The host-only address is the one left.

`network-config` matches interfaces by MAC, never by kernel name, so the
static address survives any interface renaming.

## VirtualBox 7.0 specifics

Verified against 7.0.26:

1. The `modifyvm` flags are the hyphenated 7.0 spellings
   (`--host-only-adapter2`, `--nic-type1`, `--cable-connected1`,
   `--mac-address1`, `--os-type`). 7.1 still accepts them; the playbook
   warns on any version that is not 7.0.
2. `createvm` takes `--ostype`, `modifyvm` takes `--os-type`. Both are
   right.
3. `showvminfo --machinereadable` still prints the old key names.
4. There is no `Debian13_64` OS type in 7.0, so `Debian_64` is used. It is a
   GUI label only; the guest is Debian 13 because of the image.
5. `modifymedium --resize` does not work on VMDK, hence the resize while the
   image is still qcow2.
6. The VMDK subformat is pinned to `monolithicSparse`.
7. `unregistervm --delete` plus a `closemedium dvd … --delete` for the seed
   ISO, not `--delete-all`. `--delete-all` fails as soon as the seed ISO is
   referenced more than once, by the current state and a snapshot, as on
   every VM after its first `take`: it deletes the snapshot images and the
   ISO, then stops at the base disk with `E_ACCESSDENIED` ("The object is
   not ready"), leaving the disk registered and the `.vbox` behind.
   `--delete` alone leaves the ISO registered, which blocks a later
   re-create, hence the `closemedium`.

## KVM conflict

On host kernels 6.8 and newer, KVM claims the virtualization extensions
when its module loads, and VirtualBox VMs fail to start with
`VERR_SVM_IN_USE` (AMD) or `VERR_VMX_IN_VMX_ROOT_MODE` (Intel). The
preflight detects this and stops with the fix.

Persistent, keeps KVM usable alongside VirtualBox:

```bash
sudo sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 kvm.enable_virt_at_load=0"/' /etc/default/grub
sudo update-grub && sudo reboot
cat /sys/module/kvm/parameters/enable_virt_at_load   # -> N
```

For this boot only:

```bash
sudo modprobe -r kvm_amd kvm      # AMD
sudo modprobe -r kvm_intel kvm    # Intel
```

## Troubleshooting

**The sandbox playbook fails with permission denied right after
provisioning.** cloud-init had not finished. Run
`ansible-playbook tutner.agent_sandbox.wait --limit sandbox-vm`.

**The VM starts but never answers on its host-only address.** Watch it
boot and check cloud-init inside the guest:

```bash
VBoxManage startvm sandbox-vm --type separate
# in the guest:
sudo cat /var/log/cloud-init-output.log
sudo cloud-init status --long
ip -br addr
```

Most likely a MAC in host_vars that does not match, or one shared with
another VM.

**Re-create fails with a UUID-already-registered error.** Stale media,
for example from a `destroy` that stopped partway:

```bash
VBoxManage list hdds
VBoxManage closemedium disk <uuid> --delete
VBoxManage list dvds
VBoxManage closemedium dvd <uuid> --delete
```

**Checksum mismatch on the base image.** Debian rotated `latest/`. Delete
the cache and re-run: `rm -rf ~/.cache/ansible-vbox-images`.

**VirtualBox rejects the host-only range.** Allow it in
`/etc/vbox/networks.conf`, e.g. `* 192.168.56.0/21`. Without that file,
`192.168.56.0/24` is allowed by default.
