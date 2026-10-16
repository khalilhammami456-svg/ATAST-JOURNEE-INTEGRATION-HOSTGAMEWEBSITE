@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Journee d'Integration - ATAST ISIMM

where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Node.js n'est pas installe. Telechargez-le sur https://nodejs.org puis relancez ce fichier.
  echo.
  pause
  exit /b 1
)

if not exist node_modules (
  echo  Premiere utilisation : installation des dependances...
  call npm install
  if errorlevel 1 (
    echo  L'installation a echoue. Verifiez votre connexion Internet puis relancez.
    pause
    exit /b 1
  )
)

echo.
echo  Application : http://localhost:5173
echo  Fermez cette fenetre pour arreter l'application.
echo.
call npm run dev
pause
