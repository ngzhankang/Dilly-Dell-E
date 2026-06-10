#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

# ── Frontend ────────────────────────────────────────────────────────────

echo "=> Choose your frontend:"
echo "   [1] Expo (React Native)    — recommended for mobile, no Xcode/Android Studio needed"
echo "   [2] React Native CLI       — bare mobile, requires Xcode or Android Studio"
echo "   [3] Vite (React web)       — web browser app"
echo "   [4] Skip                   — backend only, add frontend manually later"
read -r -p "   Selection [1-4]: " FRONTEND_CHOICE

case "$FRONTEND_CHOICE" in
  1)
    echo ""
    echo "=> Scaffolding Expo app..."
    npx create-expo-app@latest mobile --template
    grep -qxF 'mobile/' .gitignore || echo 'mobile/' >> .gitignore
    ;;
  2)
    echo ""
    echo "=> Scaffolding React Native CLI app..."
    npx react-native@latest init mobile --template react-native-template-typescript
    grep -qxF 'mobile/' .gitignore || echo 'mobile/' >> .gitignore
    ;;
  3)
    echo ""
    echo "=> Scaffolding Vite web app..."
    npm create vite@latest frontend -- --template react-ts
    ;;
  4)
    echo "   Skipping frontend scaffold."
    ;;
  *)
    echo "   Invalid choice, skipping frontend."
    ;;
esac

# ── Backend ─────────────────────────────────────────────────────────────

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

# ── Environment ─────────────────────────────────────────────────────────

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
echo "  1. Fill in .env (MONGO_URI, JWT_SECRET, ML_SERVICE_URL, etc.)"
echo "  2. Run: make docker-up   (start MongoDB + Redis + ML service)"
echo "  3. Run: make dev         (start backend + frontend)"
