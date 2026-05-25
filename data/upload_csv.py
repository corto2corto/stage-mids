from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="corto2corto/articles",
    repo_type="dataset",
    local_dir="/data/elias/stage-mids/data"
)