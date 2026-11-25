# Definition probe in VS Code (C8 follow-up)

Asks VS Code's own definition provider, served by the rust-analyzer extension, for the definition of `ApiResult` at two
positions of vaultwarden until the answers stay the same for a minute, and writes them to a JSON file. It answers a
maintainer's request (rust-lang/rust-analyzer#23433) to check the report in a common editor. Results of 2026-10-07 are in
`data/lsptest/runs/main_v1/evidence/c8_vscode/` (VS Code 1.140.0, extension 0.3.3073, server 2026-10-04; default settings and
`rust-analyzer.cargo.features = ["sqlite"]`).

Steps (macOS; the user data directory must have a short path, since VS Code puts its IPC socket there):

1. `code --extensions-dir EXT --user-data-dir USER --install-extension rust-lang.rust-analyzer`
2. Copy the project at the pinned commit without `target/` and `.git/`; fill `ws` and `out` in `test/config.json`.
3. Put the settings in `USER/User/settings.json` (`rust-analyzer.server.extraEnv.PATH` must reach `cargo`; add
   `rust-analyzer.cargo.features` for the second run).
4. `"/Applications/Visual Studio Code.app/Contents/MacOS/Code" --user-data-dir=USER --extensions-dir=EXT --extensionDevelopmentPath=THIS_DIR --extensionTestsPath=THIS_DIR/test/index.js --disable-workspace-trust --new-window PROJECT_COPY`

VS Code exits when the probe has written its output.
