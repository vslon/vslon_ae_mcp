# Troubleshooting and ExtendScript gotchas

## Connection

| Symptom | Fix |
|---|---|
| `AE bridge not reachable at http://127.0.0.1:8765` | After Effects is closed, or the extension did not load. Open `Window > Extensions > AE MCP Bridge`. If the menu item is missing, unsigned extensions are not enabled: run `scripts/install.ps1` (or `scripts/enable_cep_debug.reg`) and restart AE. |
| Panel says `already running (port 8765)` | This is normal. The headless server started first, and the panel only shows status. |
| Panel says `error: …` | Another program uses port 8765. Set `AE_MCP_PORT` to a free port for both AE and the MCP server (see README → Configuration). |
| Tools do not appear in the client | Check the absolute paths in the client config, then restart the client. Run `python server/ae_mcp_server.py --check` with AE open: it should print the AE version. |
| Calls time out during renders | `ae_render` blocks AE until the queue is done. Pass a larger `timeout_s`. |

## Scripting

- **`empty result from AE (ExtendScript syntax error?)`**: the code did not parse. Common causes:
  - ES5+ syntax (`let`, `const`, arrow functions, template strings);
  - reserved words used as identifiers. ExtendScript reserves more words than modern JS, for example `short`, `int`, `char`, `byte`, `float`, `double`, `long`, `final`, `native`. `var short = …` fails with *Illegal use of reserved word*.
- **Return values**: the code is a function body, so use `return`. `File` and `Date` objects should be converted explicitly (`f.fsName`, `d.toString()`).
- **Undo**: wrap edits in `app.beginUndoGroup("…")` / `app.endUndoGroup()`, so one tool call is one undo step.
- **Indices shift**: removing or moving layers renumbers them. Look layers up by name, or iterate backwards when removing.
- **Track mattes (AE 2023+)**: mattes reference an explicit layer. Use `layer.setTrackMatte(matteLayer, TrackMatteType.ALPHA)`. After duplicating layers, re-assign their mattes.
- **Effect parameters**: get the match names by adding the effect and listing `effect.property(k).name / matchName`. Some third-party parameters, and some built-ins such as EXtractoR channel pickers, are not scriptable.

## Rendering and color

- **`ae_save_frame_png` looks dark or flat in a 32-bpc linear / ACES project.** `saveFrameToPng` writes working-space values without the output transform. For review frames, render through the queue with an output module that converts to display space.
- **Output-module color settings are not scriptable.** Create the template once in AE (`Edit > Templates > Output Module…`), for example an H.264 template with *Output Color Space: sRGB*. Then pass its name to `ae_render_queue_add` as `template`.
- **`Can not set attribute 'render' when RenderQueueItem status is … DONE`**: finished queue items cannot be re-queued. Use `app.project.renderQueue.item(i).duplicate()` and render the copy.
- **`Error Code: 512 … unexpected error while exporting`**: usually a GPU or third-party effect failing at render time. Disable effects one by one to find the culprit. Moving the effect from an adjustment layer onto the precomp layer, or switching it to CPU, often helps.
- **Work area vs full comp**: `ae_render_queue_add` renders the work area by default. Pass `full_comp: true` to render the whole comp.
