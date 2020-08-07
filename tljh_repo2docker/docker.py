import json

from urllib.parse import urlparse

from aiodocker import Docker


async def list_images():
    """
    Retrieve local images built by repo2docker
    """
    async with Docker() as docker:
        r2d_images = await docker.images.list(
            filters=json.dumps({"dangling": ["false"], "label": ["repo2docker.ref"]})
        )
    images = [
        {
            "repo": image["Labels"]["repo2docker.repo"],
            "ref": image["Labels"]["repo2docker.ref"],
            "image_name": image["Labels"]["tljh_repo2docker.image_name"],
            "display_name": image["Labels"]["tljh_repo2docker.display_name"],
            "mem_limit": image["Labels"]["tljh_repo2docker.mem_limit"],
            "cpu_limit": image["Labels"]["tljh_repo2docker.cpu_limit"],
            "status": "built",
        }
        for image in r2d_images
        if "tljh_repo2docker.image_name" in image["Labels"]
            and "tljh_repo2docker.storage_for" not in image["Labels"]
    ]
    return images


async def find_storage(imagename=None):
    """
    Find appropiate storage image name for imagename
    """
    async with Docker() as docker:
        images = None if not imagename else await docker.images.list(
            filters=json.dumps({
                "dangling": ["false"],
                "label": ["tljh_repo2docker.storage_for=" + imagename]
            })
        )
        images = images if images else await docker.images.list(
            filters=json.dumps({
                "dangling": ["false"],
                "label": ["tljh_repo2docker.storage_for=ALL"]
            })
        )
    result = images[0] if images else None
    if not result:
        return None
    return result["Id"]


async def list_containers():
    """
    Retrieve the list of local images being built by repo2docker.
    Images are built in a Docker container.
    """
    async with Docker() as docker:
        r2d_containers = await docker.containers.list(
            filters=json.dumps({"label": ["repo2docker.ref"]})
        )
    containers = [
        {
            "repo": container["Labels"]["repo2docker.repo"],
            "ref": container["Labels"]["repo2docker.ref"],
            "image_name": container["Labels"]["repo2docker.build"],
            "display_name": container["Labels"]["tljh_repo2docker.display_name"],
            "mem_limit": container["Labels"]["tljh_repo2docker.mem_limit"],
            "cpu_limit": container["Labels"]["tljh_repo2docker.cpu_limit"],
            "status": "building",
        }
        for container in r2d_containers
        if "repo2docker.build" in container["Labels"]
    ]
    return containers


async def build_image(repo, ref, name="", memory=None, cpu=None):
    """
    Build an image given a repo, ref and limits
    """
    ref = ref or "master"
    if len(ref) >= 40:
        ref = ref[:7]

    # default to the repo name if no name specified
    # and sanitize the name of the docker image
    name = name or urlparse(repo).path.strip("/")
    name = name.lower().replace("/", "-")
    image_name = f"{name}:{ref}"

    # memory is specified in GB
    memory = f"{memory}G" if memory else ""
    cpu = cpu or ""

    # add extra labels to set additional image properties
    labels = [
        f"LABEL tljh_repo2docker.display_name={name}",
        f"LABEL tljh_repo2docker.image_name={image_name}",
        f"LABEL tljh_repo2docker.mem_limit={memory}",
        f"LABEL tljh_repo2docker.cpu_limit={cpu}",
    ]
    cmd = [
        "jupyter-repo2docker",
        "--ref",
        ref,
        "--user-name",
        "jovyan",
        "--user-id",
        "1100",
        "--no-run",
        "--image-name",
        image_name,
        "--appendix",
        "\n".join(labels),
        repo,
    ]
    async with Docker() as docker:
        await docker.containers.run(
            config={
                "Cmd": cmd,
                "Image": "jupyter/repo2docker:master",
                "Labels": {
                    "repo2docker.repo": repo,
                    "repo2docker.ref": ref,
                    "repo2docker.build": image_name,
                    "tljh_repo2docker.display_name": name,
                    "tljh_repo2docker.mem_limit": memory,
                    "tljh_repo2docker.cpu_limit": cpu,
                },
                "Volumes": {
                    "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw",}
                },
                "HostConfig": {"Binds": ["/var/run/docker.sock:/var/run/docker.sock"],},
                "Tty": False,
                "AttachStdout": False,
                "AttachStderr": False,
                "OpenStdin": False,
            }
        )
