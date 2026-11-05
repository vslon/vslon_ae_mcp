// Duplicates a comp N times with suffixed names, e.g. for look or sky variants.
var SRC = "main_comp", VARIANTS = ["A", "B", "C"];
var src = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === SRC) { src = it; break; }
}
if (!src) throw new Error("comp not found: " + SRC);
app.beginUndoGroup("Duplicate comp versions");
var made = [];
for (var v = 0; v < VARIANTS.length; v++) {
    var d = src.duplicate();
    d.name = SRC + "_" + VARIANTS[v];
    made.push(d.name);
}
app.endUndoGroup();
return made;
