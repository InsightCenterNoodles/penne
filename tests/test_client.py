
import threading
import asyncio
import logging

import pytest

from rigatoni import Server, StartingComponent, Method
from penne import Client
from penne.handlers import handle

from delegates import TableDelegate


logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG
)


def print_method():
    print("Method on server called!")


starting_components = [
    StartingComponent(Method, {"name": "print", "arg_doc": []}, print_method)
]


@pytest.fixture
def rig_base_server():

    with Server(50000, starting_components) as server:
        yield server

    # t = threading.Thread(target=run_test_server)
    # t.start()
    # asyncio.run(asyncio.sleep(1))  # Pause to let server set up
    # yield t
    # shutdown_server()
    # t.join()
    # asyncio.run(asyncio.sleep(.5))  # Pause to let server shut down


@pytest.fixture
def base_client(rig_base_server):

    with Client("ws://localhost:50000", strict=True) as client:
        yield client

    # client = create_client("ws://localhost:50000", strict=True)
    # asyncio.run(asyncio.sleep(1))  # Pause to let the client connect
    # yield client
    # print(f"Socket: {client._socket}")
    # client.shutdown()
    # client.thread.join(timeout=5)


@pytest.fixture
def delegate_client(rig_base_server):
    with Client("ws://localhost:50000", custom_delegate_hash={"tables": TableDelegate}, strict=True) as client:
        yield client

    # client = create_client("ws://localhost:50000", {"tables": TableDelegate}, strict=True)
    # asyncio.run(asyncio.sleep(1))  # Pause to let the client connect
    # yield client
    # client.shutdown()
    # client.thread.join(timeout=5)


def test_create_client(base_client):
    assert isinstance(base_client, Client)
    assert "document" in base_client.state
    assert base_client.is_active is True
    assert base_client.callback_queue.empty()
    assert len(base_client.delegates) == 14
    assert len(base_client.server_messages) == 36


def test_create_delegate_client(delegate_client):
    assert isinstance(delegate_client, Client)
    assert "document" in delegate_client.state
    assert delegate_client.is_active is True
    assert delegate_client.callback_queue.empty()
    assert len(delegate_client.delegates) == 14
    assert len(delegate_client.server_messages) == 36
    assert delegate_client.delegates["tables"] == TableDelegate
