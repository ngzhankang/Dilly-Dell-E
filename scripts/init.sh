#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "=> Scaffolding frontend..."
npm create vite@latest frontend -- --template react-ts

echo ""
echo "=> Scaffolding backend..."
mkdir -p backend/src/{routes,middleware,config}
cd backend
npm init -y
npm install express cors dotenv zod jsonwebtoken mongoose
npm install -D typescript ts-node nodemon @types/express @types/cors @types/node @types/jsonwebtoken
cd "$ROOT_DIR"

echo ""
echo "=> Copying backend stubs..."
cp docs/snippets/index.ts backend/src/index.ts
cp docs/snippets/env.ts backend/src/config/env.ts
cp docs/snippets/asyncHandler.ts backend/src/middleware/asyncHandler.ts
cp docs/snippets/errorHandler.ts backend/src/middleware/errorHandler.ts
cp docs/snippets/tsconfig.json backend/tsconfig.json
cp docs/snippets/nodemon.json backend/nodemon.json

echo ""
echo "=> Adding backend npm scripts..."
cd backend
npm pkg set scripts.dev="nodemon"
npm pkg set scripts.build="tsc"
npm pkg set scripts.lint="tsc --noEmit"
cd "$ROOT_DIR"

echo ""
echo "=> Setting up .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "   Created .env from .env.example — fill in your secrets."
else
  echo "   .env already exists, skipping."
fi

echo ""
echo "Done. Next steps:"
echo "  1. Fill in .env with your secrets"
echo "  2. Run: make docker-up   (start MongoDB + Redis)"
echo "  3. Run: make dev         (start both servers)"
