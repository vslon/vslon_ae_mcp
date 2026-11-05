// AE MCP Bridge (vslon_ae_mcp): local HTTP server on 127.0.0.1:8765 -> evalScript in After Effects.
// Requests are serialised through a promise queue because AE's scripting engine is single-threaded.
// Endpoints: GET /ping, POST /eval {"code": "<ExtendScript>"}. Port can be overridden with the AE_MCP_PORT env var.
(function () {
  var PORT = 8765;
  try { if (typeof process !== 'undefined' && process.env && process.env.AE_MCP_PORT) PORT = parseInt(process.env.AE_MCP_PORT, 10) || PORT; } catch (e) {}
  var http = require('http');
  var queue = Promise.resolve();
  function evalES(code) {
    return new Promise(function (resolve) { window.__adobe_cep__.evalScript(code, function (r) { resolve(r); }); });
  }
  function log(msg) {
    var el = document.getElementById('log');
    if (el) { el.textContent = new Date().toLocaleTimeString() + '  ' + msg + '\n' + el.textContent.slice(0, 3000); }
  }
  window.aeMcpStart = function (onState) {
    var server = http.createServer(function (req, res) {
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      if (req.method === 'GET' && req.url === '/ping') { res.end(JSON.stringify({ ok: true, app: 'After Effects', port: PORT })); return; }
      if (req.method === 'POST' && req.url === '/eval') {
        var body = '';
        req.on('data', function (c) { body += c; });
        req.on('end', function () {
          var code;
          try { code = JSON.parse(body).code; } catch (e) { res.statusCode = 400; res.end(JSON.stringify({ ok: false, error: 'bad json' })); return; }
          queue = queue.then(function () {
            log('eval ' + code.length + ' chars');
            return evalES(code).then(function (r) { res.end(JSON.stringify({ ok: true, result: r })); })
              .catch(function (e) { res.statusCode = 500; res.end(JSON.stringify({ ok: false, error: String(e) })); });
          });
        });
        return;
      }
      res.statusCode = 404; res.end(JSON.stringify({ ok: false, error: 'not found' }));
    });
    server.on('error', function (e) { onState && onState(e.code === 'EADDRINUSE' ? 'already running (port ' + PORT + ')' : 'error: ' + e.message); });
    server.listen(PORT, '127.0.0.1', function () { onState && onState('listening on 127.0.0.1:' + PORT); log('server up'); });
    server.timeout = 0;
  };
})();
