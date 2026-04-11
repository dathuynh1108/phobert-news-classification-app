# Dataset

Đặt dữ liệu parquet cho notebook PhoBERT trong thư mục này.

Kỳ vọng tối thiểu:

- `dataset/ban-doc.parquet`
- `dataset/bao-ve-nguoi-tieu-dung.parquet`
- `dataset/bat-dong-san.parquet`
- `...`
- `dataset/van-hoa-giai-tri.parquet`

Artifact inference có thể export vào `dataset/artifacts/active/` để `model-service` load trực tiếp:

- `config.json`
- `model.safetensors` hoặc `pytorch_model.bin`
- tokenizer files
- `label_config.json`
- `thresholds.json`
