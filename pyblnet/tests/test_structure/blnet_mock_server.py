import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer
try:
    from http import HTTPStatus
except ImportError:
    # Backwards compatability
    import http.client as HTTPStatus
import re
import posixpath
from pathlib import Path

SERVER_DIR = Path(__file__).parent or Path('.')


class BLNETServer(HTTPServer):

    # Currently allowed login cookie
    # or none if no one logged in
    logged_in = True
    # no login necessary
    password = None
    # access to digital nodes
    nodes = {}
    # Enable option to block server
    # (sends access denied all the time, for whatever reason)
    blocked = False

    def set_password(self, password):
        self.password = password
        self.logged_in = None

    def set_logged_in(self, cookie):
        self.logged_in = cookie

    def set_node(self, id, value):
        self.nodes[id] = value

    def get_node(self, id):
        return self.nodes.get(id)

    def set_blocked(self):
        self.blocked = True

    def unset_blocked(self):
        self.blocked = False


class BLNETRequestHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        """
        Handle get request, but check for errors in protocol
        :return:
        """
        if self.server.blocked:
            self.send_error(403, "Access denied because server is blocked")
            return
        path = self.translate_path(self.path)
        # Only access that is allowed without login is main.html
        if (not Path(path) == SERVER_DIR
                and not Path(path) == SERVER_DIR.joinpath('main.htm')
                and not Path(path) == SERVER_DIR.joinpath('main.html')):
            if not self.server.logged_in:
                self.send_error(403, "Not logged in, access denied")
                return
            # Parse node sets
            node_reg = re.compile(
                r'[?&]blw91A1200(?P<node>[0-9a-fA-F])=(?P<value>[1-3])')
            for match in node_reg.finditer(self.path):
                self.server.set_node(match.group('node'), match.group('value'))

        # print(path)
        super().do_GET()

    def do_POST(self):
        if self.server.blocked:
            # apparently login may still may possible, access may be denied anyway
            pass
        # Result of self.rfile.read() if correct POST request:
        # b'blu=1&blp=0123&bll=Login'
        perfect = b'blu=1&blp=0123&bll=Login'
        request_raw = self.rfile.read(len(perfect))
        request_string = request_raw.decode(encoding='utf-8')
        request_data = request_string.split("&")

        blu = False
        blp = False
        bll = False
        for query in request_data:
            if query.startswith("blu"):
                if query.split("=")[1] != "1":
                    self.send_error(
                        403,
                        "Wrong user set: expected blu=1, got {}".format(query))
                    return
                blu = True
            elif query.startswith("blp"):
                if query.split("=")[1] != self.server.password:
                    self.send_error(
                        403, "Wrong password: expected blp={}, got {}".format(
                            self.server.password, query))
                    return
                blp = True
            elif query.startswith("bll"):
                if query.split("=")[1] != "Login":
                    self.send_error(
                        403,
                        "Wrong bll spec, expected bll=Login, got {}".format(
                            request_string))
                    return
                bll = True
        if not (blu and blp and bll):
            self.send_error(403,
                            "Missing query param in {}".format(request_string))
            return
        # Check for content type
        if not self.headers.get(
                'Content-Type') == 'application/x-www-form-urlencoded':
            self.send_error(403, "Wrong content-type")
            return
        # All checks passed? set Set-Cookie header and do_GET
        # random cookie - do not hardcode
        self.server.set_logged_in('C1A3')
        self.headers.add_header('Cookie', 'C1A3')
        self.do_GET()

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        only slightly changed method of the standard library
        """
        # abandon query parameters
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = str(SERVER_DIR.absolute())
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Ignore components that are not a simple file/directory name
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/'
        return path

    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        only slightly changed method of the standard library
        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/', parts[3],
                             parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            # BLNET has main.html/main.htm
            for index in "main.html", "main.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified",
                             self.date_time_string(fs.st_mtime))
            # Addition: send cookie
            if (self.server.logged_in is not None
                    and self.server.logged_in == self.headers.get('Cookie')):
                self.send_header('Set-Cookie', 'C1A3')
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def send_error(self, code, message=None, explain=None):
        """
        Send blnet zugang verweigert page
        :param code:
        :param message:
        :param explain:
        :return:
        """
        self.log_error("code %d, message %s", code, message)
        self.send_response(code, message)
        self.send_header('Connection', 'close')

        # Message body is omitted for cases described in:
        #  - RFC7230: 3.3. 1xx, 204(No Content), 304(Not Modified)
        #  - RFC7231: 6.3.6. 205(Reset Content)
        body = None
        if (code >= 200 and
                code not in (HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT,
                             HTTPStatus.NOT_MODIFIED)):
            # HTML encode to prevent Cross Site Scripting attacks
            # (see bug #1100201)
            # Specialized error method for BLNET
            with SERVER_DIR.joinpath(".error.html").open('rb') as file:
                body = file.read()
            self.send_header("Content-Type", self.error_content_type)
            self.send_header('Content-Length', int(len(body)))
        self.end_headers()

        if self.command != 'HEAD' and body:
            self.wfile.write(body)
