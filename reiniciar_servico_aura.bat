@echo off
cd /d "%~dp0"
title Reiniciando Servico AURA

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0reiniciar_servico_aura.ps1"
