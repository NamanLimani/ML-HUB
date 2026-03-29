
#  Decentralized ML Hub (Federated Learning Platform)

Welcome to the **Decentralized ML Hub**, an end-to-end Federated Learning platform. This project allows multiple remote Edge Nodes (like personal laptops or hospital servers) to collaboratively train a central Artificial Intelligence model **without ever sharing their private raw data**. 

Instead of uploading sensitive datasets to the cloud, the Hub sends the neural network to the Edge Nodes. The nodes train the model locally and only send the "learned math" (model weights) back to the cloud, where they are aggregated into a smarter global model.

---

## Live Demo & Links
* **Admin Dashboard (Web):** `ml-hub-hard.vercel.app/login`
* **Edge Node Desktop App (macOS):** `https://github.com/NamanLimani/ML-HUB/releases/download/dmg/MLHub.Edge-1.0.0-arm64.dmg`

> **IMPORTANT CLOUD DISCLAIMER:** The central backend API is hosted on Koyeb's free tier. If the platform has not been used for a while, the Koyeb instance will "go to sleep." **If the Admin Dashboard fails to fetch data, simply log into Koyeb and click "Redeploy" to wake the server up.**

---

##  Core Concepts
* **Federated Learning:** Training algorithms across decentralized edge devices holding local data samples, without exchanging them.
* **Edge Computing:** Bringing computation and data storage closer to the location where it is needed (the user's machine) to save bandwidth and improve privacy.
* **The "Trojan Horse" Architecture:** The desktop app looks like a simple React UI, but it secretly contains a massive, fully-compiled PyTorch Python engine inside it. It executes complex ML training natively without requiring the user to install Docker, Python, or use the terminal.

##  Tech Stack & Libraries
* **Backend Hub:** FastAPI (Python), PostgreSQL, Redis.
* **Asynchronous Workers:** Celery (handles heavy model aggregation).
* **Machine Learning:** PyTorch, Torchvision.
* **Frontend (Admin):** React.js, Tailwind CSS, Vite.
* **Edge Node Client:** Electron.js (Desktop App wrapper), React.js (UI).
* **Compiler:** PyInstaller (Freezes the PyTorch pipeline into a standalone native executable).
* **Cloud Infrastructure:** Koyeb (API hosting), Vercel (Web hosting), Neon (Serverless Postgres), Upstash (Serverless Redis).

---

##  Prerequisites & Account Setup (For Developers)

If you want to clone this repository and set up your own cloud Hub, you will need to create free accounts for the following services and replace the connection URLs in the code:

1. **[Neon.tech](https://neon.tech/):** Create a Serverless PostgreSQL database. Get the connection string for `DATABASE_URL`.
2. **[Upstash](https://upstash.com/):** Create a Serverless Redis database. Get the connection string for `REDIS_URL` / Celery Broker.
3. **[Koyeb](https://www.koyeb.com/):** For deploying the FastAPI Backend and Celery Worker.
4. **[Vercel](https://vercel.com/):** For deploying the React Admin Dashboard.
5. **[Docker](https://www.docker.com/) (Local Dev Only):** Required if you want to run the Hub entirely on your local machine.

---

##  How to Run the Platform

There is a distinct difference between running the platform **Locally** (for development) and deploying it to the **Cloud** (for production).

### Option A: Running Locally (Development Mode)
Running locally simulates the entire cloud environment on your personal machine using Docker.

**1. Start the Hub Infrastructure**
Open your terminal in the root project folder and spin up the Postgres database and Redis broker:
```bash
docker-compose up -d
```

**2. Start the FastAPI Backend & Celery Worker**
*(Open two separate terminal windows in your Python virtual environment)*
```bash
# Terminal 1: Start the API
uvicorn main:app --reload --port 8000

# Terminal 2: Start the background worker
celery -A worker.celery_app worker --loglevel=info
```

**3. Start the Admin Web UI**
```bash
cd web-ui
npm install
npm run dev
```

**4. Start the Edge Node Client (Developer Mode)**
```bash
cd client-ui
npm install
npm run electron
```

### Option B: Running in the Cloud (Production Mode)
In production, you do not need `docker-compose`. The databases and APIs live on the internet.

**1. Deploy the Backend**
* Push the code to GitHub.
* Connect your repo to **Koyeb**.
* Add your Neon and Upstash connection strings as Environment Variables.
* Deploy the web service (FastAPI) and a separate worker service (Celery) using the same repository.

**2. Deploy the Admin Web UI**
* Connect your repo to **Vercel**.
* Change the API base URL in the React code to point to your new Koyeb domain (e.g., `https://your-app.koyeb.app`).
* Deploy.

**3. Build the Standalone Mac App (The Edge Node)**
To distribute the app to clients (like a hospital), you must compile the Python ML engine and pack it into a Mac `.dmg`. No Docker required for the end user!

```bash
# Step 1: Compile the PyTorch AI Engine into a standalone binary
pyinstaller --name edge_engine --onedir edge_server.py

# Step 2: Move the binary into the Electron folder
cp -r dist/edge_engine client-ui/engine/edge_engine

# Step 3: Package the Mac App
cd client-ui
npm run dist
```
*The final `.dmg` will be generated in `client-ui/release/`. You can now send this file to anyone with a Mac!*

---

##  The End-to-End Workflow

1. **Admin Setup:** An administrator logs into the Web Dashboard and creates a new Training Job (e.g., a CNN for Image Classification).
2. **Initialization:** The Celery worker creates a blank "Round 0" baseline PyTorch model (`.pt` file) and saves it to the cloud registry.
3. **Edge Node Joins:** A user downloads the Mac `.dmg`, opens the app, and logs in.
4. **Local Execution:** The user selects the Job ID and points the app to a local folder containing their private data.
5. **Secure Training:** The Edge App downloads the global model via HTTP REST, trains it natively using local hardware, and uploads **only the updated weights** back to the Hub.
6. **Aggregation:** Once enough nodes submit their weights, the Hub mathematically averages them into a newly improved "Round 1" global model. 


