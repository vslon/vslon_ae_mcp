// Run with ae_run_jsx (paste as `code`) or ae_run_jsx_file (pass the path).
// Returns every comp with size, frame rate, duration and layer count.
var out = [];
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem) {
        out.push({ name: it.name, w: it.width, h: it.height, fps: it.frameRate, dur: it.duration, layers: it.numLayers });
    }
}
return out;
