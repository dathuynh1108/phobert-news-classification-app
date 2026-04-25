# Train

This directory contains the PhoBERT Colab notebook and helper scripts for exporting inference artifacts.
The raw dataset lives in the repo-level `dataset/` directory. Model packages live in `train/artifacts/`.

Recommended flow:

1. Upload this repo to Colab or mount it from Google Drive.
2. Open `train/notebooks/main_PhoBERT.ipynb`.
3. Run all cells. If `./dataset` is empty, the notebook downloads `dathuynh1108/vietnamnet-news` from Hugging Face. If you provide only `data_URLs.json`, it can create missing parquet files.
4. After training, package or copy the artifact into `train/artifacts/active/`.

Colab quick start:

Run the notebook from the folder you want to use as the workspace root. It creates `dataset/`, `train/runs/`, and `train/artifacts/` under that current directory.

By default, the notebook downloads the dataset from `https://huggingface.co/datasets/dathuynh1108/vietnamnet-news` into `./dataset`. You can still upload a dataset folder manually or edit `DATASET_DIR` in notebook Section 0.3.

If the Hugging Face dataset is private, add a Colab secret named `HF_TOKEN`; do not hardcode tokens into the notebook.

All Colab/runtime knobs are centralized in notebook Section 0.3:

- `VNN_MAX_ROWS_PER_CLASS=0` trains on the full dataset by default. Keep this for final runs; use a positive value only for quick smoke tests.
- `VNN_PARQUET_BATCH_SIZE=2048` controls parquet read batches.
- `VNN_PREPROCESS_BATCH_SIZE=512` and `VNN_PREPROCESS_N_JOBS=2` control ViTokenizer batches.
- `VNN_RAW_CONTENT_HEAD_WORDS=220` and `VNN_RAW_CONTENT_TAIL_WORDS=80` keep compact head/tail article text in RAM.
- CUDA batch defaults are selected from detected VRAM. Override with `VNN_BATCH_SIZE`, `VNN_GRAD_ACCUM`, `VNN_EVAL_BATCH`, or `VNN_NUM_EPOCHS` only when needed.
- Trainer, cache, smoke-test, and calibration knobs are also defined in Section 0.3, so later notebook cells should not need manual edits.

The notebook was adapted from the upstream repo:

- `https://github.com/dangtai111325/VietNamNet-News-Classification/tree/main/PhoBERT`

To materialize the dataset before opening the notebook:

```bash
python train/scripts/materialize_vietnamnet_dataset.py
```

To package a trained Hugging Face model directory for `model-service`:

```bash
python train/scripts/package_run.py \
  --model-dir train/runs/model \
  --output-dir train/artifacts/active
```

`model-service` installs from its unified `model-service/requirements.txt` file and reads the active artifact from `train/artifacts/active/` by default.

The Model Versions upload screen expects a PhoBERT/Hugging Face artifact folder or a zip of that folder. Required files are:

- `config.json`
- `model.safetensors` or `pytorch_model.bin`
- tokenizer files such as `tokenizer.json`, `tokenizer_config.json`, `vocab.txt`, or `bpe.codes`
- `label_config.json`
- `thresholds.json` is optional; the API creates a default file when it is missing.
