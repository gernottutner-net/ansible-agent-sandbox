# Linting

How the collection's YAML is checked with `yamllint` and `ansible-lint`,
what their configs leave out and why, and how to install them. Both pass
on `main`; a release needs them to pass, see
[docs/release-tests.md](../docs/release-tests.md#before).

---

## Contents

- [Running them](#running-them)
- [What they check](#what-they-check)
- [The configs](#the-configs)
  - [Line length](#line-length)
  - [Skipped rules](#skipped-rules)
- [Installing them](#installing-them)

---

## Running them

From the repository root:

```bash
ansible-lint
yamllint roles playbooks examples meta galaxy.yml
```

Both must end without findings: ansible-lint with `Passed: 0 failure(s),
0 warning(s)` and `Profile 'production' was required, and it passed`,
yamllint with no output and exit code 0.

ansible-lint installs the collection from the working tree into
`.ansible/` in the repository, which `.gitignore` leaves out, and keeps
its cache there. If the collection is also installed under
`~/.ansible/collections`, it warns that another version of
`tutner.agent_sandbox` was found. That does not change the result: it
lints the files in the working tree.

## What they check

- **yamllint:** YAML as YAML: syntax, indentation, line length, truthy
  values, octal values, braces, comments. It knows nothing about Ansible.
- **ansible-lint:** playbooks, roles, `galaxy.yml` and `meta/runtime.yml`
  against Ansible's rules, at the strictest profile, `production`:
  modules by their full name, `changed_when` on commands, `become_user`
  with `become` beside it, names on tasks, and more. It runs yamllint's
  rules too, with the same config.

## The configs

`.yamllint` and `.ansible-lint` in the repository root. ansible-lint
leaves out `.claude/`, `.vscode/`, `.ansible/`, `docs/`, `dev/` and
`security/`: none of them holds Ansible content.

### Line length

120 columns, not yamllint's default of 80. The comments are wrapped near
80 columns; what runs longer is Jinja expressions, `argv` entries and
conditions, which read better on one line than split mid-expression. At
80, the first run found 106 lines; at 120, six, which were rewrapped.

### Skipped rules

| Rule | Why |
|---|---|
| `var-naming[no-role-prefix]` | The variable names are part of the interface. `sandbox_user` and `egress_allowlist` are shared by several roles, and `vm_` is the documented prefix of `virtualbox_vm`. Role prefixes would break every inventory. |
| `name[template]` | Task names in `virtualbox_vm` start with `[{{ vm_name }}]`, so the output shows, with several VMs, which VM a task ran for. |
| `galaxy[no-changelog]` | The changelog is `CHANGES.md`, which the rule does not recognise, and the collection is never published to Galaxy. |

A new skip needs its reason in `.ansible-lint` and in this table. A
finding in a single place is fixed, or marked with a `# noqa: <rule>`
comment and its reason on that line.

## Installing them

Neither is needed to use the collection; they are tools for working on
it. On Ubuntu 22.04, from apt and from PyPI through pipx, for every user:

```bash
sudo apt install yamllint pipx
sudo PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install ansible-lint
```

- apt's own `ansible-lint` (5.4.0) is too old: it predates ansible-core
  2.17 and the profiles. apt's `yamllint` (1.26.3) is fine;
  ansible-lint brings a newer one of its own.
- Do not pin ansible-core 2.17 into ansible-lint's virtualenv:
  ansible-lint 26.10.1 requires `ansible-core!=2.17.*` and refuses to run
  with it. On Python 3.10 it gets 2.16, while the playbooks run with
  whatever ansible-core the system has. The lint rules do not depend on
  that difference.
- `sudo pip install` would mix PyPI packages into the Python apt manages.

An audit of what that install pulls in, through Socket Firewall and
against OSV, is in
[security/audits/2026-11-03-ansible-lint.md](../security/audits/2026-11-03-ansible-lint.md).
On Python 3.10 the tree holds `filelock` 4.1.0 with 17 published
advisories; one is reachable, and only when ansible-lint's cache falls
back to `/tmp`, which it does not when run from a checkout you own.
