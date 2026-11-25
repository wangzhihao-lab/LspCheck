# [rust-analyzer 2026-09-21] quickfix edit is not valid (diagnostics:extra:inactive_code)

Draft for the author (not filed). Group `rust-analyzer-r4-diagnostics-extra-inactive-code-quickfix-f2d641`, signature `rust-analyzer|r4_edits|diagnostics:extra:inactive_code`, case family `quickfix`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `sxyazi/yazi@0ea4c5d9ef75` (corpus, commit 0ea4c5d9ef75d7165c2e3b4eb8d713fc11f26c96), language rust

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. request code actions for the diagnostic {'code': 'inactive_code', 'message': 'code is inactive due to #[cfg] directives: target_os = "linux" is disabled', 'range': {'end': {'character': 2, 'line': 74}, 'start': {'character': 1, 'line': 54}}, 'severity': 4} in `yazi-fs/src/mounts/partition.rs`; apply the quick fix 'Remove all unused imports'; wait until idle: the diagnostic must be gone and no error added.

## Expected vs actual

Expected (fresh session / reference):

```json
[
 [
  33,
  2,
  36,
  3,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ],
 [
  41,
  2,
  44,
  3,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"macos\" is enabled"
 ]
]
```

Actual:

```json
[
 [
  33,
  2,
  36,
  3,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ],
 [
  41,
  2,
  44,
  3,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"macos\" is enabled"
 ],
 [
  54,
  1,
  73,
  2,
  4,
  "inactive_code",
  "rust-analyzer",
  "code is inactive due to #[cfg] directives: target_os = \"linux\" is disabled"
 ]
]
```

Project file `yazi-fs/src/mounts/partition.rs`:

```
   1 | use std::{ffi::OsString, path::PathBuf};
     ...
   3 | #[derive(Debug, Default)]
   4 | pub struct Partition {
   5 | 	pub src:         OsString,
   6 | 	pub dist:        Option<PathBuf>,
   7 | 	#[cfg(unix)]
   8 | 	pub(crate) rdev: Option<u64>,
   9 | 	pub label:       Option<OsString>,
  10 | 	pub fstype:      Option<OsString>,
  11 | 	pub capacity:    u64,
  12 | 	pub external:    Option<bool>,
  13 | 	pub removable:   Option<bool>,
  14 | }
     ...
  16 | impl Partition {
  17 | 	// Match mount types that do not update directory mtime on changes,
  18 | 	// and should be refreshed frequently.
  19 | 	pub(crate) fn timeless(&self) -> bool {
  20 | 		let b: &[u8] = self.fstype.as_ref().map_or(b"", |s| s.as_encoded_bytes());
  21 | 		matches!(b, b"exfat")
  22 | 	}
     ...
  24 | 	// Match mount types that do not reliably emit change notifications,
  25 | 	// and should be polled for changes.
  26 | 	pub(crate) fn soundless(&self) -> bool {
  27 | 		let b: &[u8] = self.fstype.as_ref().map_or(b"", |s| s.as_encoded_bytes());
  28 | 		matches!(b, b"fuse.rclone" | b"nfs4")
  29 | 	}
     ...
  31 | 	#[rustfmt::skip]
  32 | 	pub fn systemic(&self) -> bool {
  33 | 		let _b: &[u8] = self.fstype.as_ref().map_or(b"", |s| s.as_encoded_bytes());
  34 | 		#[cfg(target_os = "linux")]
  35 | 		{
  36 | 			matches!(_b, b"autofs" | b"binfmt_misc" | b"bpf" | b"cgroup2" | b"configfs" | b"debugfs" | b"devpts" | b"devtmpfs" | b"fuse.gvfsd-fuse" | b"fusectl" | b"hugetlbfs" | b"mqueue" | b"proc" | b"pstore" | b"ramfs" | b"securityfs" | b"sysfs" | b"tmpfs" | b"tracefs")
  37 | 		}
  38 | 		#[cfg(target_os = "macos")]
  39 | 		{
  40 | 			_b.is_empty()
  41 | 		}
  42 | 		#[cfg(not(any(target_os = "linux", target_os = "macos")))]
  43 | 		{
  44 | 			false
  45 | 		}
  46 | 	}
  47 | }
     ...
  49 | impl Partition {
  50 | 	#[cfg(any(target_os = "linux", target_os = "macos"))]
  51 | 	pub(super) fn new(name: &std::ffi::OsStr) -> Self {
  52 | 		Self { src: std::path::Path::new("/dev/").join(name).into(), ..Default::default() }
  53 | 	}
     ...
  55 | 	#[cfg(target_os = "linux")]
  56 | 	pub(super) fn dev_name(&self, full: bool) -> Option<&std::ffi::OsStr> {
  57 | 		use std::os::unix::ffi::OsStrExt;
     ...
  59 | 		let s = std::path::Path::new(&self.src).strip_prefix("/dev/").ok()?.as_os_str();
  60 | 		if full {
  61 | 			return Some(s);
  62 | 		}
     ...
  64 | 		let b = s.as_bytes();
  65 | 		if b.len() < 3 {
  66 | 			None
  67 | 		} else if b.starts_with(b"sd") || b.starts_with(b"hd") || b.starts_with(b"vd") {
  68 | 			Some(std::ffi::OsStr::from_bytes(&b[..3]))
  69 | 		} else if b.starts_with(b"nvme") || b.starts_with(b"mmcblk") {
  70 | 			let n = b.iter().position(|&b| b == b'p').unwrap_or(b.len());
  71 | 			Some(std::ffi::OsStr::from_bytes(&b[..n]))
  72 | 		} else {
  73 | 			None
  74 | 		}
  75 | 	}
  76 | }
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v1/triage/rust-analyzer-r4-diagnostics-extra-inactive-code-quickfix-f2d641/repro.json
```

