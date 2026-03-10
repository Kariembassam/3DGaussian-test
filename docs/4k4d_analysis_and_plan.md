# 4K4D Analysis and Implementation Plan

## Upstream repository analysis summary

### zju3dv/4K4D
- Architecture: dynamic scene reconstruction/training stack with Python entrypoints and CUDA-heavy dependencies.
- Operational flow: dataset prep -> training launch -> periodic monitoring -> visualization/viewer path.
- Dependency profile: PyTorch/CUDA, scientific Python stack, git repo editable install.

### JonathonLuiten/Dynamic3DGaussians
- Provides reference dynamic Gaussian training/runtime behavior and helps infer expected visualization and experiment management patterns.

## Mapped ComfyUI production behavior
1. Strict environment bootstrap + preflight (`EnvBootstrap`, `EnvCheck`)
2. Artifact model resolution + placement (`ArtifactResolve`, `ArtifactDownload`, `ArtifactManualFallback`)
3. Runtime control (`LaunchCommand`, `Poll`, `Stop`) with persistent job index/logs
4. Viewer orchestration (`ViewerLaunch`, `ViewerPoll`)
5. End-to-end one-shot graph (`99_main_one_shot_pipeline.json`)

## Known Gaps
- Model URLs in `model_registry.json` are preconfigured to upstream release-style links and can be overridden if upstream changes naming.
- Exact 4K4D train/view commands may need adaptation to upstream CLI changes.
- Native extension build variance across CUDA versions remains environment dependent.
