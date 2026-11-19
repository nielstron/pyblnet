"""
The web interface of the BL-NET without I/O: parsing its pages, and the
requests to log in, read values and set outputs as flows (see flow.py).
pyblnet.sync.BLNETWeb runs them with requests, pyblnet.aio.BLNETWeb with aiohttp.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import html
import re
from html.parser import HTMLParser

# An input on the inputs page: a measured value with unit, or the state of a
# digital input. The value of a digital input is "1" (on) or "0" (off), like
# the direct connection reports it.
INPUT_PATTERN = re.compile(
    r"(?P<id>\d+):&nbsp;(?P<name>.+)\n(&nbsp;){3,6}"
    r"(?:(?P<value>(-&nbsp;)?\d+,\d+) (?P<unit_of_measurement>.+?) &nbsp;&nbsp;"
    r"|(?P<state>AUS|EIN|OFF|ON)(&nbsp;)+)PAR?"
)
DIGITAL_INPUT_STATES = {"AUS": "0", "OFF": "0", "EIN": "1", "ON": "1"}

# A mixer on the outputs page: its mode, then the state of the opening output
# and of the closing output, which has the next id
MIXER_OUTPUT_PATTERN = re.compile(
    r"(?P<id>\d+):&nbsp;(?P<name>.+)\n(&nbsp;)+(?P<mode>AUTO|HAND) .*PAR\?.*\n"
    r"(&nbsp;)+auf:(&nbsp;)+(?P<open>AUS|EIN)\n"
    r"(&nbsp;)*(?P<id_close>\d+):&nbsp;zu:(&nbsp;)+(?P<close>AUS|EIN)"
)


class _ElementTextParser(HTMLParser):
    """
    Collects the text of all elements with the given tag and class or id.
    Entities like &nbsp; are kept as written and <br> becomes a newline,
    which is what the regular expressions below expect.
    """

    def __init__(self, tag, cls=None, id=None):
        super().__init__(convert_charrefs=False)
        self.tag = tag
        self.cls = cls
        self.id = id
        # text of each matching element, in document order
        self.texts = []
        # for each open element with self.tag: its index in self.texts,
        # or None if it doesn't match. Matching elements can be nested.
        self._open = []

    def _matches(self, attrs):
        attrs = dict(attrs)
        return (self.cls is None or self.cls in (attrs.get("class") or "").split()) and (
            self.id is None or attrs.get("id") == self.id
        )

    def handle_starttag(self, tag, attrs):
        if tag == self.tag:
            if self._matches(attrs):
                self.texts.append("")
                self._open.append(len(self.texts) - 1)
            else:
                self._open.append(None)
        elif tag == "br":
            self.handle_data("\n")

    def handle_endtag(self, tag):
        if tag == self.tag and self._open:
            self._open.pop()

    def handle_data(self, data):
        for index in self._open:
            if index is not None:
                self.texts[index] += data

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")


def _element_texts(page, tag, cls=None, id=None):
    """Texts of all elements in page with the given tag and class or id"""
    parser = _ElementTextParser(tag, cls, id)
    parser.feed(page)
    parser.close()
    return parser.texts


def _element_text(page, tag, cls=None, id=None):
    """Text of the first such element, empty if there is none"""
    texts = _element_texts(page, tag, cls, id)
    return texts[0] if texts else ""


# A digital output on the outputs page: its mode and state
DIGITAL_OUTPUT_PATTERN = re.compile(
    r"(?P<id>\d+):&nbsp;(?P<name>.+)\n&nbsp;&nbsp;&nbsp;&nbsp;(?P<mode>(AUTO|HAND))/(?P<value>(AUS|EIN))"
)


@dataclass(frozen=True)
class Request:
    """An HTTP request to the BL-NET, path is relative to its address"""

    method: str
    path: str
    data: dict | None = None
    headers: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Response:
    """What the flows need of an HTTP response"""

    text: str
    # the Set-Cookie header, None if there is none
    set_cookie: str | None = None


class TransportError(Exception):
    """A request failed, e.g. no connection or a timeout"""


def is_blnet_page(page):
    """Whether page is served by a BL-NET"""
    # either a 'Zugriff verweigert' message is shown
    if "BL-Net".lower() in _element_text(page, "title").lower():
        return True
    # or (more often) the BL-NET Menü
    return "BL-NET" in _element_text(page, "div", id="head")


def parse_analog_values(page):
    """
    The analog values (temperatures, speeds) and digital inputs on the inputs
    page, a list of dicts with id, name, value, unit of measurement (and type
    for digital inputs). None if the page has none, e.g. access is denied.
    """
    # get the element containing the interesting information
    texts = _element_texts(page, "div", cls="c")
    # in case of access denied or other errors, return None
    if len(texts) < 2:
        return None
    data = []
    for match in INPUT_PATTERN.finditer(texts[1]):
        # convert html entities to unicode characters,
        # replace &nbsp; by " " since it is not unescaped as expected
        entry = {
            "id": match["id"],
            "name": html.unescape(match["name"].replace("&nbsp;", " ")),
        }
        if match["state"] is not None:
            entry["value"] = DIGITAL_INPUT_STATES[match["state"]]
            entry["unit_of_measurement"] = None
            entry["type"] = "digital"
        else:
            # replace decimal "," by "." and remove "&nbsp;" completely
            entry["value"] = match["value"].replace("&nbsp;", "").replace(",", ".")
            entry["unit_of_measurement"] = html.unescape(
                match["unit_of_measurement"].replace("&nbsp;", " ")
            )
        data.append(entry)
    return data


def parse_digital_values(page):
    """
    The digital outputs (switches) on the outputs page, a list of dicts with
    id, name, mode (AUTO/HAND), value (EIN/AUS). None if the page has none,
    e.g. access is denied.
    """
    # Check if we didn't fail in access
    if "BL-Net Zugang verweigert" in _element_text(page, "title"):
        return None
    # get the element containing the interesting information
    texts = _element_texts(page, "div", cls="c")
    if len(texts) < 2:
        return None
    data_raw = texts[1]
    data = []
    for match in DIGITAL_OUTPUT_PATTERN.finditer(data_raw):
        # convert html entities to unicode characters
        data.append(
            {
                key: html.unescape(value.replace("&nbsp;", " "))
                for key, value in match.groupdict().items()
            }
        )
    # a mixer uses two outputs (open, close) with a common mode
    for match in MIXER_OUTPUT_PATTERN.finditer(data_raw):
        name = html.unescape(match["name"].replace("&nbsp;", " "))
        for id, direction, value in [
            (match["id"], "auf", match["open"]),
            (match["id_close"], "zu", match["close"]),
        ]:
            data.append(
                {"id": id, "name": f"{name} {direction}", "mode": match["mode"], "value": value}
            )
    data.sort(key=lambda entry: int(entry["id"]))
    return data


def digital_command(value):
    """
    The command setting a digital output to value: "1" (off), "2" (on) or
    "3" (auto). Accepts 'EIN', 'AUS', 'AUTO', their English names, the
    commands, and anything evaluating to True or False.
    """
    if isinstance(value, str):
        if value.lower() == "auto" or value == "3":
            return "3"
        if value.lower() in ("ein", "on") or value == "2":
            return "2"
        if value.lower() in ("aus", "off") or value == "1":
            return "1"
        raise ValueError("Illegal input string {}".format(value))
    if isinstance(value, int) and not isinstance(value, bool):
        if value in (1, 2, 3):
            return str(value)
        if value == 0:
            return "1"
        raise ValueError("Illegal input integer {}".format(value))
    # value can be interpreted as a true value
    return "2" if value else "1"


def digital_path(digital_id, value):
    """Path of the request setting the digital output digital_id to value"""
    digital_id = int(digital_id)
    if digital_id < 1:
        raise ValueError("Device id can't be smaller than 1, was {}".format(digital_id))
    if digital_id > 15:
        raise ValueError("Device id can't be larger than 15, was {}".format(digital_id))
    # the id is a hex digit, so that 10 etc become A...
    return "/580600.htm?blw91A1200{:X}={}".format(digital_id, digital_command(value))


def probe():
    """Flow: whether a BL-NET answers"""
    try:
        response = yield Request("GET", "")
    except TransportError:
        return False
    return is_blnet_page(response.text)


class WebSession:
    """
    The state of a session with the web interface, and the flows using it.
    The flows return what the methods of BLNETWeb return.
    """

    def __init__(self, password):
        self.password = password
        # TAID cookie in the form 'TAID="EEEE"'
        self.current_taid = ""

    def _get(self, path):
        # without a session cookie, e.g. after a failed login, send none
        headers = {"Cookie": self.current_taid} if self.current_taid else {}
        return Request("GET", path, headers=headers)

    def logged_in(self):
        """Flow: whether we are still logged into the web interface"""
        if self.password is None:
            return True
        # check if a request to a restricted page returns a cookie if
        # we have sent one (if our cookie is the current one this
        # would be the case). The page is chosen to be small.
        try:
            response = yield self._get("/par.htm?blp=A1200101&1238653")
        except TransportError:
            return False
        return response.set_cookie is not None

    def log_in(self):
        """Flow: log in as expert, renews the TAID. Returns whether it worked"""
        if (yield from self.logged_in()):
            return True
        try:
            response = yield Request(
                "POST",
                "/main.html",
                data={"blu": 1, "blp": self.password, "bll": "Login"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except TransportError:
            return False
        self.current_taid = response.set_cookie
        # try two times to log in
        for _ in range(2):
            if (yield from self.logged_in()):
                return True
        return False

    def log_out(self):
        """Flow: log out. Returns whether it worked"""
        if self.password is None:
            return True
        try:
            yield self._get("/main.html?blL=1")
        except TransportError:
            return False
        return not (yield from self.logged_in())

    def _still_logged_in(self, path):
        """Send a command, whether we are still logged in afterwards (it worked)"""
        try:
            response = yield self._get(path)
        except TransportError:
            return False
        return self.password is None or response.set_cookie is not None

    def set_node(self, node):
        """Flow: select the CAN node of the UVR to read and control"""
        return (yield from self._still_logged_in("/can.htm?blaB=" + str(node)))

    def read_analog_values(self):
        """Flow: the analog values, see parse_analog_values"""
        try:
            response = yield self._get("/580500.htm")
        except TransportError:
            return None
        return parse_analog_values(response.text)

    def read_digital_values(self):
        """Flow: the digital outputs, see parse_digital_values"""
        try:
            response = yield self._get("/580600.htm")
        except TransportError:
            return None
        return parse_digital_values(response.text)

    def set_digital_value(self, digital_id, value):
        """Flow: set a digital output, see digital_command for the values"""
        return (yield from self._still_logged_in(digital_path(digital_id, value)))

    def _logged_in_session(self, flow):
        """Run flow between logging in and out, like `with BLNETWeb(...)`"""
        yield from self.log_in()
        try:
            result = yield from flow
        except GeneratorExit:
            # the flow is abandoned, no more requests possible
            raise
        except BaseException:
            yield from self.log_out()
            raise
        yield from self.log_out()
        return result

    def fetch(self, node=None):
        """Flow: the analog values and digital outputs, as lists"""

        def read():
            if node is not None:
                yield from self.set_node(node)
            analog = yield from self.read_analog_values()
            digital = yield from self.read_digital_values()
            return analog, digital

        return (yield from self._logged_in_session(read()))

    def turn(self, digital_id, value, node=None):
        """Flow: set a digital output in a session of its own, raise if it fails"""

        def turn():
            if not (yield from self.logged_in()):
                raise ConnectionError("Could not log in")
            if node is not None and not (yield from self.set_node(node)):
                raise ConnectionError("Could not set can node to {}".format(node))
            if not (yield from self.set_digital_value(digital_id, value)):
                raise ConnectionError(
                    "Failed to set digital switch {} to value {}".format(digital_id, value)
                )
            return True

        return (yield from self._logged_in_session(turn()))
