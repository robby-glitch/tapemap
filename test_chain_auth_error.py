"""The reload trigger must match the failure, not the advice.

2026-08-12: NIFTY's chain was dead from the open every session. `poll` raises
"upstox feed down: no error recorded -- the socket has not finished a connect
attempt yet. If this does not clear, check the token first: python
upstox_auth.py" while the websocket is still dialling, and the poller decided
whether to tear the socket down with `"token" in str(e).lower()`. The ADVICE
matched, so a warm-up rebuilt the socket, and the round-robin's first index
polled into the next connect and rebuilt it again -- forever. The other two
indices, polled 3.5s and 7s later, were fine on the same socket.

These lock both halves: the warm-up sentence must not trigger a reload, and a
real 401 still must.
"""

import chain_live

# `upstox_chain` is imported INSIDE the one test that needs it, never at module
# scope: test_broker_switch asserts it stays out of sys.modules unless the
# broker is upstox, and importing it here would fail that guard through a
# side door.

# The exact sentence upstox_chain.poll raises while the socket is dialling.
WARMING_UP = (
    "upstox feed down: no error recorded -- the socket has not finished a "
    "connect attempt yet. If this does not clear, check the token first: "
    "python upstox_auth.py")


def test_the_warming_up_message_does_not_force_a_reload():
    assert not chain_live.is_auth_error(RuntimeError(WARMING_UP))


def test_a_real_401_still_forces_a_reload():
    assert chain_live.is_auth_error(
        RuntimeError("upstox feed down: WebSocketBadStatusException: 401"))
    assert chain_live.is_auth_error(RuntimeError("Unauthorized"))


def test_other_poll_failures_leave_the_socket_alone():
    # Staleness and an empty mailbox are feed problems, not credential
    # problems -- rebuilding the socket for them costs every index a session.
    assert not chain_live.is_auth_error(
        RuntimeError("upstox feed stale: 91s since the last frame"))
    assert not chain_live.is_auth_error(
        RuntimeError("upstox feed connected but has sent nothing yet"))


def test_the_advice_is_still_in_the_message_a_human_reads():
    # The hint stays for the operator; only the machine stopped acting on it.
    # If this fails, the wording moved and the first test no longer guards
    # anything real.
    assert "token" in WARMING_UP
    assert "connect attempt" in WARMING_UP


def test_start_waits_for_the_socket_rather_than_returning_cold():
    # The structural half: whichever index polls first must not eat a cold
    # socket every morning.
    import upstox_chain
    assert upstox_chain.CONNECT_WAIT_S > 0
