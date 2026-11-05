# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-05

### Added
- CEP extension **AE MCP Bridge**: headless HTTP server inside After Effects (starts with AE) plus a status panel.
- Zero-dependency stdio MCP server (`server/ae_mcp_server.py`) with 10 tools:
  `ae_ping`, `ae_run_jsx`, `ae_run_jsx_file`, `ae_project_info`, `ae_comp_layers`, `ae_save_frame_png`,
  `ae_render_queue_add`, `ae_render`, `ae_save_project`, `ae_open_project`.
- Dialog suppression and structured ExtendScript errors with line numbers.
- `AE_MCP_HOST` / `AE_MCP_PORT` environment overrides, `--version` and `--check` flags.
- Windows installer/uninstaller (PowerShell), macOS install script, registry file for unsigned CEP extensions.
- Protocol test suite against a fake bridge and GitHub Actions CI.
