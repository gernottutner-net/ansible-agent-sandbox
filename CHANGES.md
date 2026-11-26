# Changes

All notable changes to this repository are recorded here. Newest first at every
level.

## [Unreleased]

## [0.7.0] - 2026-11-26 — The Editor

### 2026-11-26

#### Added

- `meta/updates.yml`: the entry for 0.7.0, for `update_check`: `sandbox --tags agentbox`, no image change, the nine new editor variables, `agentbox-remote` changed.

#### Changed

- `galaxy.yml` and the README's pinned install examples at `v0.7.0`.
- `.claude/CLAUDE.md`: commit messages carry the `Co-Authored-By` trailer as their only attribution: no `Claude-Session:` trailer or other session link, which Claude Code's instructions began to ask for; the repository is public, and the link points into a private account. Release proposals: every commit proposal says whether a release is due, by dev/releasing.md, and if so proposes the version, a short release name drawn from the change and the tag message, which I accept, rename or decline; a proposal is not a cut. A release's name is the one accepted or renamed from a proposal, or given with the request, and without one the bare version.
- `docs/release-tests.md`: new section "The release test of v0.7.0", in the table of contents and the intro: steps 1 to 9 on a VM of its own, the checks of `--tmux` and `agentbox-remote`, of the editor and the known-unknowns session, and the upgrade test from `v0.6.0` on a VM taken back to `v0.6.0` first; "Not covered yet" drops the skipped full runs of `v0.5.0` and `v0.6.0` and `update_check`'s untested cases, and names `SIGINT`, a `git_token` session token under `--tmux`, `update_check`'s line on unset variables and a browser other than Chromium. `docs/design.md`, "The editor": the refused VSIX did not stay in the release test, and the unexplained `--tmux` disconnect was not reproduced in it.
- The editor with `agentbox_editor_accept_server_license` set back to `false`: the role keeps the editors' settings and state in `~agent/.agentbox-editor`, as it keeps Claude Code's in `~agent/.agentbox`, but the defaults comment and the entry of 2026-11-16 said it removes everything but the image. Both corrected; the README's "The editor" says what such a run removes and what stays (found in the release test of v0.7.0).
- README, "Updating the collection", step 5: run what `update_check`'s "To apply" line names, in order, usually `sandbox --check --diff`, then `sandbox`; no longer `provision` every time. It was in the step since before `update_check` existed, as a catch-all; now `meta/updates.yml` lists it only for 0.3.0, and on a running VM, which step 4 needs, it changes nothing. A new step 6: `update_check` afterwards reports "Up to date", and `-e install_scripts=true` replaces a controller script it reports as different.
- README, "Snapshots and teardown": `restore` works on a running VM, powering it off hard and starting it again; a VM that is off stays off, with a link to "Starting and stopping the VM"; a restore brings back the memory and CPUs the VM had then, with a link to "Tuning the VM". `docs/virtualbox.md`, "Behaviour notes": the same about the settings, and that the next `provision` with the VM off applies the variables again (seen 2026-11-26: a `base` from 6 GB came back with 6 GB).

### 2026-11-16

#### Added

