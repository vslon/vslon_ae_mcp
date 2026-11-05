# Example prompts

Things that work well once the server is connected. The assistant composes ExtendScript on the fly
and runs it through `ae_run_jsx`, so you describe the result, not the code.

**Project hygiene**
- "Open `D:\shots\sh010\comp\sh010_v012.aep`, remove all unused footage and empty folders, save as v013."
- "Rename the layers in `sh010_main` by what they contain and group the mattes at the bottom."

**Variants**
- "Duplicate `main_precomp` for each sky render in `render/sky_v*/` and swap the CG footage in each copy."
- "Lower the opacity of every layer named `*_glow*` to 40% of its current value in all comps."

**Rendering**
- "Queue `sh010_final` with the `H264_15M_sRGB_out` template to `out/sh010_v013.mp4` and render it."
- "Render frame 24 of `sh010_final` to PNG so you can look at it."

**Inspection**
- "List the layers of `sh010_main` with their effects and track mattes."
- "Which comps use `bg_plate_v003.exr`?"
