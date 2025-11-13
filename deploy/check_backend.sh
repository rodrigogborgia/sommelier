#!/bin/bash
set -e

echo "🔍 Verificando backend..."

# Health principal (si falla, corta el job)
echo "➡️  Chequeando /api/health..."
curl -f http://127.0.0.1:5000/api/health

# Validación opcional del token (si falla, no corta el job)
echo "➡️  Chequeando /api/get-access-token..."
curl -s http://127.0.0.1:5000/api/get-access-token || true

# Test básico de /api/ask (si falla, no corta el job)
echo "➡️  Chequeando /api/ask..."
curl -s -X POST http://127.0.0.1:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"vino"}' || true

echo "✅ Backend verificado"
