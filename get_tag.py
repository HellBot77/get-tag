import argparse
import http.client
import json
import re
import subprocess
import sys
import time
import urllib.request

_RETRIES = 3


def _urlopen(url: str, __retries: int = _RETRIES) -> http.client.HTTPResponse:
    if _RETRIES == __retries:
        print(f"{url=}", file=sys.stderr)
    try:
        response = urllib.request.urlopen(url)
        assert 200 == response.status
        return response
    except BaseException:
        if __retries:
            sleep = 30 * (_RETRIES - __retries + 1)
            print(f"{sleep=}", file=sys.stderr)
            time.sleep(sleep)
            return _urlopen(url, __retries - 1)
        raise


def get_pip_versions_1(package: str) -> list[str]:
    process = subprocess.run(["pip", "install", f"{package}=="], capture_output=True)
    match = re.search(r"\(from versions: (.*)\)", process.stderr.decode())
    assert match
    return match.group(1).split(", ")


def get_pip_versions_2(package: str) -> list[str]:
    url = f"https://pypi.org/pypi/{package}/json"
    response = _urlopen(url)
    releases = json.loads(response.read())["releases"]
    return sorted(
        releases, key=lambda release: releases[release][0]["upload_time_iso_8601"]
    )


def get_pip_versions_3(package: str) -> list[str]:
    process = subprocess.run(
        ["pip", "index", "versions", package], capture_output=True, check=True
    )
    return process.stdout.decode().splitlines()[1][20:].split(", ")[::-1]


def get_pip_versions(package: str) -> list[str]:
    return get_pip_versions_2(package)


def get_pip_version_1(package: str) -> str:
    return get_pip_versions_1(package)[-1]


def get_pip_version_2(package: str) -> str:
    return get_pip_versions_2(package)[-1]


def get_pip_version_3(package: str) -> str:
    return get_pip_versions_3(package)[-1]


def get_pip_version_4(package: str) -> str:
    subprocess.check_call(["pip", "install", "--upgrade", package])
    process = subprocess.run(["pip", "freeze"], capture_output=True, check=True)
    for frozen in process.stdout.decode().splitlines():
        if frozen.startswith(f"{package}=="):
            return frozen[11:]
    raise AssertionError


def get_pip_version(package: str) -> str:
    return get_pip_version_2(package)


def get_go_versions(module: str) -> list[str]:
    process = subprocess.run(
        ["go", "list", "-json", "-m", "-versions", module],
        capture_output=True,
        check=True,
    )
    return json.loads(process.stdout)["Versions"]


def get_go_version(module: str) -> str:
    return get_go_versions(module)[-1]


def _get_repository_branch(repository: str) -> tuple[str, str]:
    if "#" not in repository:
        repository += ":"
    return tuple(repository.split(":", 1))  # type: ignore[return-value]


def _get_gh_repository_base_url(repository: str) -> tuple[str, str]:
    if "@" not in repository:
        repository += "@https://api.github.com"
    return tuple(repository.split("@", 1))  # type: ignore[return-value]


def get_gh_commit_versions(repository: str) -> list[str]:
    repository, base_url = _get_gh_repository_base_url(repository)
    repository, branch = _get_repository_branch(repository)
    url = f"{base_url}/repos/{repository}/commits?sha={branch}"
    response = _urlopen(url)
    return [result["sha"] for result in reversed(json.loads(response.read()))]


def get_gh_commit_version(repository: str) -> str:
    return get_gh_commit_versions(repository)[-1]


def get_gh_tags_versions(repository: str) -> list[str]:
    repository, base_url = _get_gh_repository_base_url(repository)
    url = f"{base_url}/repos/{repository}/tags"
    response = _urlopen(url)
    return [result["name"] for result in reversed(json.loads(response.read()))]


def get_gh_tag_version(repository: str) -> str:
    return get_gh_tags_versions(repository)[-1]


def get_gh_release_versions(repository: str) -> list[str]:
    repository, base_url = _get_gh_repository_base_url(repository)
    url = f"{base_url}/repos/{repository}/releases"
    response = _urlopen(url)
    return [result["tag_name"] for result in reversed(json.loads(response.read()))]


def get_gh_release_version(repository: str) -> str:
    return get_gh_release_versions(repository)[-1]


def _get_gl_repository(repository: str) -> int:
    if repository.isdigit():
        return int(repository)
    else:
        url = f"https://gitlab.com/api/v4/projects/{repository.replace('/', '%2F', 1)}"
        response = _urlopen(url)
        return json.loads(response.read())["id"]


def get_gl_commit_versions(repository: str) -> list[str]:
    repository, branch = _get_repository_branch(repository)
    url = f"https://gitlab.com/api/v4/projects/{_get_gl_repository(repository)}/repository/commits?ref_name={branch}"
    response = _urlopen(url)
    return [result["id"] for result in reversed(json.loads(response.read()))]


def get_gl_commit_version(repository: str) -> str:
    return get_gl_commit_versions(repository)[-1]


def get_docker_versions(repository: str) -> list[str]:
    url = f"https://hub.docker.com/v2/repositories/{repository}/tags"
    response = _urlopen(url)
    return [result["name"] for result in json.loads(response.read())["results"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("docker")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pip")
    group.add_argument("--go")
    group.add_argument("--gh-commit", "--git-commit")
    group.add_argument("--gh-tag", "--git-release")
    group.add_argument("--gh-release")
    group.add_argument("--gl-commit")
    args = parser.parse_args()
    tags = get_docker_versions(args.docker)
    if args.pip:
        tag = get_pip_version(args.pip)
    elif args.go:
        tag = get_go_version(args.go)
    elif args.gh_commit:
        tag = get_gh_commit_version(args.gh_commit)
    elif args.gh_tag:
        tag = get_gh_tag_version(args.gh_tag)
    elif args.gh_release:
        tag = get_gh_release_version(args.gh_release)
    elif args.gl_commit:
        tag = get_gl_commit_version(args.gl_commit)
    else:
        raise NotImplementedError
    if tag not in tags:
        print(f"tag={tag}")


if __name__ == "__main__":
    main()
