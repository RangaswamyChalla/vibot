# Phase 4 Deployment Guide

This guide details how to confidently release the VoiceBot AXIOM Pipeline onto a standard Virtual Private Server (VPS).

## 1. Prerequisites
- Docker & Docker Compose installed natively.
- Minimum 8GB RAM (16GB highly recommended if hosting the Ollama Local LLMs directly on the same machine without splitting architecture).

## 2. Infrastructure Setup & Runbook
1. Securely SSH into your host environment and clone the pipeline repository.
2. Initialize your configurations:
   ```bash
   cp voice-bot/.env.example voice-bot/.env
   # Make sure to set VOICEBOT_API_KEY to a secure random string!
   ```
3. Start the architecture in detached mode:
   ```bash
   docker-compose up -d
   ```
4. Verify all components are healthy and interconnected:
   ```bash
   curl http://localhost:8000/health
   # Ollama should return true if successfully mapped!
   ```

## 3. CI/CD Operations
This repository contains a `.github/workflows/ci.yml` file which automatically validates the integrity of pull requests by executing PyTest runners in isolated environments. No code reaches `main` unless it is proven stable.

## 4. Open Question Resolutions
- **Auth Strategy:** Fully integrated. A mandatory `X-API-Key` header safeguards all incoming REST endpoints (`/api/chat`, etc.). Meanwhile, the `/ws/voice` WebSocket accepts a `?token=` parameter so the secure Streamlit frontend can inject the key natively.
- **Monitoring Configuration:** Prometheus mappings are natively surfaced at `/api/metrics`. Queue depth (`QUEUE_SIZE`) and historical logging can be monitored there via polling by an external visualization tool like Grafana.
- **Rollback Planning:** The usage of `docker-compose.yml` natively implies that to rollback, you simply check out the specific old Git tag, and re-run `docker-compose up -d --build`. 
