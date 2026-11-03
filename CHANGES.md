# Changes

All notable changes to this repository are recorded here. Newest first at every
level.

## [Unreleased]

### 2026-11-03

#### Added

- README: new section "Starting and stopping the VM", listed in the table of contents. The VM does not start with the host; `provision` starts an existing VM that is off and waits for it, and needs the network for Debian's `SHA512SUMS`; or `VBoxManage startvm --type headless` followed by the playbook `wait`. Stopping with `VBoxManage controlvm <vm> acpipowerbutton`, and that a shutdown clears every `session` token.

## [0.2.0] - 2026-11-03 — Repository Tokens

### 2026-11-03

#### Changed

- README: a new banner, `docs/images/README_banner.png` (1280×640, also GitHub's social preview): a hooded robot with red eyes at a desk behind prison bars, its terminal answering `sudo: not found`, under a "World domination (pending approval)" poster, with the collection's name, its tagline "Let it work. Keep it in." and its four layers. Stripped of metadata; the alt text describes it.

### 2026-11-02

#### Added

- `docs/release-tests.md`: new section "The release test of v0.2.0", listed in the table of contents: the run of steps 1 to 9 on a new VM, steps 1 to 5 on `e31a15e` and 6 to 9 on the fix `6a30875`, with each step's `changed=` count; the known unknowns repeated on the same VM; the upgrade test from `v0.1.0`; three findings. "Not covered yet" drops the upgrade test and step 5 on a new VM, and names what step 5 leaves out and the unfixed check-mode finding.
- README, "Repository tokens": Claude Code's sandbox keeps the commands Claude runs from writing `.git/config`, so `git push -u` records no upstream although it says so and exits 0, and `git config` in the repository fails; set those up in `agentbox <project> bash`. Found in the release test of `v0.2.0`.
- Repository tokens: a project's tokens for cloning private repositories and pushing to any, each with the lifetime `session` (on tmpfs, deleted by the launcher when the project's next session ends, never on disk or in a snapshot) or `permanent` (in `~agent/.agentbox-tokens/<project>/`). New playbook `git_token` (`-e project=<name>`, `-e git_token_action=remove`), which fetches each token on the controller with `git credential fill`, so any credential helper there answers, run from `/` with no prompt; refuses a host off `egress_allowlist`; keeps the token out of every log (`no_log`, also under `-vvv` and `--check --diff`); and replaces what the project had. New variable `agentbox_git_tokens`, with a commented example in `examples/host_vars/sandbox-vm.yml`, and `agentbox_token_dir_name`. The image gets `git-credential-agentbox`, a credential helper for every host that answers from the mounted tokens, `session` before `permanent`, HTTPS only, and never stores. The launcher mounts them read-only at `/run/agentbox/git/`, names each token's host and lifetime at the start, and refuses a start while the project's session runs. The managed settings deny Claude's Edit tool `/run/agentbox/**`; not the Read tool, since Claude Code turns a Read deny into an empty tmpfs for the sandboxed commands, git among them. README: new section "Repository tokens", and a bullet under "What it protects, and what not": a token is readable by every command. `docs/design.md`: the section describes the code now, with what was tested on the controller and on a VM, and the findings; `docs/release-tests.md`: new step 5 for the tokens, through a shell and through Claude, with a private repository of your own kept for tests.
- `examples/ansible.cfg`: a commented-out `log_path = ./ansible.log`, since Ansible writes no log by default; the README's list of the example files mentions it.
- README, "Autonomous mode": a long silence of `-p` need not be a hang; an overloaded API answers `529 Overloaded`, which Claude Code retries quietly before it gives up. "Claude Code's own sandbox": how to see that a command Claude runs is inside the sandbox, with `podman top` from a second shell, and what to expect (`/run/podman-init`, `claude`, the command below `bwrap --new-session`). Both taken from the private repository's notes.
- `dev/releasing.md`: how this collection is released. What a tag means (never moved once pushed; not every commit tagged), which version a change gets (patch, minor, none for docs, 1.0.0 once the extension points are stable), the steps of a release, and the GitHub release that follows every tag (title, short notes with links at the tag, no pre-release for 0.x, no artefacts). `.claude/CLAUDE.md` refers to it, adds `dev/` to the doc files, and has the check before every commit whether a release is due and which version. Its rule on naming the AI model in commit messages now counts the `Co-Authored-By` trailer, so the model is no longer named twice.

- `docs/release-tests.md`: new section "The install of v0.1.0 from GitHub", listed in the table of contents: the first install from the GitHub URL at the tag, identical to the tag apart from the built `MANIFEST.json` and `FILES.json`, and the sandbox roles with `--check --diff` on the VM of the upgrade test, with nothing to change. The install from GitHub is gone from "Not covered yet".

#### Changed

