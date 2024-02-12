import argparse
import json
import re
import subprocess
import urllib.request

_RE_PIP_VERSIONS_1 = re.compile(r"\(from versions: (.*)\)")


def get_pip_versions_1(package: str) -> list[str]:
    process = subprocess.run(["pip", "install", f"{package}=="], capture_output=True)
    if match := _RE_PIP_VERSIONS_1.search(process.stderr.decode()):
        return match.group(1).split(", ")


def get_pip_versions_2(package: str) -> list[str]:
    url = f"https://pypi.org/pypi/{package}/json"
    response = urllib.request.urlopen(url)
    assert 200 == response.status
    return list(json.loads(response.read())["releases"])


def get_pip_versions_3(package: str) -> list[str]:
    process = subprocess.run(
        ["pip", "index", "versions", package], capture_output=True, check=True
    )
    return process.stdout.decode().splitlines()[1][20:].split(", ")[::-1]


def get_pip_versions(package: str) -> list[str]:
    return get_pip_versions_1(package)


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
    raise ModuleNotFoundError()


def get_pip_version(package: str) -> str:
    return get_pip_version_1(package)


def get_go_versions(module: str) -> list[str]:
    process = subprocess.run(
        ["go", "list", "-json", "-m", "-versions", module],
        capture_output=True,
        check=True,
    )
    return json.loads(process.stdout)["Versions"]


def get_go_version(module: str) -> str:
    return get_go_versions(module)[-1]


def get_gh_commit_versions(repository: str) -> list[str]:
    if "?" not in repository:
        repository += "?"
    repository, branch = repository.split("?", 1)
    url = f"https://api.github.com/repos/{repository}/commits?sha={branch}"
    response = urllib.request.urlopen(url)
    assert 200 == response.status
    return [result["sha"] for result in json.loads(response.read())][::-1]


def get_gh_commit_version(repository: str) -> str:
    return get_gh_commit_versions(repository)[-1]


def get_gh_release_versions(repository: str) -> list[str]:
    url = f"https://api.github.com/repos/{repository}/tags"
    response = urllib.request.urlopen(url)
    assert 200 == response.status
    return [result["name"] for result in json.loads(response.read())][::-1]


def get_gh_release_version(repository: str) -> str:
    return get_gh_release_versions(repository)[-1]


def get_docker_versions(repository: str) -> list[str]:
    url = f"https://hub.docker.com/v2/repositories/{repository}/tags"
    response = urllib.request.urlopen(url)
    assert 200 == response.status
    return [result["name"] for result in json.loads(response.read())["results"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repository")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pip")
    group.add_argument("--go")
    group.add_argument("--gh-commit", "--git-commit")
    group.add_argument("--gh-release", "--git-release")
    args = parser.parse_args()
    deployed = get_docker_versions(args.repository)
    if args.pip:
        tag = get_pip_version(args.pip)
    elif args.go:
        tag = get_go_version(args.go)
    elif args.gh_commit:
        tag = get_gh_commit_version(args.gh_commit)
    elif args.gh_release:
        tag = get_gh_release_version(args.gh_release)
    else:
        raise ValueError()
    if tag not in deployed:
        print(f"tag={tag}")


if __name__ == "__main__":
    main()
