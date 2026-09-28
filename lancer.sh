#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js n'est pas installé. Téléchargez-le sur https://nodejs.org puis relancez ce script."
  exit 1
fi

if [ ! -d node_modules ]; then
  echo "Première utilisation : installation des dépendances..."
  npm install || { echo "L'installation a échoué. Vérifiez votre connexion Internet."; exit 1; }
fi

echo ""
echo "Application : http://localhost:5173  (Ctrl+C pour arrêter)"
echo ""
npm run dev
