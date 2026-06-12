# Sidney

An end-to-end tool for migrating a repo from GitHub to Codeberg.

Named after the lovable, but derpy character from Ice Age: [Sidney (or Sid for short)](https://iceage.fandom.com/wiki/Sid).

# Requirements

## Python dependencies
- python 3.10+
- GitPython (>=3.1.4)
- requests (~=2.34.0)
- setuptools-scm (build only)

## Standalone commands
- gh
- ripgrep

# Installation

```
pipx install .
```

# Setup

In order to use this tool, you must create an access token for Codeberg that
has the following permissions:
- write:organization
- write:repository
- write:user

See [Generating an Access Token](https://docs.codeberg.org/advanced/access-token/) for more details.

# Usage

Use `sid --help` to get a better idea of how to use the tool on the command-line.

## Recommendations

- Run it from the project directory for simplicity.
- Provide a config file instead of specifying all of the arguments on the
  command-line.

## Config File

Many command line parameters can be specified in a .ini file, which can be read
in by `sid` using the `--config-file` flag:

```
[codeberg]
username = ...
password = ...

[github]
username = ...
```

- `github:password` is technically only required if you need to access private
  repos.
- Technically `password` should be token, but meh.. whatever.

Providing a config file avoids the need for having to specify a bunch of
[repeat] secrets on the command-line.
