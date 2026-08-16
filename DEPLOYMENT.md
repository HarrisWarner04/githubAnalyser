# Deployment Guide

## Transports

| Mode | Command | Use case |
|---|---|---|
| **stdio** | `python server.py` | Local — Claude Desktop, Kiro, Cursor on your machine |
| **HTTP** | `python server.py --http` | Remote VM — any client over the network |

---

## Local (stdio) — No deployment needed

```bash
# Start the server
python server.py
# → Blocks silently, waiting for MCP host on stdin

# Test with MCP Inspector
npx @modelcontextprotocol/inspector python server.py
# → Opens http://localhost:5173
```

### Add to Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "github-analyzer": {
      "command": "python",
      "args": ["C:\\path\\to\\github-analyzer-mcp\\server.py"],
      "env": {
        "GEMINI_API_KEY": "your_key",
        "GROQ_API_KEY": "your_key",
        "GEMINI_MODEL": "gemini-flash-latest",
        "GROQ_MODEL": "llama-3.1-8b-instant"
      }
    }
  }
}
```

### Add to Kiro IDE

Edit `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "github-analyzer": {
      "command": "python",
      "args": ["d:\\MCP Project\\github-analyzer-mcp\\server.py"],
      "env": {
        "GEMINI_API_KEY": "your_key",
        "GROQ_API_KEY": "your_key",
        "GEMINI_MODEL": "gemini-flash-latest",
        "GROQ_MODEL": "llama-3.1-8b-instant"
      }
    }
  }
}
```

---

## VM Deployment (Docker + HTTP transport)

### 1. Provision a Linux VM

Any cloud provider, free tier eligible:

| Provider | Spec | Cost |
|---|---|---|
| AWS EC2 t2.micro | 1 vCPU, 1 GB | Free (12 months) |
| GCP e2-micro | 0.25 vCPU, 1 GB | Free (always free) |
| Azure B1s | 1 vCPU, 1 GB | Free (12 months) |
| DigitalOcean | 1 vCPU, 1 GB | $6/month |

Recommended OS: **Ubuntu 22.04 LTS**

---

### 2. Install Docker on the VM

```bash
# SSH into your VM
ssh user@YOUR_VM_IP

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
```

---

### 3. Upload the project

**Option A — SCP (simple)**
```bash
# From your local machine
scp -r "d:\MCP Project\github-analyzer-mcp" user@YOUR_VM_IP:~/github-analyzer-mcp
```

**Option B — Git (recommended)**
```bash
# Push to GitHub first, then on the VM:
git clone https://github.com/YOUR_USERNAME/github-analyzer-mcp.git
cd github-analyzer-mcp
```

---

### 4. Configure secrets

```bash
cd github-analyzer-mcp
cp .env.example .env
nano .env   # Add GEMINI_API_KEY and GROQ_API_KEY
```

> **Never commit `.env` to git.** It is in `.gitignore`.

---

### 5. Build and run

```bash
# Build image and start container
docker compose up -d --build

# Verify it's running
docker compose ps
docker compose logs -f
```

Expected logs:
```
github-analyzer-mcp  | 2026-08-15 12:00:00 INFO  __main__ — Starting HTTP transport on 0.0.0.0:8000/mcp
github-analyzer-mcp  | INFO:     Application startup complete.
github-analyzer-mcp  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### 6. Open firewall port

```bash
# Ubuntu ufw
sudo ufw allow 8000/tcp
sudo ufw enable
```

On cloud providers also open port 8000 in the security group / firewall rules:
- **AWS**: EC2 → Security Groups → Inbound Rules → Add TCP 8000
- **GCP**: VPC Network → Firewall → Create rule → tcp:8000
- **Azure**: Networking → Inbound port rules → Add TCP 8000

---

### 7. Test the deployment

```bash
# From your browser or curl:
# 1. Interactive Web Dashboard
http://YOUR_VM_IP:8000/

# 2. Health check
curl http://YOUR_VM_IP:8000/api/health

# 3. REST API Analysis
curl -X POST http://YOUR_VM_IP:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/pallets/click"}'

# 4. MCP Protocol streamable HTTP endpoint
curl http://YOUR_VM_IP:8000/mcp
```

---

### 8. Connect MCP clients to the remote server

Update your MCP host config to use HTTP transport:

**Claude Desktop / Kiro / Cursor:**
```json
{
  "mcpServers": {
    "github-analyzer": {
      "url": "http://YOUR_VM_IP:8000/mcp",
      "transport": "http"
    }
  }
}
```

**MCP Inspector (remote test):**
```bash
npx @modelcontextprotocol/inspector --url http://YOUR_VM_IP:8000/mcp
```

---

## Management Commands

```bash
# View logs
docker compose logs -f

# Restart after code changes
docker compose up -d --build

# Stop
docker compose down

# Check resource usage
docker stats
```

---

## Custom Subdomain & HTTPS (Nginx + Let's Encrypt)

Point your subdomain (e.g. `analyzer.yourdomain.com`) to your Azure VM Public IP (DNS **A-record**), then configure Nginx to proxy both the Web UI and MCP protocol with automated SSL:

```bash
# 1. Install Nginx & Certbot on the VM
sudo apt install nginx certbot python3-certbot-nginx -y

# 2. Create Nginx site config: /etc/nginx/sites-available/analyzer
sudo nano /etc/nginx/sites-available/analyzer
```

Paste the following Nginx server block:

```nginx
server {
    listen 80;
    server_name analyzer.yourdomain.com;

    # Allow large analysis timeouts (up to 120s)
    proxy_read_timeout 120s;
    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;

    # Pass all traffic to Docker container on port 8000
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE / Streaming support
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
    }
}
```

```bash
# 3. Enable site and test config
sudo ln -s /etc/nginx/sites-available/analyzer /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 4. Generate free Let's Encrypt SSL certificate
sudo certbot --nginx -d analyzer.yourdomain.com
```

Now you have:
- 🌐 **Web Dashboard**: `https://analyzer.yourdomain.com/`
- 🤖 **MCP Protocol**: `https://analyzer.yourdomain.com/mcp`
- ⚡ **REST API**: `https://analyzer.yourdomain.com/api/analyze`

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio key |
| `GROQ_API_KEY` | ✅ | — | Groq Console key |
| `GITHUB_TOKEN` | ❌ | `""` | Raises GitHub rate limit to 5000/h |
| `GEMINI_MODEL` | ❌ | `gemini-flash-latest` | Run `check_models.py` to find available |
| `GROQ_MODEL` | ❌ | `llama-3.1-8b-instant` | Groq model name |
| `MAX_SOURCE_FILES` | ❌ | `12` | Files fetched per repo |
| `MAX_FILE_SIZE_KB` | ❌ | `80` | Max file size to fetch |
| `MCP_PORT` | ❌ | `8000` | Docker host port mapping |
