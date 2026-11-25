# [rust-analyzer 2026-09-21] completion edit is not valid (completionInsert:gained)

Draft for the author (not filed). Group `rust-analyzer-r4-completioninsert-gained-completion-e99b79`, signature `rust-analyzer|r4_edits|completionInsert:gained`, case family `completion`.

## Server

- rust-analyzer 2026-09-21; launch `temp/lsp_servers/rust-analyzer-2026-09-21/rust-analyzer`; entry sha256 c960485d618e126a; package version -
- project `iced-rs/iced@0ef42477fb6f` (corpus, commit 0ef42477fb6fe3e7384baf9e324d9f188bd3a240), language rust

## Relation violated

Edit validity (R4): a quick fix must remove the diagnostic it targets without adding errors; formatting and organize imports applied twice must be no-ops; inserting a completion must not introduce a syntax error.

## Minimal steps (LSP)

1. Start rust-analyzer 2026-09-21 on the project root; answer workspace/configuration with the settings under Environment.
2. `textDocument/completion` on `wgpu/src/quad/solid.rs` at line 9, column 9 (LSP position {line: 8, character: 8}); insert the item: the file must not gain a syntax error.

## Expected vs actual

Expected (fresh session / reference):

```json
[]
```

Actual:

```json
[
 "expected `]`, found `(`"
]
```

Project file `wgpu/src/quad/solid.rs`:

```
   1 | use crate::Buffer;
   2 | use crate::graphics::color;
   3 | use crate::quad::{self, Quad};
     ...
   5 | use bytemuck::{Pod, Zeroable};
   6 | use std::ops::Range;
     ...
   8 | /// A quad filled with a solid color.
   9 | #[derive(Clone, Copy, Debug, Pod, Zeroable)]
  10 | #[repr(C)]
  11 | pub struct Solid {
  12 |     /// The background color data of the quad.
  13 |     pub color: color::Packed,
     ...
  15 |     /// The [`Quad`] data of the [`Solid`].
  16 |     pub quad: Quad,
  17 | }
     ...
  19 | #[derive(Debug)]
  20 | pub struct Layer {
  21 |     instances: Buffer<Solid>,
  22 |     instance_count: usize,
  23 | }
     ...
  25 | impl Layer {
  26 |     pub fn new(device: &wgpu::Device) -> Self {
  27 |         let instances = Buffer::new(
  28 |             device,
  29 |             "iced_wgpu.quad.solid.buffer",
  30 |             quad::INITIAL_INSTANCES,
  31 |             wgpu::BufferUsages::VERTEX | wgpu::BufferUsages::COPY_DST,
  32 |         );
     ...
  34 |         Self {
  35 |             instances,
  36 |             instance_count: 0,
  37 |         }
  38 |     }
     ...
  40 |     pub fn prepare(
  41 |         &mut self,
  42 |         device: &wgpu::Device,
  43 |         encoder: &mut wgpu::CommandEncoder,
  44 |         belt: &mut wgpu::util::StagingBelt,
  45 |         instances: &[Solid],
  46 |     ) {
  47 |         let _ = self.instances.resize(device, instances.len());
  48 |         let _ = self.instances.write(encoder, belt, 0, instances);
     ...
  50 |         self.instance_count = instances.len();
  51 |     }
  52 | }
     ...
  54 | #[derive(Debug, Clone)]
  55 | pub struct Pipeline {
  56 |     pipeline: wgpu::RenderPipeline,
  57 | }
     ...
  59 | impl Pipeline {
  60 |     pub fn new(
  61 |         device: &wgpu::Device,
  62 |         format: wgpu::TextureFormat,
  63 |         constants_layout: &wgpu::BindGroupLayout,
  64 |     ) -> Self {
  65 |         let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
  66 |             label: Some("iced_wgpu.quad.solid.pipeline"),
  67 |             bind_group_layouts: &[Some(constants_layout)],
  68 |             immediate_size: 0,
  69 |         });
     ...
  71 |         let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
  72 |             label: Some("iced_wgpu.quad.solid.shader"),
  73 |             source: wgpu::ShaderSource::Wgsl(std::borrow::Cow::Borrowed(concat!(
  74 |                 include_str!("../shader/quad/snap.wgsl"),
  75 |                 "\n",
  76 |                 include_str!("../shader/color.wgsl"),
  77 |                 "\n",
  78 |                 include_str!("../shader/quad.wgsl"),
  79 |                 "\n",
  80 |                 include_str!("../shader/vertex.wgsl"),
  81 |                 "\n",
  82 |                 include_str!("../shader/quad/shadow.wgsl"),
  83 |                 "\n",
  84 |                 include_str!("../shader/quad/solid.wgsl"),
  85 |             ))),
  86 |         });
     ...
  88 |         let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
  89 |             label: Some("iced_wgpu.quad.solid.pipeline"),
  90 |             layout: Some(&layout),
  91 |             vertex: wgpu::VertexState {
  92 |                 module: &shader,
  93 |                 entry_point: Some("solid_vs_main"),
  94 |                 buffers: &[wgpu::VertexBufferLayout {
  95 |                     array_stride: std::mem::size_of::<Solid>() as u64,
  96 |                     step_mode: wgpu::VertexStepMode::Instance,
  97 |                     attributes: &wgpu::vertex_attr_array!(
  98 |                         // Color
  99 |                         0 => Float32x4,
 100 |                         // Position
 101 |                         1 => Float32x2,
 102 |                         // Size
 103 |                         2 => Float32x2,
 104 |                         // Border color
 105 |                         3 => Float32x4,
 106 |                         // Border radius
 107 |                         4 => Float32x4,
 108 |                         // Border width
 109 |                         5 => Float32,
 110 |                         // Shadow color
 111 |                         6 => Float32x4,
 112 |                         // Shadow offset
 113 |                         7 => Float32x2,
 114 |                         // Shadow blur radius
 115 |                         8 => Float32,
 116 |                         // Snap
 117 |                         9 => Uint32,
 118 |                     ),
 119 |                 }],
 120 |                 compilation_options: wgpu::PipelineCompilationOptions::default(),
     ... (truncated)
```

## Environment

- macOS-27.0-arm64-arm-64bit-Mach-O, Python 3.14.7, 10 CPUs
- client: scripts/lsp_repro (capabilities.client_capabilities); timing settled; settle timeout 300.0 s; request timeout 30.0 s
- workspace settings: the tool defaults (driver.SESSION_SETTINGS and the launch spec)

## Reproduce

```
python3 scripts/lsptest/repro_violation.py data/lsptest/runs/main_v2/triage/rust-analyzer-r4-completioninsert-gained-completion-e99b79/repro.json
```

## Evidence and reduction

- representative 29862883b83e-v00: confirmed 3/3 (each replay: fresh baseline, fresh control and a fresh case session)
- ops 0 -> 0 (0 probes, 0.0 s, reduced ops confirmed 3/3); query targets narrowed to the key
- lines: not reduced
- group: 3 violation(s) in 3 run(s), projects casey/just@6119e6aff518, iced-rs/iced@0ef42477fb6f, tokio-rs/tokio@3930bd182cb1, timings settled, seeds 1, 2

## Possibly related issues (search results, to be checked by the author)

- none found
- queries: `completionInsert unexpected repo:rust-lang/rust-analyzer is:issue`; `completionInsert "wrong edit" repo:rust-lang/rust-analyzer is:issue`

## Server log excerpt (last confirming replay)

```
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20261118-235823-5d028c] stderr: 2026-11-18T23:58:27.112854-08:00  WARN cyclic deps: iced(Idx::<CrateBuilder>(24)) -> iced(Idx::<CrateBuilder>(24)), alternative path: iced(Idx::<CrateBuilder>(24))
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20261118-235823-5d028c] stderr: 2026-11-18T23:58:27.112985-08:00  WARN cyclic deps: iced_widget(Idx::<CrateBuilder>(101)) -> iced_widget(Idx::<CrateBuilder>(101)), alternative path: iced_widget(Idx::<CrateBuilder>(101))
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20261118-235823-5d028c] stderr: 2026-11-18T23:58:36.469105-08:00  WARN cyclic deps: iced(Idx::<CrateBuilder>(24)) -> iced(Idx::<CrateBuilder>(24)), alternative path: iced(Idx::<CrateBuilder>(24))
[rust-analyzer-2026-09-21-tre99b79-r4-replay-case-20261118-235823-5d028c] stderr: 2026-11-18T23:58:36.469517-08:00  WARN cyclic deps: iced_widget(Idx::<CrateBuilder>(101)) -> iced_widget(Idx::<CrateBuilder>(101)), alternative path: iced_widget(Idx::<CrateBuilder>(101))
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20261118-235907-289836] stderr: 2026-11-18T23:59:10.922586-08:00  WARN cyclic deps: iced(Idx::<CrateBuilder>(24)) -> iced(Idx::<CrateBuilder>(24)), alternative path: iced(Idx::<CrateBuilder>(24))
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20261118-235907-289836] stderr: 2026-11-18T23:59:10.922661-08:00  WARN cyclic deps: iced_widget(Idx::<CrateBuilder>(101)) -> iced_widget(Idx::<CrateBuilder>(101)), alternative path: iced_widget(Idx::<CrateBuilder>(101))
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20261118-235907-289836] stderr: 2026-11-18T23:59:19.349467-08:00  WARN cyclic deps: iced(Idx::<CrateBuilder>(24)) -> iced(Idx::<CrateBuilder>(24)), alternative path: iced(Idx::<CrateBuilder>(24))
[rust-analyzer-2026-09-21-tre99b79-r4-replay-control-20261118-235907-289836] stderr: 2026-11-18T23:59:19.34958-08:00  WARN cyclic deps: iced_widget(Idx::<CrateBuilder>(101)) -> iced_widget(Idx::<CrateBuilder>(101)), alternative path: iced_widget(Idx::<CrateBuilder>(101))
```
