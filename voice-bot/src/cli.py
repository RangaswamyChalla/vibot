"""CLI tool for VoiceBot AXIOM management."""
import asyncio
import click
import requests
import json
import os

API_URL = os.getenv("VOICEBOT_API_URL", "http://localhost:8000")
API_KEY = os.getenv("VOICEBOT_API_KEY", "")

def get_headers():
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers

@click.group()
def cli():
    """VoiceBot AXIOM Command Line Interface."""
    pass

@cli.command()
def status():
    """Check API and Ollama status."""
    try:
        r = requests.get(f"{API_URL}/health", headers=get_headers())
        click.echo(json.dumps(r.json(), indent=2))
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")

@cli.command()
def metrics():
    """Show system metrics and queue depth."""
    try:
        r = requests.get(f"{API_URL}/api/metrics", headers=get_headers())
        click.echo(json.dumps(r.json(), indent=2))
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")

@cli.command()
@click.argument('file_path')
def ingest(file_path):
    """Ingest a file into the RAG knowledge base."""
    if not os.path.exists(file_path):
        click.secho(f"File not found: {file_path}", fg="red")
        return
        
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            r = requests.post(f"{API_URL}/api/rag/ingest", files=files, headers=get_headers())
            click.echo(json.dumps(r.json(), indent=2))
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")

if __name__ == "__main__":
    cli()
