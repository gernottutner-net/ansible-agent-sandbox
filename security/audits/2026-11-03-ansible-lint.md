# Passed, With Seventeen Advisories

Socket Firewall allowed every package in `ansible-lint`'s tree, and the tree still
carries seventeen published advisories. Both results are correct. They answer different
questions.

| | |
|---|---|
| Target | `ansible-lint` 26.10.1, as a pipx install would resolve it |
| Question | Is it safe to install `ansible-lint` with pipx, and what does a Socket Firewall pass establish? |
| Date | 2026-11-03 |
| Instruments | sfw 2.0.6 (Socket Firewall Free) · OSV API (`api.osv.dev`) · the script in [the appendix](#appendix-the-osv-check-script) · pipx 1.0.0 |
| Runtime | Python 3.10.12 (the only interpreter on the audit machine) · pip 22.0.2 for the download |
| Installed | Nothing. The tree was downloaded as wheels and never unpacked or run |

## Table of Contents

- [Summary](#summary)
- [Method](#method)
- [Socket Firewall: 31 of 31 allowed](#socket-firewall-31-of-31-allowed)
- [OSV: one package, seventeen advisories](#osv-one-package-seventeen-advisories)
  - [Why pip chose the vulnerable version](#why-pip-chose-the-vulnerable-version)
- [Which advisories ansible-lint can reach](#which-advisories-ansible-lint-can-reach)
  - [Where the lock file lives](#where-the-lock-file-lives)
- [The Socket package page](#the-socket-package-page)
- [Lessons for install gating](#lessons-for-install-gating)
- [Recommendations, ranked](#recommendations-ranked)
- [The resolved tree](#the-resolved-tree)
- [Appendix: the OSV check script](#appendix-the-osv-check-script)

## Summary

- **Malware: none known.** `sfw` checked all 31 packages and allowed every one, with no
  warning. This held on two separate downloads.
- **Known vulnerabilities: 17, all in `filelock` 4.1.0** (1 high, 12 moderate, 4 low).
  All 17 are fixed in 4.2.1. pip picked 4.1.0 because 4.2.1 needs Python 3.11 or newer,
  and the audit machine has 3.10.
- **Reachable: one moderate advisory, in one setup.** ansible-lint uses filelock for a
  single plain lock file. On Linux, only
  [GHSA-69hj-f68j-2879](https://osv.dev/vulnerability/GHSA-69hj-f68j-2879) applies to
  that lock type. Exploiting it needs another local user who can write to the cache
  folder. That happens only when ansible-compat falls back to a shared `/tmp` folder.
- **For a single-user machine, practical risk is close to zero.** On shared hosts and
  shared CI runners it is a real moderate issue. The clean fix is a Python 3.11+
  interpreter for the pipx install.
- **A Socket Firewall pass is not a vulnerability check.** Nothing in a typical
  pipx install path would have shown these 17 advisories.

## Method

The tree was downloaded through the firewall without installing it. Wheels only, so no
package's build or setup code ran. The cache was off, so every file was fetched over
the network and seen by `sfw`:

```sh
python3 -m venv ./venv
SFW_DEBUG=true sfw ./venv/bin/pip download --no-cache-dir --only-binary=:all: \
  -d ./dl ansible-lint
python3 -I osv-check.py ./dl
```

`SFW_DEBUG=true` makes `sfw` log one event per package, with the verdict and any warning
types. The [OSV check script](#appendix-the-osv-check-script) reads each wheel's name and
exact version from its file name and sends the whole list to OSV in one batch query.
It then fetches each advisory's severity, aliases and fixed versions. Reachability was
judged by reading the `ansible-lint` and `ansible-compat` wheels' source.

Before this, `sfw pipx install cowsay` into a throwaway pipx home established that
wrapping pipx works. All six PyPI downloads (the app plus pipx's own `pip`,
`setuptools`, `wheel` and `packaging`) were logged as `packageAllowed`. pipx downloads
through pip, which `sfw` supports. Socket does not list pipx itself as supported.

**A wrong turn worth recording.** A first OSV query used version numbers that were
guessed rather than read from the resolved tree. It reported advisories for
`cryptography` and `black`. The real versions (50.0.2 and 26.10.1) have none. Query
only the versions pip actually resolved.

**Resolver caveat.** The download used the venv's bundled pip 22.0.2. pipx resolves with
its own newer pip, which could pick different versions in places. For `filelock`, the
deciding constraint is `requires_python`, which does not depend on the pip version.

## Socket Firewall: 31 of 31 allowed

| Event | Count |
|---|---|
| `packageAllowed` | 31 |
| `hasWarning: true` | 0 |
| `packageBlocked` | 0 |

Every fetch went to `files.pythonhosted.org` and was classified as `registryType: 'pypi'`.

What this establishes is narrow. The free firewall blocks confirmed malware and warns
on AI-flagged suspicion. It does not check known vulnerabilities, what the code is
capable of, maintenance or licences. A clean pass means *"not known to be malware"*. It
does not mean *"safe"*.

## OSV: one package, seventeen advisories

30 of the 31 packages have no advisory at their resolved version. `ansible-lint` has
never had one. `ansible-core` has 14 advisories in its history, and none affects
2.16.20.

`filelock` 4.1.0 has 17, all fixed in 4.2.1:

| Advisory | CVE | Severity | Lock type affected |
|---|---|---|---|
| [GHSA-v4x8-3wr5-3wq8](https://osv.dev/vulnerability/GHSA-v4x8-3wr5-3wq8) | CVE-2026-112940 | High | `ReadWriteLock` |
| [GHSA-69hj-f68j-2879](https://osv.dev/vulnerability/GHSA-69hj-f68j-2879) | CVE-2026-112909 | Moderate | **`UnixFileLock`** |
| [GHSA-2g95-wg33-c5x2](https://osv.dev/vulnerability/GHSA-2g95-wg33-c5x2) | CVE-2026-112906 | Moderate | `SoftFileLock` |
| [GHSA-crv4-6mhj-j5jh](https://osv.dev/vulnerability/GHSA-crv4-6mhj-j5jh) | CVE-2026-112914 | Moderate | `SoftFileLock` |
| [GHSA-fq56-3cx3-fjxp](https://osv.dev/vulnerability/GHSA-fq56-3cx3-fjxp) | CVE-2026-112935 | Moderate | `SoftFileLock` |
| [GHSA-rfpc-qcw5-3pc4](https://osv.dev/vulnerability/GHSA-rfpc-qcw5-3pc4) | CVE-2026-112939 | Moderate | `SoftFileLock` |
| [GHSA-6627-m3xw-93mp](https://osv.dev/vulnerability/GHSA-6627-m3xw-93mp) | CVE-2026-112908 | Moderate | `StrictSoftFileLock` |
| [GHSA-9c4x-gm8v-wgc4](https://osv.dev/vulnerability/GHSA-9c4x-gm8v-wgc4) | CVE-2026-112911 | Moderate | `StrictSoftFileLock` |
| [GHSA-m462-7rxw-wvpg](https://osv.dev/vulnerability/GHSA-m462-7rxw-wvpg) | CVE-2026-112938 | Moderate | `StrictSoftFileLock` |
| [GHSA-fj95-fr6c-h845](https://osv.dev/vulnerability/GHSA-fj95-fr6c-h845) | CVE-2026-112934 | Moderate | `SoftReadWriteLock` |
| [GHSA-cwqr-hh33-gh44](https://osv.dev/vulnerability/GHSA-cwqr-hh33-gh44) | CVE-2026-112915 | Moderate | `ReadWriteLock` |
| [GHSA-jqc4-5cvw-7w85](https://osv.dev/vulnerability/GHSA-jqc4-5cvw-7w85) | CVE-2026-112937 | Moderate | `ReadWriteLock` |
| [GHSA-8mx5-7m5m-r77g](https://osv.dev/vulnerability/GHSA-8mx5-7m5m-r77g) | CVE-2026-112910 | Moderate | `WindowsFileLock` |
| [GHSA-9j6q-wvj5-jgjg](https://osv.dev/vulnerability/GHSA-9j6q-wvj5-jgjg) | CVE-2026-112912 | Low | `SoftFileLock` |
| [GHSA-wfhq-q4j2-c37m](https://osv.dev/vulnerability/GHSA-wfhq-q4j2-c37m) | CVE-2026-112941 | Low | `SoftReadWriteLock` |
| [GHSA-567q-5qvw-pf92](https://osv.dev/vulnerability/GHSA-567q-5qvw-pf92) | CVE-2026-112907 | Low | `SoftFileLock`, Windows only |
| [GHSA-9vhv-jxww-xfm5](https://osv.dev/vulnerability/GHSA-9vhv-jxww-xfm5) | CVE-2026-112913 | Low | `ReadWriteLock`, Windows only |

The last column was assigned from each advisory's summary, not from a full reading of
every advisory.

### Why pip chose the vulnerable version

| `filelock` | `requires_python` |
|---|---|
| 4.1.0 | `>=3.10` |
| 4.2.1 | `>=3.11` |

`ansible-lint` asks only for `filelock>=3.8.2`. On Python 3.10, pip drops 4.2.1 without
a word and takes the newest version that still installs. Neither pip nor `sfw` reports
that the newest version was skipped for a fixed one. So the interpreter version decides
the security outcome, and nothing in the install output shows it.

## Which advisories ansible-lint can reach

Of everything in the tree, only `ansible-lint` imports `filelock`, and it uses it in one
place (`ansiblelint/__main__.py:161`):

```python
cache_dir_lock = FileLock(
    f"{options.cache_dir}/.lock",
)
```

On Linux, `FileLock` is `UnixFileLock`. The lock is taken only when a cache folder is set
and ansible-lint is not in offline mode. It uses no soft, strict, read-write or Windows
lock. That leaves one advisory:

**GHSA-69hj-f68j-2879 (moderate).** `UnixFileLock` truncates and changes the permissions
of any regular file that another user renames or hard-links onto the lock path. An
attacker needs write access to the folder that holds `.lock`.

### Where the lock file lives

`ansible_compat/prerun.py:52` (`get_cache_dir`) picks the folder in this order:

1. `$VIRTUAL_ENV/.ansible`, if a virtual environment is active and writable.
2. `<project>/.ansible`, in the default isolated mode, if the project folder is
   writable. This overrides 1.
3. `$ANSIBLE_HOME`, or `~/.ansible`, when not isolated.
4. **Otherwise `/tmp/.ansible-<4 hex chars>`.** The suffix is the first four hex digits of
   the SHA-256 of the project path. The folder is created with `exist_ok=True`.

Cases 1 to 3 are folders only you can write to, so the advisory cannot be exploited.
Case 4 is the exact precondition the advisory describes. `/tmp` is writable by every
user, the name follows from a known project path, and only 65,536 names are possible.
And a folder another user created in advance is reused without any check. Case 4 is
reached when the project folder is not writable and no virtual environment is active.
Examples are linting a checkout owned by someone else, or a read-only mount in CI.

This is a reading of the code, not a published advisory against `ansible-compat`, and
it was not exploited or tested.

## The Socket package page

`https://socket.dev/pypi/package/ansible-lint` looked like "a security fiasco" to the
person who requested this audit. It refused automated requests (HTTP 403) during the
audit, so its alerts were not seen and are not assessed here.

The difference from the firewall result is structural, not a contradiction. A package
page shows all of Socket's alert categories across the package and its dependencies.
These include capability alerts (shell, network, filesystem, environment access, dynamic
code), known vulnerabilities, and quality, maintenance and licence signals. For a tool
whose job is to run Ansible, capability alerts are expected and say little on their
own. None of those categories makes the free firewall block or warn. A follow-up should
sort the page's actual alerts into "expected for this tool", "a known vulnerability at
the resolved versions" (so far, only the `filelock` set above), and "worth a closer
look".

## Lessons for install gating

These apply to any setup that tries to force package installs through Socket Firewall,
for example a hook or wrapper that rejects unwrapped package-manager commands:

1. **Include `pipx`.** A gate that matches `pip`, `uv` and the npm family but not `pipx`
   lets `pipx install ansible-lint` through without `sfw`. `pipx run` is worse: it
   downloads and executes in one step, and it carries no `install` verb for a matcher
   to find.
2. **Include `uvx` and `uv tool run`.** These are the other common way to run a Python
   tool straight from PyPI, and they have the same download-and-execute shape.
   `uv tool install` is caught by any matcher that looks for `install`.
3. **Don't treat an `sfw` pass as "safe".** "Protected by Socket Firewall" reads as an
   all-clear, but it only rules out known malware. On the PyPI path, add a
   known-vulnerability check (an OSV query such as the
   [appendix script](#appendix-the-osv-check-script), or `pip-audit`). npm-only tools
   like `npm audit` do not cover it.

## Recommendations, ranked

1. **Install with Python 3.11 or newer**, so pip resolves `filelock` 4.2.1 and all 17
   advisories drop out:
   `SFW_DEBUG=true PIP_NO_CACHE_DIR=1 sfw pipx install --python python3.11 ansible-lint`.
   No such interpreter was on the audit machine.
2. **If you stay on 3.10, keep the cache out of `/tmp`.** Run ansible-lint from a project
   folder you own and can write to, or with a writable virtual environment active. On a
   single-user machine this is the normal case, and the remaining risk is negligible.
   On shared hosts and CI runners, check for the `Using unique temporary directory`
   warning. It means case 4 was reached.
3. **Always install through `sfw` with the cache off** (`PIP_NO_CACHE_DIR=1`). Packages
   already in pip's cache are installed without a network request, so the firewall
   never sees them.
4. **Close the install-gating gaps** listed in
   [Lessons for install gating](#lessons-for-install-gating).
5. **Consider reporting the `/tmp` fallback to `ansible-compat`.** A predictable,
   reusable folder in a world-writable location is a weakness on its own. The `filelock`
   advisory is just one way to exploit it. Not done.

## The resolved tree

31 wheels, as resolved for CPython 3.10 on x86-64 Linux:

| Package | Version | OSV advisories |
|---|---|---|
| `ansible-lint` | 26.10.1 | 0 |
| `ansible-compat` | 26.10.0 | 0 |
| `ansible-core` | 2.16.20 | 0 |
| `attrs` | 26.1.0 | 0 |
| `black` | 26.10.1 | 0 |
| `bracex` | 3.1 | 0 |
| `cffi` | 2.1.1 | 0 |
| `click` | 8.5.0 | 0 |
| `cryptography` | 50.0.2 | 0 |
| `distro` | 1.9.0 | 0 |
| **`filelock`** | **4.1.0** | **17** |
| `jinja2` | 3.1.6 | 0 |
| `jsonschema` | 4.26.0 | 0 |
| `jsonschema-specifications` | 2025.9.1 | 0 |
| `markupsafe` | 3.0.4 | 0 |
| `mypy-extensions` | 1.2.0 | 0 |
| `packaging` | 26.3 | 0 |
| `pathspec` | 1.1.1 | 0 |
| `platformdirs` | 4.12.4 | 0 |
| `pycparser` | 3.11 | 0 |
| `pytokens` | 0.4.1 | 0 |
| `pyyaml` | 6.0.3 | 0 |
| `referencing` | 0.37.0 | 0 |
| `resolvelib` | 1.0.1 | 0 |
| `rpds-py` | 0.30.0 | 0 |
| `ruamel-yaml` | 0.19.1 | 0 |
| `subprocess-tee` | 0.4.2 | 0 |
| `tomli` | 2.5.0 | 0 |
| `typing-extensions` | 4.16.0 | 0 |
| `wcmatch` | 11.1 | 0 |
| `yamllint` | 1.38.0 | 0 |

`ansible-core` is held at the 2.16 line by two constraints together. Python 3.10 rules
out 2.18 and newer, which need 3.11 or later. And `ansible-lint` and `ansible-compat`
both require `ansible-core!=2.17.*,>=2.16.19`, which rules out 2.17. No advisory
affects 2.16.20, but the line's support window is worth checking separately.

## Appendix: the OSV check script

The script used for the OSV results above. It needs only the Python standard library.
Save it as `osv-check.py` and run it against a folder of downloaded wheels, as shown in
[Method](#method).

Limits: it expects wheel files only, since it reads name and version from the file
name. It reports advisories, not whether the affected code is actually used. It always
exits 0, so it can't serve as a pass/fail gate as written.

```python
#!/usr/bin/env python3
# Known-vulnerability check for a folder of downloaded PyPI wheels, against OSV.
import json, os, sys, urllib.request
d = sys.argv[1]
pkgs = []
for f in sorted(os.listdir(d)):
    n, v = f.split("-")[:2]
    pkgs.append((n.replace("_", "-").lower(), v))
def post(url, body):
    r = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "osv-check"})
    return json.load(urllib.request.urlopen(r, timeout=60))
res = post("https://api.osv.dev/v1/querybatch",
           {"queries": [{"package": {"ecosystem": "PyPI", "name": n}, "version": v} for n, v in pkgs]})["results"]
hits = 0
for (n, v), r in zip(pkgs, res):
    ids = [x["id"] for x in r.get("vulns", [])]
    print(f"{n:28} {v:12} {len(ids)}")
    for i in ids:
        hits += 1
        x = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.osv.dev/v1/vulns/{i}", headers={"User-Agent": "osv-check"}), timeout=60))
        sev = (x.get("database_specific") or {}).get("severity", "")
        fixed = sorted({e["fixed"] for a in x.get("affected", []) for rg in a.get("ranges", []) for e in rg.get("events", []) if "fixed" in e})
        print(f"    {i}  {sev}  aliases={x.get('aliases', [])}  fixed={fixed}\n      {x.get('summary', '')[:110]}")
print(f"\n{len(pkgs)} packages, {hits} advisories")
```
