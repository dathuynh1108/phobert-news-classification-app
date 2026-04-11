#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROTO_DIR="$ROOT_DIR/model-service/proto"
MODEL_OUT="$ROOT_DIR/model-service/app/generated"
API_OUT="$ROOT_DIR/api-service/app/generated"

mkdir -p "$MODEL_OUT" "$API_OUT"

protoc --proto_path="$PROTO_DIR" --python_out="$MODEL_OUT" "$PROTO_DIR/classifier.proto"
cp "$MODEL_OUT/classifier_pb2.py" "$API_OUT/classifier_pb2.py"

python3 "$ROOT_DIR/model-service/scripts/normalize_generated.py" \
  "$MODEL_OUT/classifier_pb2.py" \
  "$API_OUT/classifier_pb2.py"

touch "$MODEL_OUT/__init__.py" "$API_OUT/__init__.py"
echo "Generated classifier_pb2.py for model-service and synced to api-service."

