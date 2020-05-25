import pytest

from aiodocker import Docker, DockerError

from .utils import add_environment, wait_for_image, remove_environment


@pytest.mark.asyncio
async def test_add_environment(app, remove_test_image, minimal_repo, image_name):
    name, ref = image_name.split(":")
    r = await add_environment(app, repo=minimal_repo, name=name, ref=ref)
    assert r.status_code == 200
    image = await wait_for_image(image_name=image_name)
    assert (
        image["ContainerConfig"]["Labels"]["tljh_repo2docker.image_name"] == image_name
    )


@pytest.mark.asyncio
async def test_delete_environment(app, remove_test_image, minimal_repo, image_name):
    name, ref = image_name.split(":")
    await add_environment(app, repo=minimal_repo, name=name, ref=ref)
    await wait_for_image(image_name=image_name)
    r = await remove_environment(app, image_name=image_name)
    assert r.status_code == 200

    # make sure the image does not exist anymore
    docker = Docker()
    with pytest.raises(DockerError):
        await docker.images.inspect(image_name)
    await docker.close()


@pytest.mark.asyncio
async def test_delete_unknown_environment(app, remove_test_image):
    r = await remove_environment(app, image_name="image-not-found:12345")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_no_repo(app):
    r = await add_environment(app, repo="")
    assert r.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "memory, cpu", [("abcded", ""), ("", "abcde"),],
)
async def test_wrong_limits(app, minimal_repo, memory, cpu):
    r = await add_environment(app, repo=minimal_repo, memory=memory, cpu=cpu)
    assert r.status_code == 400
    assert "must be a number" in r.text


@pytest.mark.asyncio
async def test_wrong_name(app, minimal_repo):
    r = await add_environment(app, repo=minimal_repo, name="#WRONG_NAME#")
    assert r.status_code == 400
