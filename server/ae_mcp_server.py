#!/usr/bin/env python3
"""vslon_ae_mcp: MCP server for Adobe After Effects.

Stdio MCP server with zero dependencies (Python 3.9+ standard library only).
It forwards tool calls to the "AE MCP Bridge" CEP extension running inside
After Effects, which evaluates ExtendScript in the open project and returns
the result as JSON.

    MCP client  --stdio-->  ae_mcp_server.py  --HTTP 127.0.0.1:8765-->  CEP bridge  --evalScript-->  After Effects

Environment variables:
    AE_MCP_HOST   bridge host (default 127.0.0.1)
    AE_MCP_PORT   bridge port (default 8765)

https://github.com/vslon/vslon_ae_mcp
"""
import json
import os
import sys
import urllib.error
import urllib.request

__version__ = "1.0.0"

BRIDGE = "http://%s:%s" % (os.environ.get("AE_MCP_HOST", "127.0.0.1"), os.environ.get("AE_MCP_PORT", "8765"))
PROTOCOL = "2024-11-05"

# ---------------------------------------------------------------- ExtendScript side
# ES3-compatible JSON stringify (ExtendScript has no reliable JSON object), dialogs suppressed so a
# script error can never leave a modal window that freezes AE.
ES_PRELUDE = r"""
function __s(v, d){ d=d||0; if(d>6) return '"<depth>"';
 if(v===null||v===undefined) return 'null';
 var t=typeof v;
 if(t==='number') return isFinite(v)?String(v):'null';
 if(t==='boolean') return v?'true':'false';
 if(t==='string') return '"'+v.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\n/g,'\\n').replace(/\r/g,'\\r').replace(/\t/g,'\\t')+'"';
 if(v instanceof Array){ var a=[]; for(var i=0;i<v.length;i++) a.push(__s(v[i],d+1)); return '['+a.join(',')+']'; }
 if(t==='object'){ if(v.reflect && v.toString && !(v.constructor===Object)) { try{ return __s(String(v.name!==undefined? v.name : v.toString()),d+1);}catch(e){} }
   var o=[]; for(var k in v){ try{ o.push(__s(String(k))+':'+__s(v[k],d+1)); }catch(e){} } return '{'+o.join(',')+'}'; }
 return __s(String(v),d+1);
}
"""

def wrap(code: str) -> str:
    return ES_PRELUDE + (
        "(function(){ app.beginSuppressDialogs(); var __out;"
        " try { var __r = (function(){\n" + code + "\n})(); __out = __s({ok:true, value:__r}); }"
        " catch(e){ __out = __s({ok:false, error:String(e), line:(e.line||null)}); }"
        " try{ app.endSuppressDialogs(false); }catch(e){}"
        " return __out; })();"
    )


