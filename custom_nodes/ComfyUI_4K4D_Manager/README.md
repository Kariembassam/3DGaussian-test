# ComfyUI-4K4D-Manager

Manager-installable custom node pack that adapts 4K4D workflows for Runpod-first ComfyUI operation.

## Included Nodes
- IO: dataset ingest + manifest generation
- Environment: bootstrap planner/executor + strict preflight checker
- Artifacts: resolve/download/manual fallback
- Pipeline: command build + launch/poll/stop with persisted job state
- Viewer: launch + poll

## Runpod behavior
- `env_profile=runpod_official_comfyui` avoids apt assumptions.
- All launch nodes default to `require_env_ok=true`.
- Jobs persist into `workspace/jobs/index.json` and per-job logs.

## Workflows
See `workflows/` including `99_main_one_shot_pipeline.json` for end-to-end wiring.
