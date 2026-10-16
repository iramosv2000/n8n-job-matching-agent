import httpx2
import pytest

from matcher.http import USER_AGENT, DisallowedByRobots, PoliteClient


class FakeTime:
    def __init__(self):
        self.now, self.slept = 100.0, []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(round(seconds, 3))
        self.now += seconds


def client_for(handler, **kwargs):
    fake = FakeTime()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler), sleep=fake.sleep, clock=fake.clock, **kwargs
    )
    return client, fake


def test_respects_robots_disallow_and_sends_identifiable_agent():
    seen = []

    def handler(request):
        seen.append(request.headers["user-agent"])
        if request.url.path == "/robots.txt":
            return httpx2.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return httpx2.Response(200, text="ok")

    client, _ = client_for(handler)
    assert client.get_text("https://example.org/public") == "ok"
    with pytest.raises(DisallowedByRobots):
        client.get_text("https://example.org/private/x")
    assert set(seen) == {USER_AGENT}
    assert "example.org" in client.robots_checked_at


@pytest.mark.parametrize(("status", "allowed"), [(404, True), (410, True), (403, False), (500, False)])
def test_missing_vs_refused_robots(status, allowed):
    client, _ = client_for(
        lambda r: httpx2.Response(status if r.url.path == "/robots.txt" else 200, text="ok")
    )
    assert client.allowed("https://example.org/a") is allowed


def test_spacing_between_requests_to_the_same_host():
    client, fake = client_for(
        lambda r: httpx2.Response(404 if r.url.path == "/robots.txt" else 200, text="ok")
    )
    client.get_text("https://example.org/a")
    client.get_text("https://example.org/b")
    assert fake.slept == [0.8, 0.8]  # after robots.txt, and between the two pages


def test_backs_off_on_server_errors_then_succeeds():
    answers = iter([503, 429, 200])

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx2.Response(404)
        return httpx2.Response(next(answers), text="ok")

    client, fake = client_for(handler, min_interval=0)
    assert client.get_text("https://example.org/a") == "ok"
    assert fake.slept == [3.0, 6.0]


@pytest.mark.parametrize("status", [401, 403, 404, 410])
def test_refusals_and_missing_pages_are_not_retried(status):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx2.Response(404 if request.url.path == "/robots.txt" else status)

    client, _ = client_for(handler, min_interval=0)
    assert client.get_text("https://example.org/a") is None
    assert calls == ["/robots.txt", "/a"]


def test_network_errors_are_retried_then_give_up():
    def handler(request):
        if request.url.path == "/robots.txt":
            raise httpx2.ConnectError("down")
        raise httpx2.ConnectError("down")

    client, _ = client_for(handler, min_interval=0, retries=1)
    assert client.allowed("https://example.org/a") is False  # unreadable robots: nothing allowed
    client._robots["example.org"].disallow_all = False
    client._robots["example.org"].allow_all = True
    assert client.get_text("https://example.org/a") is None
    client.close()