def bridge_ping(timeout=3):
    with urllib.request.urlopen(BRIDGE + "/ping", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def run_es(code: str, timeout=120):
    data = json.dumps({"code": wrap(code)}).encode("utf-8")
    req = urllib.request.Request(BRIDGE + "/eval", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError("AE bridge not reachable at %s (%s). Is After Effects open with the AE MCP Bridge extension "
                           "(Window > Extensions > AE MCP Bridge)?" % (BRIDGE, e))
    if not resp.get("ok"):
        raise RuntimeError("bridge error: %s" % resp.get("error"))
    raw = resp.get("result")
    if raw is None or raw == "":
        raise RuntimeError("empty result from AE (ExtendScript syntax error?)")
    if isinstance(raw, str) and raw.startswith("EvalScript error"):
        raise RuntimeError(raw + " (ExtendScript syntax error)")
    try:
        out = json.loads(raw)
    except Exception:
        return raw
    if not out.get("ok"):
        raise RuntimeError("ExtendScript error%s: %s" % (" line %s" % out.get("line") if out.get("line") else "", out.get("error")))
    return out.get("value")


def js_str(s: str) -> str:
    return json.dumps(s)

# ---------------------------------------------------------------- tools
FIND_COMP = r"""
function __comp(n){ var p=app.project; for(var i=1;i<=p.numItems;i++){ var it=p.item(i); if(it instanceof CompItem && it.name===n) return it; }
  throw new Error('comp not found: '+n); }
"""

def t_ping(a):
    b = bridge_ping()
    info = run_es("return {version: app.version, project: app.project.file ? app.project.file.fsName : null, items: app.project.numItems};")
    return {"bridge": b, "ae": info}


def t_run_jsx(a):
    return run_es(a["code"], timeout=a.get("timeout_s", 120))


def t_run_jsx_file(a):
    code = "var f=new File(%s); if(!f.exists) throw new Error('no file '+f.fsName); return $.evalFile(f);" % js_str(a["path"])
    return run_es(code, timeout=a.get("timeout_s", 600))


def t_project_info(a):
    code = r"""
var p=app.project, items=[];
for(var i=1;i<=p.numItems;i++){ var it=p.item(i), o={id:it.id, name:it.name, type:it.typeName, folder:(it.parentFolder&&it.parentFolder!==p.rootFolder)?it.parentFolder.name:''};
  if(it instanceof CompItem){ o.w=it.width; o.h=it.height; o.fps=it.frameRate; o.dur=it.duration; o.layers=it.numLayers; o.usedIn=it.usedIn.length; }
  else if(it instanceof FootageItem){ o.usedIn=it.usedIn.length; try{ o.file=it.file?it.file.fsName:null; }catch(e){} try{ o.dur=it.duration; o.fps=it.frameRate; }catch(e){} }
  items.push(o); }
var rq=[]; for(var i=1;i<=p.renderQueue.numItems;i++){ var r=p.renderQueue.item(i); rq.push({i:i, comp:r.comp.name, status:String(r.status), render:r.render}); }
return {file: p.file?p.file.fsName:null, dirty: p.dirty, bpc: p.bitsPerChannel, items: items, renderQueue: rq};"""
    return run_es(code)


def t_comp_layers(a):
    code = FIND_COMP + r"""
var C=__comp(%s), out=[];
for(var j=1;j<=C.numLayers;j++){ var L=C.layer(j), o={i:j, name:L.name, enabled:L.enabled, solo:L.solo, inPoint:L.inPoint, outPoint:L.outPoint, startTime:L.startTime};
  try{ o.source=L.source?L.source.name:null; }catch(e){}
  try{ o.adjustment=L.adjustmentLayer; o.blend=String(L.blendingMode); o.trackMatte=String(L.trackMatteType); o.isMatte=L.isTrackMatte; if(L.hasTrackMatte&&L.trackMatteLayer) o.matteLayer=L.trackMatteLayer.name; }catch(e){}
  try{ o.parent=L.parent?L.parent.name:null; }catch(e){}
  try{ var fx=L.property('ADBE Effect Parade'), f=[]; for(var k=1;k<=fx.numProperties;k++) f.push({name:fx.property(k).name, match:fx.property(k).matchName, on:fx.property(k).enabled}); o.effects=f; }catch(e){}
  try{ o.opacity=L.property('ADBE Transform Group').property('ADBE Opacity').value; }catch(e){}
  out.push(o); }
return {comp:C.name, w:C.width, h:C.height, fps:C.frameRate, dur:C.duration, workArea:[C.workAreaStart, C.workAreaDuration], layers:out};""" % js_str(a["comp"])
    return run_es(code)


def t_save_frame(a):
    code = FIND_COMP + r"""
var C=__comp(%s), t=%s/C.frameRate, f=new File(%s); f.parent.create(); C.saveFrameToPng(t, f); return f.fsName;""" % (
        js_str(a["comp"]), float(a.get("frame", 0)), js_str(a["path"]))
    return run_es(code, timeout=a.get("timeout_s", 300))


def t_rq_add(a):
    code = FIND_COMP + r"""
var C=__comp(%s), it=app.project.renderQueue.items.add(C), om=it.outputModule(1);
var tpl=%s; if(tpl) om.applyTemplate(tpl);
var f=new File(%s); f.parent.create(); om.file=f;
if(%s){ it.timeSpanStart=0; it.timeSpanDuration=C.duration; }
return {index: app.project.renderQueue.numItems, file: om.file.fsName, span:[it.timeSpanStart, it.timeSpanDuration]};""" % (
        js_str(a["comp"]), js_str(a.get("template", "")), js_str(a["output_path"]), "true" if a.get("full_comp") else "false")
    return run_es(code)


def t_render(a):
    code = r"""
var rq=app.project.renderQueue, only=%s;
if(only){ for(var i=1;i<=rq.numItems;i++){ var r=rq.item(i); if(r.status==RQItemStatus.QUEUED) r.render=false; } for(var k=0;k<only.length;k++) rq.item(only[k]).render=true; }
rq.render();
var out=[]; for(var i=1;i<=rq.numItems;i++){ var r=rq.item(i); out.push({i:i, comp:r.comp.name, status:String(r.status)}); } return out;""" % (
        json.dumps(a.get("indices")) if a.get("indices") else "null")
    return run_es(code, timeout=a.get("timeout_s", 3600))


def t_save_project(a):
    if a.get("path"):
        code = "var f=new File(%s); app.project.save(f); return app.project.file.fsName;" % js_str(a["path"])
    else:
        code = "app.project.save(); return app.project.file.fsName;"
    return run_es(code)


def t_open_project(a):
    code = "var f=new File(%s); if(!f.exists) throw new Error('no file '+f.fsName); app.open(f); return app.project.file.fsName;" % js_str(a["path"])
    return run_es(code, timeout=300)


TOOLS = {
    "ae_ping": (t_ping, "Check the bridge and After Effects: AE version, open project.", {}, []),
    "ae_run_jsx": (t_run_jsx, "Run ExtendScript in After Effects. Code is a function body: use `return` to send a value back "
                   "(JSON-serialised). Dialogs are suppressed. Wrap edits in app.beginUndoGroup/endUndoGroup.",
                   {"code": {"type": "string"}, "timeout_s": {"type": "number"}}, ["code"]),
    "ae_run_jsx_file": (t_run_jsx_file, "Run a .jsx file (path on this computer) in After Effects; returns its last value.",
                        {"path": {"type": "string"}, "timeout_s": {"type": "number"}}, ["path"]),
    "ae_project_info": (t_project_info, "List project items (comps, footage, folders) and the render queue.", {}, []),
    "ae_comp_layers": (t_comp_layers, "Layers of a comp with sources, in/out, blend, mattes, effects, opacity.",
                       {"comp": {"type": "string"}}, ["comp"]),
    "ae_save_frame_png": (t_save_frame, "Render one frame of a comp to PNG (comp frame number).",
                          {"comp": {"type": "string"}, "frame": {"type": "number"}, "path": {"type": "string"}, "timeout_s": {"type": "number"}},
                          ["comp", "path"]),
    "ae_render_queue_add": (t_rq_add, "Add a comp to the render queue with an output-module template (e.g. H264_15M_sRGB_out).",
                            {"comp": {"type": "string"}, "output_path": {"type": "string"}, "template": {"type": "string"},
                             "full_comp": {"type": "boolean", "description": "render the whole comp instead of the work area"}},
                            ["comp", "output_path"]),
    "ae_render": (t_render, "Render the queue (blocks AE until done). `indices` = render only these queue items.",
                  {"indices": {"type": "array", "items": {"type": "integer"}}, "timeout_s": {"type": "number"}}, []),
    "ae_save_project": (t_save_project, "Save the project; with `path` = Save As (new version).", {"path": {"type": "string"}}, []),
    "ae_open_project": (t_open_project, "Open an .aep project.", {"path": {"type": "string"}}, ["path"]),
}

# ---------------------------------------------------------------- MCP stdio loop
def send(msg):
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(req):
    m, rid, params = req.get("method"), req.get("id"), req.get("params") or {}
    if m == "initialize":
        return {"protocolVersion": params.get("protocolVersion", PROTOCOL), "capabilities": {"tools": {}},
                "serverInfo": {"name": "after-effects", "version": __version__}}
    if m == "ping":
        return {}
    if m == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": {"type": "object", "properties": p, "required": r}}
                          for n, (f, d, p, r) in TOOLS.items()]}
    if m == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in TOOLS:
            return {"content": [{"type": "text", "text": "unknown tool " + str(name)}], "isError": True}
        try:
            res = TOOLS[name][0](args)
            text = res if isinstance(res, str) else json.dumps(res, ensure_ascii=False, indent=1)
            return {"content": [{"type": "text", "text": text}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": str(e)}], "isError": True}
    raise KeyError(m)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print("vslon_ae_mcp " + __version__)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        try:
            print(json.dumps(t_ping({}), indent=1))
        except Exception as e:
            print("FAIL: %s" % e)
            sys.exit(1)
        return
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        if "id" not in req:          # notification
            continue
        try:
            send({"jsonrpc": "2.0", "id": req["id"], "result": handle(req)})
        except KeyError as e:
            send({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "method not found: %s" % e}})
        except Exception as e:
            send({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32603, "message": str(e)}})


if __name__ == "__main__":
    main()
