import os

# Indique à HF de stocker son cache ici, car sinon conflit avec le cache de ubuntu/.cache
os.environ["HF_HOME"] = "/data/elias/hf_cache"

from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="corto2corto/articles",
    repo_type="dataset",
    local_dir="/data/elias/stage-mids/data",
    token="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"
)
