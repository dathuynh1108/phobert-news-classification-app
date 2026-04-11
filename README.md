# VNN ML News Classification App

Monorepo này đang được chia theo service rõ ràng:

- `ui/`: React + Vite UI bám wireframe Figma.
- `api-service/`: FastAPI BFF cho editor/admin/data-scientist.
- `model-service/`: gRPC service host PhoBERT inference.
- `train/`: notebook Colab PhoBERT và script package artifact.
- `dataset/`: parquet dataset và artifact output để `model-service` load.

State mutable của app hiện được persist ở Postgres:

- threshold bands
- article decisions / latest review history
- active model package
- audit log updates

## Proto ownership

`classifier.proto` được đặt trong `model-service/proto/` vì `model-service` là owner của inference contract.

Khi proto đổi, chạy:

```bash
./model-service/scripts/generate_proto.sh
```

Script sẽ:

1. Generate `model-service/app/generated/classifier_pb2.py`
2. Copy file generated sang `api-service/app/generated/classifier_pb2.py`
3. Normalize file generated để tránh runtime-version guard từ `protoc` local

## Start local

### 1. Start `model-service`

```bash
cd model-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Artifact mặc định được load từ:

```text
dataset/artifacts/active/
```

Nếu chưa có model export thật, service sẽ fallback sang heuristic để UI vẫn chạy được.

### 2. Start `postgres`

```bash
docker run --name vnn-postgres \
  -e POSTGRES_DB=vnn_ml \
  -e POSTGRES_USER=vnn \
  -e POSTGRES_PASSWORD=vnn \
  -p 5432:5432 \
  -d postgres:16-alpine
```

### 3. Start `api-service`

```bash
cd api-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Nếu cần đổi gRPC host/port:

```bash
export VNN_AI_SERVICE_HOST=127.0.0.1
export VNN_AI_SERVICE_PORT=50051
export VNN_DB_HOST=127.0.0.1
export VNN_DB_PORT=5432
export VNN_DB_NAME=vnn_ml
export VNN_DB_USER=vnn
export VNN_DB_PASSWORD=vnn
```

### 4. Start `ui`

```bash
cd ui
npm install
npm run dev -- --host 0.0.0.0
```

Mặc định UI gọi:

```text
http://localhost:8000/api
```

Nếu cần đổi:

```bash
export VITE_API_BASE_URL=http://localhost:8000/api
```

## Docker Compose: start all services

Build và chạy toàn bộ stack:

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

Endpoints:

- UI: `http://localhost:5173`
- API: `http://localhost:8000/api/health`
- gRPC model service: `localhost:50051`

## Train flow

1. Đặt parquet vào `dataset/`
2. Mở `train/notebooks/main_PhoBERT.ipynb` trên Colab
3. Train model
4. Package output:

```bash
python train/scripts/package_run.py \
  --model-dir train/runs/model \
  --output-dir dataset/artifacts/active
```

## Notes

- UI hiện đang dùng API seeded data để khớp wireframe trước.
- `api-service` load seed ban đầu vào Postgres nếu DB còn trống.
- `model-service` mặc định chạy fallback heuristic để stack lên nhanh.
- Nếu muốn `model-service` load artifact PhoBERT thật, cài thêm:

```bash
pip install -r model-service/requirements-phobert.txt
```

- Nếu đổi proto, hãy commit lại cả hai file generated trong `model-service/app/generated/` và `api-service/app/generated/`.