- The editor (#15): VS Code for the browser beside each session. Microsoft's VS Code Server, run as `bin/code-server` from its server build, in a container `agentbox-<project>-editor` of its own on the same `/work`, reached from the controller through `ssh -L` to a socket in `/run/agentbox-editor/<project>/`. Off until `agentbox_editor_accept_server_license: true`, which accepts Microsoft's licence; until then the role installs nothing of it, and with the variable set back to `false` it removes the editor's files and group; the image and `~agent/.agentbox-editor` stay. The `agentbox` role then fetches the pinned server build on the VM (`agentbox_editor_vscode_version`, `_commit`, `_sha256`, checked by `get_url`), builds `localhost/agentbox-editor:<agentbox_editor_image_tag>` (default `0.1.0`) under the same one-tag-one-build rule as the session image, writes read-only machine settings (`extensions.allowed: {"*": false}`, no extension updates, telemetry off), creates the group `agentbox-editor` with the account Ansible connects as as its only member, the socket directory from a tmpfiles entry, and `~agent/.agentbox-editor`, and ends by checking the image: the pinned commit, uid 1000, no extensions, an extensions directory the user cannot write. **Action needed on an existing install:** none; to use the editor, set `agentbox_editor_accept_server_license: true` and run `sandbox --tags agentbox`.
- The launcher starts the editor before a session on a terminal that is not a `-p` run (`agentbox_editor`, default `true`), or as `--editor` and `--no-editor` say: limits of its own (`agentbox_editor_memory`, `_cpus`, `_pids_limit`: `1g`, `1.0`, `256`), `--init`, `--cap-drop=ALL`, `no-new-privileges`, and only `/work`, its state, its socket directory, a new token per session and the machine settings; no repository tokens, API key or Claude Code state. The socket directory is recreated at each start, the token deleted and the editor stopped when the session ends, on a signal too; uploads the server refused are emptied from its state at start. `--list` shows `editor`. A failed editor start leaves the session running.
- `examples/agentbox-remote --open-editor <project> [port]`: reads the session's editor token over SSH, prints the URL and holds the tunnel from `127.0.0.1:<port>` (default 8765, `AGENTBOX_EDITOR_PORT`) until `Ctrl-C`.
- `examples/group_vars/agent_sandbox.yml`: the editor's variables, commented out.

#### Changed

- The launcher takes its options before the project in any order: `--tmux`, `--auto`, `--editor`, `--no-editor`. `--tmux` passes the others on to the launcher in its pane.
- The image build of the `agentbox` role moved into `tasks/image.yml`, shared by the session image and the editor image; the session image's recipe hash is unchanged, so no rebuild.
- README: new subsection "Sessions", "The editor", in the table of contents: installing it, opening it from the controller, when a session gets one, what it gets and keeps out, the display language, `.git/index.lock` with two writers, the group and `ControlMaster`, memory, the browser outside Squid, updating VS Code, and why not Remote-SSH. "What you get", "The launcher", "From the controller", "Tuning the VM", "Configure" and "What it protects, and what not" name it; "Open questions" gains item 3, editors under load, and the logins other than Pro become item 4.
- `docs/design.md`: new section "The editor", with "Why not Remote-SSH", "The pieces", "What it keeps out", "What was tested" and "What is open", in the table of contents; "`agentbox`: image, managed settings and launcher", "The policy surface" and "The launcher contract" name it. `docs/release-tests.md`: what a release that changes the editor or the launcher checks; "Not covered yet" names the editor under load, the built-in extensions and the unexplained `--tmux` disconnect.

#### Decisions

- Decision 24: the editor is VS Code Server in a container of its own beside each session, opt-in by the licence. Not Remote-SSH, which trusts the VM; not inside the session's container, so the editor gets `/work` and no Claude Code state or tokens; on by default once installed; the server build fetched by the role on the user's VM and pinned by version, commit and SHA-256; no extensions to start with, each later one an image change with a review.

#### Notes

- Tested on `sandbox-vm` with VS Code 1.146.0 (`6904719`), first as a spike by hand, then the role and the launcher from the working tree; the results are in `docs/design.md`, "What was tested", and on #15. The first role run put `root` in the group instead of the account Ansible uses, because the inventory's `ansible_become: true` outranks a task's `become: false`; fixed with a task variable before the commit. The diagrams in `docs/images/` do not show the editor yet.

### 2026-11-15

#### Changed

- README, "Updating the collection", step 4: the VM must be running for `update_check`, which reads its stamp over SSH; of a VM that is off it reports only that it is not reachable. With a link to "Starting and stopping the VM".

## [0.6.0] - 2026-11-15 — Update Check

### 2026-11-15

#### Added

- New playbook `update_check`: what a collection update means for an existing install, without changing anything. For each VM, the collection version that last applied each role, and for every release since then the playbook runs it needs in order, whether the image recipe changed (with the inventory's `sandbox_image_tag` and the new default), the new variables with whether the inventory sets them, and the controller scripts that are new or changed; then the variables `examples/` sets and the inventory does not. On the controller, each script from `examples/` (now `agentbox-remote`): not installed, current, or different, looked up on `PATH` and in `agent_sandbox_bin_dir` (default `~/.local/bin`). `-e install_scripts=true` installs them there, with a backup of a copy that differs, and warns when the directory is not on `PATH`. A VM that is off gets a line saying so; the controller's part runs all the same. **Action needed on an existing install:** none; run `sandbox` once so the VM gets its stamp.
- `meta/updates.yml`: what each release since 0.1.0 needs on an existing install, for `update_check` to read; the machine-readable form of "Action needed on an existing install".
- `sandbox` stamps the roles it ran with the collection's version in `/etc/agent-sandbox/deployed.json` on the VM, per role and without a date, so a run with `--tags` stamps only the roles it selects and a second run stays `changed=0`. It warns, and goes on, when the installed collection is older than what last applied a role. The version comes from `MANIFEST.json` of an installed collection, or `galaxy.yml` in a clone (`playbooks/vars/collection.yml`).
- `examples/group_vars/agent_sandbox.yml`: `agent_sandbox_bin_dir`, commented out.

#### Changed

- README, "Updating the collection": a new step 4 runs `update_check`; new subsection "What an update needs", in the table of contents; going back says that `sandbox` warns. "From the controller": install `agentbox-remote` with `update_check -e install_scripts=true`, which also replaces it after an update.
- `docs/release-tests.md`: new section "The release test of v0.6.0", in the table of contents and the intro; the upgrade test also runs `update_check` before and after; "Not covered yet" names what the release test did not cover and the skipped full run. `galaxy.yml` and the README's pinned install examples at `v0.6.0`. `meta/updates.yml`: the entry for 0.6.0.
- `dev/releasing.md`, "How to release": a new step 2, the release's entry in `meta/updates.yml`; the later steps renumbered.

#### Decisions

- Decision 23: an update is reported, not applied, beyond what the roles own. `update_check` edits no inventory file, whose comments, order and values are the user's; the stamp is per role and dateless; the release actions live in `meta/updates.yml`, not parsed from CHANGES.md; controller scripts are installed only on request; `sandbox` warns about a downgrade and goes on.

## [0.5.0] - 2026-11-15 — TMUX

### 2026-11-15

#### Added

- Sessions that outlive the connection: the launcher's `--tmux` runs a session inside the tmux session `agentbox-<project>` on the VM (`.` in the name as `+`), or attaches to it if it is there; a detach or a lost connection leaves it running, `tmux kill-session` ends it as a lost terminal does. The tmux server starts in a scope of `agent`'s systemd user instance, so a logout does not end it. It refuses a second start with arguments, and a project with a plain session running, before tmux starts. `--list` shows the projects and which have a container or a tmux session. The `agentbox` role installs `tmux` on the VM. **Action needed on an existing install:** run `sandbox`, or `sandbox --tags agentbox`; no image rebuild.
- `examples/agentbox-remote`: starts or attaches a session from the controller over `ssh -t`, with the launcher's arguments passed on unchanged. `AGENTBOX_HOST` and `AGENTBOX_USER` name the VM and the sandbox account. It runs `sudo -u agent -H -- sh -c …`, not `sudo -i`, whose login shell would expand a `$NAME` in a `-p` task.

#### Changed

- `docs/release-tests.md`: new section "The release test of v0.5.0", in the table of contents and the intro; "Not covered yet" names the skipped full run and known-unknowns session. `galaxy.yml` and the README's pinned install examples at `v0.5.0`.
- The launcher runs `podman run` in the background and waits for it with `wait`, so a signal to the launcher stops the container at once, also when the client is not signalled itself. Under tmux a closed pane hangs up only the launcher; with the client in the foreground the trap waited forever and the container kept running (found 2026-11-15, testing `--tmux`). The client still gets the terminal as its stdin. Plain sessions retested on the VM: typed input, exit status, piped stdin, `kill -9` on the `ssh` client, `SIGTERM`, `SIGINT` and `SIGHUP`.
- README, "Sessions": new subsections "Sessions that outlive the connection" and "From the controller", in the table of contents; "The launcher" points there instead of to `tmux` or `nohup` by hand. `docs/design.md`, "The launcher contract": new subsection "Sessions that outlive the connection", in the table of contents, and the lost-terminal paragraph points to it; "`agentbox`: image, managed settings and launcher" names `tmux`. `docs/release-tests.md`: a check of `--tmux` and `agentbox-remote` for a release that changes the launcher.
- README: says when a change to the inventory reaches the VM, after a token missing from a new project's session and a link that was in the inventory but not on the VM. "Configure": the VM knows only what a playbook wrote; a table of what to run after which change (`git_token`, `sandbox`, `provision`) and that running sessions have to start again. "The launcher": the lines it prints as a session starts, for each token and for a link, and what a missing one means. "Getting a project in": the `git_token` step before the session. "Agent Intercom": the exact line of a linked session, and that without it the session is not linked.
- `.gitignore`: `/tmp/` in the repository root, for scratch files kept beside the clone, such as drafts of release announcements.

#### Decisions

- Decision 22: sessions outlive the connection in tmux, on the VM, behind the launcher. Not in the container, where tmux would run under the limits and be gone with `--rm`; not inside the launcher's `podman run` line, which stays the one place of the run policy. A browser terminal was considered and left out: a web service holding a way into every session, for little more than `ssh -t` and tmux give.

#### Notes

- The release test of `v0.5.0`, shortened by decision: the upgrade test from `v0.4.0` on `sandbox-vm` (`changed=2`, then `0`, with two linked sessions running throughout) and the test of `--tmux`, `agentbox-remote` and the launcher's plain path passed. The full run on a new VM and the known-unknowns session did not run: too little free memory on the host for a second VM, and both need logins. The test of `--tmux` found the launcher's foreground wait, fixed before the release.

## [0.4.0] - 2026-11-15 — Agent Intercom

### 2026-11-15

#### Changed

- README, "Repository tokens": no longer says that Claude Code's sandbox keeps the commands Claude runs from writing `.git/config`. Claude wrote the upstream there with `git push -u` in the release tests of `v0.3.0` and `v0.4.0`, and not in that of `v0.2.0`; why is not known. The README now says not to count on it, and to treat `.git/config` like the rest of `/work`. "Updating Claude Code": the prefix example becomes `0.4.0-cc2.x.y`, the image tag of this release. `docs/release-tests.md`, finding 1 of `v0.4.0`, says the README changed.
- `docs/release-tests.md`: new section "The release test of v0.4.0", listed in the table of contents and the intro. "Not covered yet": the `.git/config` bullet names the release test of `v0.4.0` too.

#### Notes

- The release test of `v0.4.0` on `ccdd460`, on a new VM `rt-vm`: steps 1 to 9 pass, with `changed=15`, `30`, `0`, step 5 with both lifetimes, the snapshots and `destroy`. The Agent Intercom table repeated from the commit as a short check, every row passing; the known-unknowns session counted from 2026-11-14. Upgrade from `v0.3.0` on `sandbox-vm`: `--check --diff` shows exactly the two managed-settings keys, `changed=1`, then `changed=0`. No bug found. Claude wrote the upstream into `.git/config` with `git push -u`, as in the release test of `v0.3.0`, against what the README's "Repository tokens" says; the README is not changed with this record.

### 2026-11-14

#### Changed

- Claude Code 2.1.323 in the image, up from 2.1.284, and the default `sandbox_image_tag` `0.4.0`, up from `0.2.0`, following the collection version of the release that changes the image: `roles/agentbox/defaults/main.yml`, `examples/group_vars/agent_sandbox.yml`, `docs/design.md` (the intro and "The policy surface") and `docs/images/claude-code-image.svg`, regenerated from its source, where the old image in storage is now `0.2.0`. The README's update example becomes `0.4.0-cc2.x.y`. 2.1.323 rather than 2.1.317, the version linked sessions were first tested with, for four sandbox fixes in 2.1.319 to 2.1.323. **Action needed on an existing install:** none beyond the playbook run; the new tag is built beside the old one.
- The managed settings set `allowManagedHooksOnly: true` and `permissions.defaultMode: "default"`; the template's comment says why. No hook or mod loads but from the managed settings, which define none, and a session without `--auto` starts in manual mode again. `--auto` still runs in bypass mode.
- `docs/design.md`: "Known unknowns" 4 answered, with the test, and 1 to 3 repeated on 2.1.323 with the same answers; "How they were tested" gains step 6, the mod test. "Agent Intercom", "What was tested": the table repeated on 2.1.323, with a row for `allowManagedHooksOnly`, the connectors' host showing in Squid only when the session ends, and the trust dialog's default. "`agentbox`: image, managed settings and launcher" and "The launcher contract" name the two settings; Decision 14 points to Decision 21.
- README: "The launcher" says a plain session starts in manual mode and that Shift+Tab switches to auto mode; "Logging in" says the folder trust dialog defaults to *No, exit*; "Claude Code's own sandbox" says no hook or mod loads, and why; "Agent Intercom" says it was tested with the example policy's version; the RAM bullet adds the 2.1.323 figure. "Open questions": item 3, mods Claude writes, is gone, and the logins other than Pro become item 3.
- `docs/release-tests.md`: new section "Claude Code 2.1.323, before v0.4.0", listed in the table of contents. "Not covered yet": the linked sessions' bullet no longer names 2.1.284; a new bullet for a mod in manual mode without `allowManagedHooksOnly`.

#### Decisions

- Decision 20: hooks and mods only from the managed settings, which define none. From 2.1.321 a mod Claude writes turns on without asking in bypass and auto mode and runs outside the inner sandbox, with the login readable; `allowManagedHooksOnly` stopped it in both modes, and built-in plugins and linked sessions kept working. The cost: no hooks or mods from the user, a project or a plugin.
- Decision 21: interactive sessions start in manual mode. With 2.1.323 and a Pro login they started in auto mode, Claude Code's new default, against Decision 14's interactive default. Its notice is already in 2.1.284, so when it began for the sandbox is not known.

#### Notes

- Tested on `sandbox-vm` with the working tree, the settings as extra vars: the image build and `changed=0`; every row of the linked-session table; the mod test in `--auto` and in auto mode, with and without `allowManagedHooksOnly`; `defaultMode` with a plain session and with `--auto`; the known-unknowns session. Logins other than Pro and `channelsEnabled` not tested: no such login was available.

### 2026-11-13

#### Changed

- Linked sessions get a name, the Agent Intercom. The section "Sessions that talk to each other" in `docs/design.md` and in the README is now "Agent Intercom", with the TOCs, the links to it, Decision 19 and the README's `agentbox` row; the comments in the role and the example inventory that point to it follow. The variables, files and units keep their `peer` names.
- `docs/design.md`, "`agentbox`: image, managed settings and launcher": the role's list of what it sets up names the peer broker, its unit and its two files, installed only with `agentbox_peer_links` and removed without.

#### Notes

- `docs/release-tests.md`, "Not covered yet": the linked sessions' bullet adds logins other than Pro, and points to "What was tested" for Claude Code 2.1.284, which is where that is said, instead of "What is open".
- Claude Code's release notes from 2.1.285 to 2.1.323 read for what touches the collection. `docs/design.md`, "Known unknowns": a new item 4, open. From 2.1.321 a mod Claude writes turns on without asking in bypass mode, so in an `--auto` session, despite the managed `allowUnsandboxedCommands: false` and `allowManagedDomainsOnly`. It runs outside the inner sandbox, and whether `allowManagedHooksOnly` or `disableAllHooks` keeps it off is not known. It needs an answer before the pin moves to 2.1.321 or later, while moving past 2.1.317 brings four sandbox fixes, listed there. "How they were tested" now says the first three. `docs/design.md`, "Agent Intercom", "What is open": Team, Enterprise and API-key logins probably need `channelsEnabled: true` in the managed settings for channels (release notes 2.1.81 and 2.1.128), which the collection does not set; only a Pro login was tested. README, "Open questions": both, as items 3 and 4. Not affecting the collection: stdio servers offered MCP 2026-07-28 from 2.1.292, which the broker answers with 2025-06-18; an unreadable managed settings file no longer stopping Claude Code from 2.1.285, which the launcher's check before the start covers; and the `ALL_PROXY` changes, since the collection sets `HTTPS_PROXY`.
- Not yet showing linked sessions: `docs/images/architecture.svg` and the interactive version linked from the README. They show the sandbox without links, which is the default.

### 2026-11-05

#### Added

- Sessions that talk to each other. With `agentbox_peer_links` in the inventory, Claude in one session can talk to Claude in another, with nobody typing. New in the role `agentbox`: `agentbox-peer-broker`, a deterministic Python program in a hardened system unit, one Unix socket per project with the sender taken from the socket, a tool `send`, a message budget per pair of projects that only a person starting a session resets, every message in the journal; `tasks/peer.yml`, which also removes it all when the links are gone. The launcher links a plain interactive session in a project with a link: its socket, `managed-mcp.json`, Claude Code's development channels, no `DISABLE_TELEMETRY`. `--auto`, `-p` and other commands are not linked. `dev/test-peer-broker.py` tests the broker alone.
- `docs/design.md`: new section "Sessions that talk to each other", with what was tested. README: new section of the same name, a line in "What it protects, and what not", and the `agentbox` row. `dev/linting.md`: "The peer broker". `docs/release-tests.md`: when to repeat it, and what is not covered. `examples/group_vars/agent_sandbox.yml`: the links, commented out.

#### Changed

- `docs/design.md`, "Core and extensions": linked sessions join repository tokens as a former extension candidate that is in the core.

#### Decisions

- Decision 19: linked sessions are core, off by default, and for interactive sessions only. Without links, the launcher and the managed settings render byte for byte as before, checked against the previous commit. A link costs telemetry in those sessions, because Claude Code's channels do not work with `DISABLE_TELEMETRY`; accepted as the price of channels.

#### Notes

- Tested on a VM with Claude Code 2.1.317, through the launcher: a conversation with nobody typing, the budget stopping it, `--auto` not linked, a sandboxed command refused at `socket(AF_UNIX)`, and the play's second run at `changed=0`, with and without links. Not with the pinned 2.1.284 of the example policy. No image change, so no new tag.

### 2026-11-03

#### Added

- `dev/releasing.md`: new section "Announcing", listed in the table of contents, and step 8 in "How to release": announce the release on Mastodon and X by hand once the GitHub release is up, from a template: the headline change first, the repository linked, not the release page, whose link card is always GitHub's generated release card instead of the social preview banner (checked with `v0.3.0`), hashtags on Mastodon, on X the link in the first reply, the banner with its alt text only where a post has no link card; on X, 280 characters with a link counting as 23, short sentences instead of bullets, and two or three hashtags.
- README: new section "Updating the collection", after "Install" and listed in the table of contents. Read the release's "Action needed on an existing install" first, snapshot the VM, install the new tag over the old one or bump `version:` in `requirements.yml`, check with `ansible-galaxy collection list`, then `provision`, `sandbox --check --diff` and `sandbox`. From a Git URL `ansible-galaxy` installs every time, also an older tag over a newer one, so `--force` is not needed; it replaces the installed collection as a whole, and leaves the working directory alone. Going back: the previous tag and the snapshot. Tested with `-p` in a throwaway directory, from GitHub: `v0.2.0`, then `v0.3.0` and the unpinned URL without `--force`; `requirements.yml` at `v0.2.0` over `v0.3.0`, and back; a file added inside the installed collection gone after the next install.

#### Changed

- The project gets a brand name, **sacVB**: sandbox for agentic coding on VirtualBox. README: the title becomes "sacVB: a sandbox for agentic coding on VirtualBox", and the intro spells the name out; `galaxy.yml`'s description starts with it. `docs/images/README_banner.png`, also the GitHub social preview, shows sacVB as a wordmark above "sandbox for agentic coding on VirtualBox", where it said "A sandbox for agentic coding on VirtualBox"; the README's alt text names it.
- README, "Install": the command installs the release by its tag, `,v0.3.0`, instead of `main`; a tag is the commit that passed the release tests and is never moved, while `main` is what comes next, untested as a release, and still reports the last release's version. `dev/releasing.md`, "How to release", step 3 names the three pinned examples a release updates.

#### Decisions

- sacVB is a brand only: the repository stays `ansible-agent-sandbox` and the collection `tutner.agent_sandbox`, so install URLs, FQCNs and existing playbooks keep working. Written `sacVB` in prose, `sacvb` where only lowercase works, such as GitHub topics and file names.

## [0.3.0] - 2026-11-03 — Tuning the VM & Super Nice Diagrams

### 2026-11-03

#### Added

- `docs/release-tests.md`: new section "The release test of v0.3.0", listed in the table of contents: steps 1 to 9 on `59a7843`, on a new VM `rt-vm` with 4 GB beside the `sandbox-vm` in use, with each step's `changed=` count, all passed; the upgrade test from `v0.2.0` on `sandbox-vm`, where `provision` applied `vm_memory_mb: 4096` to the powered-off VM; two observations, no bug: `git push -u` in Claude's sandbox wrote `.git/config` this time, unlike finding 1 of `v0.2.0`, and the memory and CPU step is untested on a saved or paused VM. "Not covered yet" names the first.
- Linting with `yamllint` and `ansible-lint`. `.yamllint`: yamllint's defaults, lines up to 120 columns, and the settings ansible-lint expects. `.ansible-lint`: the `production` profile, without `.claude/`, `.vscode/`, `.ansible/`, `docs/`, `dev/` and `security/`, and three rules skipped, each with its reason: `var-naming[no-role-prefix]` (the variable names are the interface), `name[template]` (the `[{{ vm_name }}]` prefix) and `galaxy[no-changelog]`. New `dev/linting.md`: how to run them, what they check, the configs and the skips, and how to install them on Ubuntu 22.04, not with ansible-core 2.17 pinned, which ansible-lint 26.10.1 refuses. `docs/release-tests.md`, "Before": both pass on the commit under test. `.claude/CLAUDE.md` lists `dev/linting.md` as context.
- `security/audits/2026-11-03-ansible-lint.md`: an audit of what a pipx install of ansible-lint 26.10.1 pulls in. Socket Firewall allowed all 31 packages; OSV lists 17 advisories, all in `filelock` 4.1.0, which pip picks on Python 3.10; one of them is reachable, and only when ansible-lint's cache falls back to `/tmp`. With the reachability from ansible-lint's source, ranked recommendations, and the OSV check script.
- `virtualbox_vm`: `provision` applies `vm_memory_mb` and `vm_cpus` to an existing VM with `modifyvm` when it finds the VM powered off (or aborted) and either value differs. Before, both were used only when the VM was created, and changing them for an existing VM did nothing, silently. A VM that is running, paused or saved keeps its values, with a message naming the configured and the asked-for values and what to do; the role never shuts a guest down for them. `vm_disk_size` and `vm_vram_mb` still apply only to a new VM. The role's defaults, `examples/host_vars/sandbox-vm.yml` and `docs/virtualbox.md`, "Provisioning", say so; the README's "Create the VM and the sandbox" and "Starting and stopping the VM" too.
- README: new section "Tuning the VM", listed in the table of contents. A table of the VM's and the session's size variables, where each is set and when it takes effect; the commands to change the VM's memory and CPUs and check them; that a snapshot `restore` brings back the values recorded in the snapshot; applying the session limits with `sandbox --tags agentbox`; how big for one session and for more; what the VM costs the host: VirtualBox keeps every guest page it has used, the guest's file cache among them, until the VM stops, so the VirtualBox process grows towards `vm_memory_mb` while the guest shows little in use, and a host that swaps slows the guest down, with `TM: Giving up catch-up attempt` in `VBox.log`; and that the disk size applies only to a new VM.
- README, "Updating Claude Code": how to name the tag. The role compares tags for equality only, never by order. The recommended tag is the collection's default tag plus `-cc` and the Claude Code version, such as `0.2.0-cc2.1.290`: it shows which Claude Code an old image holds, cannot be confused with a later default of the collection, and uses `-` because image tags do not allow `+`. The example changes from `0.3.0` to `0.2.0-cc2.x.y`, and so does the update row of `docs/images/claude-code-image.svg`, regenerated from its source. `docs/design.md`, "`agentbox`: image, managed settings and launcher": a new point, "A tag is a name, not a version", which says the same and adds that the collection's default follows the collection version of the release that last changed the image.

- `dev/flatten-svg.py` and `dev/diagrams/`: each diagram now has a readable source, with classes and CSS custom properties, and the script turns it into the published file in `docs/images/`: light colours and fonts as attributes, solid tints, CSS only for the dark override. Python 3 standard library only. `docs/images/architecture.svg` is regenerated from its source; its elements are unchanged, only the order of its dark CSS rules differs. `dev/diagrams.md` describes the source and the published file, the rules for a source (no `<tspan>`, which ImageMagick lays out on top of the text before it), and the workflow.
- `docs/design.md`, "`agentbox`: image, managed settings and launcher": a second diagram, `docs/images/claude-code-image.svg`, of how Claude Code gets into a session. The pinned version and tag in the inventory, the root-owned recipe and its hash, when the role builds, keeps or fails, the build steps with the host each needs through Squid, the image storage with the old tag kept, the role's check of the image, the launcher with `--pull=never`, and the session where `dev` cannot update Claude Code; below, the four steps of an update, going back, and a forgotten tag bump. The README's "Updating Claude Code" links it. `dev/diagrams.md` covers both diagrams, with a layout grid for each.
- README, "What you get": links to the diagram `docs/images/architecture.svg` and to an interactive version of it on claude.ai, which explains each part when clicked and sends a request through the layers to show which one stops it.
- `dev/diagrams.md`: how the diagrams in `docs/images/` are made and changed. Why light colours are attributes and CSS holds only the dark override (CSS variables showed as black in librsvg viewers; ImageMagick ignores `fill-opacity`), the rules, the palette with its tints and how to compute a new one, the layout grid, and how to check a change with `xmllint` and ImageMagick. `.claude/CLAUDE.md` lists it as context.
- `docs/design.md`, "Why this stack": a diagram next to the ASCII tree, `docs/images/architecture.svg`. It shows the nested layers from the VM to Claude Code under bubblewrap, the four host paths mounted into the container, the only way out (pasta as uid `agent`, the nftables owner rule, Squid's allowlist, the NAT NIC) with where other traffic is rejected or answered 403, the account `ansible` reached over SSH on the host-only NIC, and the role that builds each part as its outline colour. A hand-written SVG with the light colours as attributes, so it renders in plain SVG viewers too, and a dark variant through `prefers-color-scheme`; the alt text describes it.
- `.claude/CLAUDE.md`: issues get a type (Feature, Bug or Task), not the labels `bug` or `enhancement`; labels only for what a type cannot say.
- README: new section "Starting and stopping the VM", listed in the table of contents. The VM does not start with the host; `provision` starts an existing VM that is off and waits for it, and needs the network for Debian's `SHA512SUMS`; or `VBoxManage startvm --type headless` followed by the playbook `wait`. Stopping with `VBoxManage controlvm <vm> acpipowerbutton`, and that a shutdown clears every `session` token.

#### Changed

- README, "Starting and stopping the VM": `acpipowerbutton` returns at once, and the guest powers off on its own some seconds later, minutes on a host that is swapping; a loop on `VBoxManage list runningvms` waits until the VM is off, instead of a single check, and `VBoxManage controlvm <vm> poweroff` is the hard way for a guest that never gets there. "Tuning the VM" uses the same loop.
- The first lint run's findings, none of which was a bug: `become: true` beside `become_user:` on seven tasks in `agentbox`, `egress_proxy` and `podman`, so they no longer depend on the play's `become`; `changed_when: true` on the image build, which runs only when the tag is missing, and on the handler `Migrate rootless Podman storage`; six lines over 120 columns rewrapped, in `playbooks/snapshot.yml`, `agentbox`'s `git_token.yml` and `virtualbox_vm`'s `preflight.yml`, where the host-only interface check names the interface once, as `_ifname`. No change in behaviour.
- README, "Updating Claude Code": the full command to apply an update, `ansible-playbook tutner.agent_sandbox.sandbox --tags agentbox`, run from the working directory, instead of only naming the tag; where the two values live (`group_vars/agent_sandbox.yml`); that the new image is built beside the old one and the next session runs it; and that it reaches every project on a VM, since a VM has one image for all of them, and every VM in the group whose values come from `group_vars`, with `--limit <vm>` to try one first. A running session keeps the old image until it ends. The sentence linking the diagram is no longer part of the last bullet about tag names. The same for allowing a host: the full command, `ansible-playbook tutner.agent_sandbox.sandbox --tags egress,agentbox`, instead of only the tags.

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
