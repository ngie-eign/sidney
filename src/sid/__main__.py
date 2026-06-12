"""Sidney: an end-to-end script for migrating GitHub projects to Codeberg.

It's not sexy. It's kind of derpy... but it gets the job done.
"""

import argparse
import configparser
import getpass
import pathlib
import shutil
import subprocess
import sys
import urllib.parse
from shlex import quote as shq

import git
import requests


CB_URL_BASE = "https://codeberg.org"
GH_URL_BASE = "https://github.com"
MIGRATE_API_URL = "https://codeberg.org/api/v1/repos/migrate"


GH = shutil.which("gh")
RIPGREP = shutil.which("rg")
if not GH or not RIPGREP:
    sys.exit("Please install gh / ripgrep before using this tool.")


def sshify_url(url: str) -> str:
    """Convert an HTTP-based URI to a git+ssh one.

    Args:
        url: HTTP-based URI.

    Returns:
        The git+ssh version of `url`!

    """
    url_parts = urllib.parse.urlsplit(url)
    url_parts = url_parts._replace(scheme="git+ssh")
    netloc = url_parts.netloc
    url_parts = url_parts._replace(netloc=f"git@{netloc}")
    return urllib.parse.urlunsplit(url_parts)


def setup_codeberg_project(
    old_url: str,
    cb_repo_name: str,
    cb_username: str,
    gh_username: str,
    cb_password: str | None = None,
    gh_password: str | None = None,
) -> None:
    # Credit to:
    # https://dev.to/alanwest/how-to-actually-migrate-from-github-to-codeberg-without-losing-your-mind-33bf
    # for the API call, params, etc.
    #
    # This can also be found in more gross detail via
    # [swagger](https://codeberg.org/api/swagger#) :)
    data = {
        "auth_username": gh_username,
        "clone_addr": old_url,
        "repo_name": cb_repo_name,
        "repo_owner": cb_username,
        "service": "github",
        "mirror": False,
        "issues": True,
        "labels": True,
        "releases": True,
        "pull_requests": True,
        "wiki": True,
    }
    headers = {}
    if cb_password is not None:
        headers["Authorization"] = f"token {cb_password}"
    if gh_password is not None:
        data["auth_token"] = gh_password
    resp = requests.post(MIGRATE_API_URL, headers=headers, json=data, timeout=20)
    resp.raise_for_status()


def neuter_gh_project(repo_clone: pathlib.Path, old_url: str, new_url: str) -> None:
    new_description = "Project has migrated to Codeberg"
    command_set = [
        # fmt: skip
        [
            GH,
            "repo",
            "edit",
            "--description",
            new_description,
            "--homepage",
            new_url,
            old_url,
        ],
        [
            GH,
            "repo",
            "archive",
            "-y",
            old_url,
        ],
    ]
    for command in command_set:
        subprocess.call(command, cwd=str(repo_clone))


def convert_urls(repo_clone: pathlib.Path, old_url: str, new_url: str) -> None:
    subprocess.call(
        (
            f"{RIPGREP} -l {shq(old_url)} . | "
            f"xargs -n 1 sed -e 's,{shq(old_url)},{shq(new_url)},g' -i ''"
        ),
        cwd=str(repo_clone),
        shell=True,
    )


def change_mainline_to_cb(repo_clone: pathlib.Path, old_url: str, new_url: str) -> None:
    repo = git.Repo(str(repo_clone))
    # XXX: only do this for `old_url`.
    repo.remote("origin").set_url(sshify_url(new_url))


def main(argv: list[str] | None = None) -> None:

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--codeberg-project-name", help="Codeberg project name")
    argparser.add_argument("--codeberg-username", help="Codeberg username")
    argparser.add_argument("--codeberg-password", help="Codeberg password")
    argparser.add_argument(
        "--config-file",
        type=argparse.FileType("r"),
        help="Configuration file",
    )
    argparser.add_argument(
        "--clone-path",
        default=pathlib.Path.cwd(),
        type=pathlib.Path,
        help="Path to repo clone",
    )
    argparser.add_argument("--github-project-name", help="GitHub project name")
    argparser.add_argument("--github-username", help="GitHub username")
    argparser.add_argument("--github-password", help="GitHub password")

    args = argparser.parse_args(args=argv)

    cb_username = args.codeberg_username
    cb_password = args.codeberg_password
    gh_username = args.github_username
    gh_password = args.github_password
    if args.config_file:
        config = configparser.ConfigParser()
        config.read(args.config_file.name)
        cb_username = cb_username or config["codeberg"].get(
            "username",
            getpass.getuser(),
        )
        cb_password = cb_password or config["codeberg"].get("password")
        gh_username = gh_username or config["github"].get("username", getpass.getuser())
        gh_password = gh_password or config["github"].get("password")

    cb_project_name = args.codeberg_project_name or args.clone_path.name
    gh_project_name = args.github_project_name or args.clone_path.name

    cb_url = f"{CB_URL_BASE}/{cb_username}/{cb_project_name}"
    gh_url = f"{GH_URL_BASE}/{gh_username}/{gh_project_name}"

    repo_clone = pathlib.Path(args.clone_path)

    # 1. Migrate the project from GH to CB.
    setup_codeberg_project(
        gh_url,
        cb_project_name,
        cb_username,
        gh_username,
        cb_password=cb_password,
        gh_password=gh_password,
    )

    # 2. Switch the local mirror from GH to CB.
    change_mainline_to_cb(repo_clone, gh_url, cb_url)

    # 3. Convert URLs on the local filesystem to CB.
    convert_urls(repo_clone, gh_url, cb_url)

    # 4. Neuter the GH project: archive GH project and redirect folks to Codeberg.
    neuter_gh_project(repo_clone, gh_url, cb_url)


if __name__ == "__main__":
    main()
