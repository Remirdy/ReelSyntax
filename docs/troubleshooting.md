# Troubleshooting

Run `reelsyntax doctor` in the same environment as the render command. Use `--json` for the tool versions, paths and gateway diagnostics. A project can be validated on a machine with just Python. Rendering and QC require Pillow, FFmpeg and FFprobe.

| Symptom | Check and repair |
| --- | --- |
| FFmpeg or FFprobe unavailable | Run both executables with `-version`. Add their directory to PATH or set `REELSYNTAX_FFMPEG` and `REELSYNTAX_FFPROBE` to absolute executable paths. Restart the host if its environment predates the change. |
| Blender unavailable | Run Blender with `--version` and set `REELSYNTAX_BLENDER` to the executable. Aperture requires native Blender 5.1 or newer. |
| Chromium binary missing | Install the browser extra and run `python -m playwright install chromium` with the same interpreter. Use the same `PLAYWRIGHT_BROWSERS_PATH` during setup and rendering. |
| Registry digest mismatch on Windows | Inspect `git diff` and `git ls-files --eol`. The checkout uses LF for skill bodies and CRLF for the CSV. Reindex intentional changes with `reelsyntax skills reindex`. |
| Source changed since render | Review the changed input and render the current project before exporting or running QC. |
| Text exceeds safe layout | Shorten or wrap the affected string in its locale table. Check the rendered label at the smallest delivery size. |

The optional development container includes FFmpeg, Blender and Playwright Chromium. The distribution's Blender version determines which native recipes can run.