## Evidence and reduction

- representative 11b3a40bbec3-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 2 violation(s) in 2 run(s), projects alacritty/alacritty@d692748d3f61, sxyazi/yazi@0ea4c5d9ef75, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- [rust-lang/rust-analyzer#16642](https://github.com/rust-lang/rust-analyzer/issues/16642) When using code actions for quick fix, multiple possible options were not split (open, 2024-02-23, 6 comments)
- [rust-lang/rust-analyzer#15733](https://github.com/rust-lang/rust-analyzer/issues/15733) Import quick fix offers duplicate options (open, 2023-10-09, 0 comments)
- [rust-lang/rust-analyzer#11039](https://github.com/rust-lang/rust-analyzer/issues/11039) Quick fix to declare an unresolved lifetime (open, 2021-12-17, 1 comments)
- [rust-lang/rust-analyzer#14373](https://github.com/rust-lang/rust-analyzer/issues/14373) Consider present type aliases when using quick fixes (open, 2023-03-18, 2 comments)
- [rust-lang/rust-analyzer#14189](https://github.com/rust-lang/rust-analyzer/issues/14189) Quick Fix options for implementing individual default members (open, 2023-02-22, 0 comments)
- [rust-lang/rust-analyzer#23193](https://github.com/rust-lang/rust-analyzer/issues/23193) FP `expected &&&u32, found &&&&&&&&&&&&&&&&&&&&&&&&&i32` (open, 2026-08-19, 5 comments)
- [rust-lang/rust-analyzer#13317](https://github.com/rust-lang/rust-analyzer/issues/13317) Runnables: Extra Args sets Args instead of Extra Args (open, 2022-09-30, 0 comments)
- [rust-lang/rust-analyzer#19491](https://github.com/rust-lang/rust-analyzer/issues/19491) Too many arguments generates two diagnostics (open, 2025-04-01, 13 comments)
- queries: `"quick fix" in:title repo:rust-lang/rust-analyzer is:issue`; `diagnostics extra repo:rust-lang/rust-analyzer is:issue`; `diagnostics "quick fix" repo:rust-lang/rust-analyzer is:issue`; `diagnostics "wrong edit" repo:rust-lang/rust-analyzer is:issue`