- `snapshot` take: the wait for the guest to stop polls on through `showvminfo`'s transient `E_ACCESSDENIED` ("The object is not ready") while the VM is stopping, and waits for `poweroff` or `aborted` rather than anything but `running`; a new assert refuses the snapshot, with a message, if the guest did not stop in time. Before, that error failed the play with the VM off and no snapshot, a race that the release test of `v0.2.0` hit at step 6; and a `stopping` VM passed as stopped.
- The launcher stops the container on `SIGHUP`, `SIGINT` and `SIGTERM`, so a dropped SSH connection ends the session. Before, the hangup killed `podman run` but not the container, which `conmon` kept running, holding the project's name until stopped by hand; seen in the VM test, and already true of `v0.1.0`. README, "The launcher": a lost terminal ends the session; `tmux` or `nohup` for a run that should outlive it. `docs/design.md`, "The launcher contract": the same, with why.
- The image changes, so the default `sandbox_image_tag` is now `0.2.0`, as in `examples/group_vars/agent_sandbox.yml`. **An existing install must bump its tag**: the role refuses to rebuild 0.1.0 from the new recipe. The build label is now `agentbox.build-sha256`, over the Containerfile and the files it copies, instead of `agentbox.containerfile-sha256`. The role's check of the image also asserts git's credential helper. The launcher no longer `exec`s `podman run` but waits for it, to delete a session token afterwards. The role's sandbox user lookup moved to `tasks/paths.yml`, shared with `git_token`.
- `docs/design.md`: "Private repositories" is now "Repository tokens", since pushing needs a token for a public repository too. It moves out of "Possible features" into a section of its own, marked planned, with the design as decided: two lifetimes, `session` (on tmpfs, deleted by the launcher when the session ends, never in a snapshot) and `permanent` (on disk); tokens fetched on the controller with `git credential fill`, so any credential helper answers and the collection knows no password store, run from `/` so that no repository's own credential settings apply; a playbook `git_token` that writes and removes them, apart from the `sandbox` run; a host off the allowlist refused; a credential helper in the image that never stores, read-only mounts per lifetime, a Read and Edit deny on them, and the launcher naming each token's host and lifetime; what it does not protect, and what done would mean. "Core and extensions" and "Secrets, honestly" point to it.
- README, "Check the sandbox": the roles' own checks run from the VM, not from inside a container; when to run the smoke tests (once after the first `sandbox` run, before the baseline snapshot, and after changing the allowlist or the policy), and that nothing enforces them.
- README, "Install": no existing Ansible project is needed; where `ansible-galaxy` puts the collection (`~/.ansible/collections/ansible_collections/tutner/agent_sandbox/` by default), `-p` with `collections_path`, `ansible-galaxy collection list` to find it, and `requirements.yml` for a project you already have. "Configure": the collection brings the playbooks, the contents of `examples/`, copied into it, are the whole working directory, and every command runs from inside it, since Ansible reads `ansible.cfg` from the current directory.
- `docs/virtualbox.md`, "VirtualBox 7.0 specifics": the 6.x and 7.0 names of the `modifyvm` flags as a table; the old key names `showvminfo` prints and why they matter; why `Debian_64` is only a GUI label, with a command to check the guest's release; why the VMDK subformat is pinned; new item 8, `qemu-img` 6.2 on an Ubuntu 22.04 host being enough. "Snapshots": long chains slow disk I/O and take space, which is why `take` prunes. All taken from the private repository's README, where they were documented before.

#### Decisions

- `docs/design.md`, Decision 18: repository tokens are core, not an extension, while the extension points are not built; they come from the controller's git through `git credential fill`; they have a `session` and a `permanent` lifetime; neither is minted or revoked at the remote, so the token's scope and expiry are the limit.

#### Notes

- Release test of `v0.2.0`, recorded in `docs/release-tests.md`: all steps pass, step 6 after the fix `6a30875`; the known unknowns give the answers of 2026-10-31; the upgrade from `v0.1.0` shows exactly the changes listed here, after the tag bump it refuses to do without, then `changed=0`. Findings: `snapshot` take failed on VirtualBox's transient error while the guest was stopping (fixed); Claude cannot write `.git/config` in its sandbox (Claude Code's behaviour, now in the README); `--check --diff` does not show an image rebuild, already so in `v0.1.0` (not fixed).
- Repository tokens tested on a VM, by hand, with a self-hosted GitLab and a private GitHub repository kept for tests: both lifetimes, in a shell and through Claude's sandbox, the token in no file, config or transcript, the session token gone after the session and after a dropped connection. Four findings, recorded in `docs/design.md`, "Findings on the VM": the playbook tried `sudo` on the controller under an inventory with `ansible_become: true` in `group_vars/all.yml`, fixed with a task variable; a dropped connection left the container running, fixed in the launcher; a Read deny hid the tokens from git inside Claude's sandbox, so it went; `git clone <url> .` fails inside Claude's sandbox on Claude Code's `/dev/null` stand-ins in `/work`.

### 2026-10-31

#### Added

