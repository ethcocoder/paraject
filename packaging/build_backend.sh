#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="${ROOT}/.models/smollm-135m"
VENV="${ROOT}/.venv-packaging"
DIST="${ROOT}/packaging/backend-dist"
PYI_DIST="${ROOT}/desktop-electron/dist/backend"

if [[ ! -s "${MODEL_DIR}/model_q4.onnx" || ! -s "${MODEL_DIR}/tokenizer.json" ]]; then
  echo "Missing bundled model artifacts in ${MODEL_DIR}; download/provide them before packaging." >&2
  exit 2
fi
python3 -m venv "${VENV}"
"${VENV}/bin/python" -m pip install --upgrade pip pyinstaller
"${VENV}/bin/python" -m pip install -e "${ROOT}[camera,discovery,network,onnx,vision]"
rm -rf "${DIST}" "${PYI_DIST}"
"${VENV}/bin/pyinstaller" --noconfirm --clean --onedir --name backend --paths "${ROOT}/src" "${ROOT}/packaging/backend_entry.py"
mkdir -p "${DIST}"
cp -a "${PYI_DIST}/." "${DIST}/"
sha256sum "${MODEL_DIR}/model_q4.onnx" "${MODEL_DIR}/tokenizer.json" > "${DIST}/MODEL_SHA256SUMS.txt"
echo "Bundled backend at ${DIST}; model assets are copied by electron-builder from ${MODEL_DIR}."
