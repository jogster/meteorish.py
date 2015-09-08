import asyncio
import ddpserver
import json
import datetime
from nose.tools import (assert_equal, assert_raises, assert_true,
                        assert_is_none, assert_false, with_setup,
                        assert_in, assert_not_in)
from unittest import mock


def setup_socket_message():
    global loop, server, socket, session
    loop = asyncio.get_event_loop()
    server = ddpserver.DDPServer(loop=loop)
    socket = mock.Mock()
    session = ddpserver.DDPSession(server, "1", socket, loop)


def next_tick():
    loop.run_until_complete(asyncio.coroutine(lambda: None)())


@with_setup(setup_socket_message)
def test_session_send():
    session.send({
        "msg": "connected",
        "session": "TeStSeSsIoNiD",
        })
    (out_msg, ), _ = socket.send.call_args
    out_msg = json.loads(out_msg)
    assert_equal(out_msg, {"msg": "connected", "session": "TeStSeSsIoNiD"})
    session.send({
        "msg": "result",
        "id": "1",
        "result": datetime.datetime(2015, 8, 17, 19, 43, 56, 289379),
        })
    (out_msg, ), _ = socket.send.call_args
    out_msg = json.loads(out_msg)
    assert_equal(out_msg, {
        "msg": "result",
        "id": "1",
        "result": {"$date": 1439840636000}
        })
    assert_raises(ValueError, session.send, {
        "msg": "result",
        "id": 4,
        "result": "foo",
        })


@mock.patch("ddpserver.utils.gen_id")
@mock.patch("ddpserver.DDPSession.send")
@with_setup(setup_socket_message)
def test_create_ddp_session(session_send, gen_id):
    gen_id.return_value = "TeStSeSsIoNiD"
    session = ddpserver.DDPSession(server, "1", socket, loop)
    session_send.assert_called_with({
        "msg": "connected",
        "session": "TeStSeSsIoNiD",
        })


@with_setup(setup_socket_message)
def test_process_ping():
    session.send = mock.Mock()
    session.process_message({"msg": "ping"})
    session.send.assert_called_with({"msg": "pong"})
    session.process_message({"msg": "ping", "id": "4"})
    session.send.assert_called_with({"msg": "pong", "id": "4"})


@mock.patch("ddpserver.utils.gen_id")
@with_setup(setup_socket_message)
def test_close_session(gen_id):
    gen_id.return_value = "TeStSeSsIoNiD"
    session = ddpserver.DDPSession(server, "1", socket, loop)
    server.ddp_sessions["TeStSeSsIoNiD"] = session
    session.close()
    socket.close.assert_called_with(3000, "Normal closure")
    assert_is_none(socket._ddp_session)
    assert_not_in("TeStSeSsIoNiD", server.ddp_sessions)


@with_setup(setup_socket_message)
def test_session_on_close_callbacks_deferring():
    callbacks = [mock.Mock() for i in range(100)]
    for callback in callbacks:
        session.on_close(callback)
    session.close()
    for callback in callbacks:
        assert_false(callback.called)
    next_tick()
    for callback in callbacks:
        assert_true(callback.called)


@with_setup(setup_socket_message)
def test_session_on_close_callback_with_error():
    callback1 = mock.Mock()
    session.on_close(callback1)
    callback2 = mock.Mock(side_effect=ValueError)
    session.on_close(callback2)
    callback3 = mock.Mock()
    session.on_close(callback3)
    session.close()
    next_tick()
    assert_true(callback1.called)
    assert_true(callback2.called)
    assert_true(callback3.called)