- README: a banner under the title, `docs/images/README_banner.png` (1280×640, also fit for GitHub's social preview): a retro robot working contentedly in a cosy cell behind bars, labelled with the VM, rootless Podman and the egress allowlist. Stripped of metadata.

#### Changed

- README: the title says what the collection is, "A sandbox for agentic coding on VirtualBox", instead of the repository's name.

## [0.1.0] - 2026-10-31 — A system you can build on

### 2026-10-31

#### Added

- `.claude/CLAUDE.md`: the project's conventions for working on it with Claude Code — the rules for the public repository (nothing private, the noreply address, VirtualBox only, semver below 1.0.0, Git install only, release tests before a release), the commit and CHANGES.md rules. `.gitignore` keeps Claude Code's per-machine `.claude/settings.local.json` out.
- `docs/release-tests.md`: the release tests. A checklist for running them before a release, on a new VM from the release's commit and with the public docs alone: provision, `sandbox` twice with `changed=0` the second time, the README's smoke tests, snapshots taken and restored with `ssh` right after, `destroy` on a VM with snapshots; an upgrade test with `--check --diff` where a release changes a role, and the known-unknowns session where it changes Claude Code, the managed settings or the launcher. Then the record of the runs before `v0.1.0`: three full runs on fresh VMs, the re-test that explained `destroy`'s failure on VMs with snapshots, the upgrade of the VM the design was developed on from the roles' older copies, and the known-unknowns session, with what each found and the commits that fixed it. The README and `docs/design.md` point to it.
- `docs/design.md`: the design behind the collection, edited from the private repository's design docs for the public: the layers, the sandbox account, the four roles with their traps and the finding on what a pasta container can reach, the policy surface, the launcher contract, "Secrets, honestly", core and extensions, the extension points (planned), the rules for extensions and the security boundary (proposed), the known unknowns with their results and the plan they were tested by, the possible features, why not bare metal, the decisions in force with their reasoning, and gVisor in a section of its own, marked experimental. New in it: the rule for credential extensions, which follows from the test of the environment: no credential in the environment or on a command line; a file under the credentials deny where Claude Code reads it; a narrow scope, and saying so, where a command such as git does. The README's "What it protects, and what not" points to it.

- README: new section "Check the sandbox", listed in the table of contents: the smoke tests to run once as `agent` after the first `sandbox` run and before the baseline snapshot. They check that the memory limit binds, an allowlisted host works through the proxy, a host not on the list gets Squid's 403, a direct connection past the proxy is refused, no resolver answers, and the launcher runs as uid 1000 with the policy's limits and the pinned Claude Code. The proxy address is read from `$https_proxy`, which Podman's `containers.conf` hands to every container. The step to take the baseline moved there from "Create the VM and the sandbox", and `docs/virtualbox.md` says to take it after the smoke tests.

#### Changed

- `docs/design.md`: the reference architecture from the private repository, edited and folded in as "Why this stack" under "The layers": a diagram of the stack as the core builds it, why the guest is Debian 13 whatever the host runs (Ubuntu 22.04's Podman 3.4 has no pasta, which the egress rule depends on), why rootless Podman rather than Docker, egress as an allowlist rather than no network, and only the project mounted into a session. gVisor is left out of the diagram and points to its experimental section; the old advice of scoped tokens in environment variables points to "Secrets, honestly", which says why it does not hold. `docs/virtualbox.md`, "Adding a VM": sizing guidance next to the role's defaults. The README's "What you get" points to "The layers".
- README: the results of the tests for the open questions, on Claude Code 2.1.284. "What it protects, and what not" has a new item: every command Claude runs inherits the session's environment, `agentbox_claude_env`, `agentbox_auto_claude_env` and the API key included, and command lines are readable through the container's `/proc`, while another process's environment and the login are not; so no credential goes into the environment or onto a command line. "Logging in" and "Configure" say so for the API key and for the environment. "The launcher": a second session in the same project is refused, and two sessions in different projects, each cloning a repository and running `npm install`, peaked at about 310 MB each. "Open questions" now lists what those tests left open: heavier work in two sessions, and whether Claude Code withholds `ANTHROPIC_API_KEY` by name. The comments on `agentbox_api_key_secret` and `agentbox_claude_env` in the role's defaults say the same.
- `examples/group_vars/agent_sandbox.yml`: `DISABLE_ERROR_REPORTING: "1"` added to `agentbox_claude_env`, next to `DISABLE_TELEMETRY`. The image's Claude Code (2.1.284) knows the switch, and error reporting's host was never seen, so it is off and denied on purpose, like telemetry. The README's "Egress" says so, and error reporting is gone from its "Open questions".
- `destroy`: works on a VM with snapshots. `unregistervm --delete-all` failed as soon as the seed ISO was referenced by a snapshot as well as the current state, as on every VM after its first `take`: it stopped at the base disk with `E_ACCESSDENIED`, leaving the disk registered, the `.vbox` and the build artefacts behind. Now `unregistervm --delete` removes the disks and the `.vbox`, `closemedium dvd --delete` the seed ISO, once, and the machine folder is removed after a check that it is named after the VM. Tested on a VM with a branched snapshot tree, and on a VM that no longer exists. `docs/virtualbox.md` says so, and that the snapshot state file outlives `destroy`.
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
