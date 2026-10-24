import os
import re
from http.server import SimpleHTTPRequestHandler, HTTPServer

class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    HTTP handler with full support for Range: bytes=start-end headers (HTTP 206),
    enabling native browser HTML5 <video> streaming and seeking in Chrome/Safari/Edge.
    """
    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_head(self):
        self.range_bytes_to_send = None
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()

        range_header = self.headers.get("Range")
        if not range_header or not range_header.startswith("bytes="):
            return super().send_head()

        total_bytes = os.path.getsize(path)
        m = re.match(r"bytes=(\d*)-(\d*)", range_header)
        if not m:
            return super().send_head()

        raw_start, raw_end = m.groups()
        start = int(raw_start) if raw_start else 0
        end = int(raw_end) if raw_end else total_bytes - 1

        if start >= total_bytes:
            self.send_error(416, "Requested Range Not Satisfiable")
            return None

        end = min(end, total_bytes - 1)
        length = end - start + 1
        self.range_bytes_to_send = length

        try:
            f = open(path, "rb")
            f.seek(start)
        except OSError:
            self.send_error(404, "File not found")
            return None

        self.send_response(206)
        ctype = self.guess_type(path)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Range", f"bytes {start}-{end}/{total_bytes}")
        self.send_header("Content-Length", str(length))
        self.send_header("Last-Modified", self.date_time_string(os.path.getmtime(path)))
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        """Copies only the specified range if bytes_to_send is set."""
        if getattr(self, "range_bytes_to_send", None) is not None:
            remaining = self.range_bytes_to_send
            chunk_size = 64 * 1024
            while remaining > 0:
                to_read = min(remaining, chunk_size)
                chunk = source.read(to_read)
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        else:
            super().copyfile(source, outputfile)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4173
    web_dir = sys.argv[2] if len(sys.argv) > 2 else "frontend/dist"
    
    os.chdir(os.path.abspath(web_dir))
    server = HTTPServer(("0.0.0.0", port), RangeHTTPRequestHandler)
    print(f"Serving {web_dir} with Range support on http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
