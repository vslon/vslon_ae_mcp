// Removes footage items that are not used in any comp (like File > Dependencies > Remove Unused Footage).
// Undoable as a single step.
app.beginUndoGroup("Remove unused footage");
var removed = [];
for (var i = app.project.numItems; i >= 1; i--) {
    var it = app.project.item(i);
    if (it instanceof FootageItem && it.usedIn.length === 0) {
        removed.push(it.name);
        it.remove();
    }
}
app.endUndoGroup();
return { removed: removed.length, names: removed };
