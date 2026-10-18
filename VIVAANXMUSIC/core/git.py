import asyncio
import shlex
from typing import Tuple

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

import config

from ..logging import LOGGER
from ..security import build_subprocess_env


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=build_subprocess_env(),
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    return asyncio.get_event_loop().run_until_complete(install_requirements())


def git():
    REPO_LINK = config.UPSTREAM_REPO
    if config.GIT_TOKEN:
        GIT_USERNAME = REPO_LINK.split("com/")[1].split("/")[0]
        TEMP_REPO = REPO_LINK.split("https://")[1]
        UPSTREAM_REPO = f"https://{GIT_USERNAME}:{config.GIT_TOKEN}@{TEMP_REPO}"
    else:
        UPSTREAM_REPO = config.UPSTREAM_REPO
    try:
        # Heroku/container deployments commonly receive a source archive/slug
        # without the .git directory. Do not initialize a fake repository and
        # attempt an interactive GitHub fetch during application startup.
        repo = Repo(search_parent_directories=True)
        LOGGER(__name__).info("Git repository found; checking upstream updater.")
    except InvalidGitRepositoryError:
        LOGGER(__name__).warning(
            "Git updater skipped: this deployment has no .git metadata. "
            "Deploy updates through your hosting provider instead."
        )
        return
    except GitCommandError as exc:
        LOGGER(__name__).warning("Git updater skipped due to Git error: %s", exc)
        return

    try:
        origin = repo.remote("origin")
        # Use the configured upstream URL, including the configured token if
        # supplied, rather than trusting a stale/private URL in the deployment.
        if origin.url != UPSTREAM_REPO:
            origin.set_url(UPSTREAM_REPO)
        origin.fetch(config.UPSTREAM_BRANCH)
        if config.UPSTREAM_BRANCH not in [head.name for head in repo.heads]:
            if f"origin/{config.UPSTREAM_BRANCH}" not in [ref.name for ref in repo.refs]:
                LOGGER(__name__).warning(
                    "Git updater skipped: upstream branch '%s' was not found.",
                    config.UPSTREAM_BRANCH,
                )
                return
            repo.create_head(config.UPSTREAM_BRANCH, f"origin/{config.UPSTREAM_BRANCH}")
        branch = repo.heads[config.UPSTREAM_BRANCH]
        branch.set_tracking_branch(origin.refs[config.UPSTREAM_BRANCH])
        branch.checkout(True)
        try:
            branch.pull(config.UPSTREAM_BRANCH)
        except GitCommandError:
            repo.git.reset("--hard", "FETCH_HEAD")
        install_req("pip3 install --no-cache-dir -r requirements.txt")
        LOGGER(__name__).info("Fetching updates from upstream repository...")
    except GitCommandError as exc:
        LOGGER(__name__).warning(
            "Git updater could not fetch updates; continuing startup: %s", exc
        )
