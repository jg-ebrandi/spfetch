# 🚀 spfetch

![spfetch_lg](https://github.com/user-attachments/assets/c66f083b-3899-4482-94da-1f85609b357e)

<p align="center">
  <b>Simple. Streaming. Resilient. MFA-ready.</b><br>
  List and fetch files from <b>SharePoint</b> via <b>Microsoft Graph</b> with clean APIs and cloud-native downloads.
</p>

---

## ✨ What is spfetch?

`spfetch` is an asynchronous Python library built for modern data pipelines:

- 📂 **List** SharePoint folders with structured metadata  
- ⬇️ **Stream** large files directly to Local Disk, S3, GCS, or Azure without memory crashes  
- ⚡ **Smart Buffering** – Control chunk and buffer sizes to optimize Cloud I/O (50+ MB/s)  
- 📊 **Load** small files directly into Pandas DataFrames  
- 🔐 **Authenticate** via MFA (Device Code) or Silent (Client Secret) flows  
- 🛡️ **Auto-Recover** from Microsoft API Throttling (HTTP 429) with Exponential Backoff  

---

## 🚀 Performance Benchmark (v0.1.3)

**Zero Intermediate Disk Architecture + Smart Buffering**

**Benchmark Results**

- **Payload:** 10.10 GB CSV (SharePoint ➡ Azure Data Lake)  
- **Time:** 3m 11s (191.96s)  
- **Average Speed:** 53.87 MB/s  
- **Config:** `chunk_size_mb=1` | `buffer_size_mb=100`

---

## 🏗️ Technical Architecture

The library is designed with a layered approach to ensure high throughput and resilience. By decoupling the reading rate from the writing rate, we maximize the performance of both the Microsoft Graph API and Cloud Providers.

<img width="1771" height="826" alt="diagram-spfetch" src="https://github.com/user-attachments/assets/356f1d0d-a29a-4314-8c7c-c257540aaa1f" />

### The Data Pipeline Flow:
1. **Source (SharePoint):** Chunks are read at a light rate (default 1MB) to avoid API throttling.
2. **Core (Smart Buffer & Router):** Data is accumulated in a memory buffer. The Smart Router dynamically distributes multiple files across isolated Async Workers.
3. **Destination (Cloud):** Once the buffer reaches the set size (e.g., 100MB), a single high-speed write is performed via `fsspec`.
4. **Resilience:** The `@retry_on_429` shield monitors all requests, while internal loop-retries protect individual files from network drops.

---

# 🔐 1. Authentication

Instantiate the client using your Microsoft Entra ID (Azure AD) credentials.

---

### Option A: Interactive / Local (Device Code Flow)

Ideal for local scripts. Supports MFA.

```python
from spfetch.auth import DeviceCodeAuth
from spfetch.client import SharePointClient

auth = DeviceCodeAuth(
    tenant_id="<YOUR_TENANT_ID>",
    client_id="<YOUR_CLIENT_ID>"
)

client = SharePointClient(auth=auth)
```

---

### Option B: Automated / CI/CD (Client Secret Flow)

Ideal for Airflow, Databricks, GitHub Actions.

```python
from spfetch.auth import ClientSecretAuth
from spfetch.client import SharePointClient

auth = ClientSecretAuth(
    tenant_id="<YOUR_TENANT_ID>",
    client_id="<YOUR_CLIENT_ID>",
    client_secret="<YOUR_CLIENT_SECRET>"
)

client = SharePointClient(auth=auth)
```

---

# 📊 2. Telemetry & Dual Progress Bar

By default, `spfetch` does not override your logging configuration (uses `NullHandler`).

To enable structured logs and dual progress bars:

```python
import asyncio
from spfetch.auth import ClientSecretAuth
from spfetch.client import SharePointClient
from spfetch.destinations import LocalDestination
from spfetch import enable_console_logs # <-- Add this line

enable_console_logs() # <-- Add this line

async def main():
    auth = ClientSecretAuth(
        tenant_id="YOUR_TENANT_ID",
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET"
    )

    client = SharePointClient(auth=auth)
    destination = LocalDestination()

    await client.download(
        hostname="your_company.sharepoint.com",
        site_path="/sites/YourSite",
        file_path="/Folder/your_file.csv",
        dest_path="./data/your_file.csv",
        destination=destination
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 🖥️ Expected Terminal Output

```text
🚀 Iniciando Ingestão | Starting Ingestion (Number of files: 3 | concurrency: 3)

✅ INGESTION COMPLETED SUCCESSFULLY
📂 Source | Fonte: Data/file1.csv (1.00 GB)
📍 Destination | Destino: AzureDestination -> abfs://landing/file1.csv (Chunk: 2MB | Buffer: 50MB)

⌛ Total Time | Tempo total: 40.07s
🚀 Started at | Começou em: 2026-03-01 01:41:18
🏁 Finished at | Terminou em: 2026-03-01 01:41:58
⚡ Average Speed | Velocidade média: 25.20 MB/s

📥 Reading | Leitura: 100%|█████████████████████████████████████████████| 1024.0M/1024.0M [00:40<00:00, 25.2MB/s]
📤 Saving  | Salvando: 100%|█████████████████████████████████████████████| 1024.0M/1024.0M [00:40<00:00, 25.2MB/s]
-------------------------------------------------------
```

---

# 📖 3. Exploration – Listing Folders

📦 Installation:

```bash
pip install spfetch
```

```python
import asyncio

async def list_files():
    items = await client.ls(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        folder_path="/Shared Documents/General"
    )

    for item in items:
        print(item["name"], item["size"], item["is_folder"])

asyncio.run(list_files())
```

---

# 🚀 4. Concurrent Batch Downloads & Smart UI

`spfetch` allows you to download multiple files in parallel using the `max_concurrency` parameter. You can pass the files as a Python `List` or as a pipe-separated string `|`.

The library uses an advanced `tqdm` slot-manager to display concurrent progress bars without polluting your terminal. Once a file finishes, the animation disappears and leaves a clean, static audit log behind.

```python
import asyncio
from spfetch.auth import ClientSecretAuth
from spfetch.client import SharePointClient
from spfetch.destinations import AzureDestination

async def main():
    auth = ClientSecretAuth(tenant_id="...", client_id="...", client_secret="...")
    client = SharePointClient(auth=auth)
    azure_dest = AzureDestination(account_name="...", account_key="...")

    # Pass multiple files separated by pipe "|"
    arquivos_origem = "Data/file1.csv | Data/file2.csv | Data/file3.csv"
    arquivos_destino = "abfs://landing/file1.csv | abfs://landing/file2.csv | abfs://landing/file3.csv"

    await client.download(
        hostname="your_company.sharepoint.com",
        site_path="/sites/YourSite",
        file_path=arquivos_origem,
        dest_path=arquivos_destino,
        destination=azure_dest,
        chunk_size_mb=2,
        buffer_size_mb=50,
        max_concurrency=3 # <-- 🚀 3 files will be downloaded simultaneously!
    )

if __name__ == "__main__":
    asyncio.run(main())
```
---

# 🌊 5. Ingestion Workflows

---

## ☁️ A) Azure (ADLS / Blob)

📦 Installation:

```bash
pip install "spfetch[azure]"
```

```python
from spfetch.destinations import AzureDestination
import asyncio

async def download_to_azure():
    destination = AzureDestination(
        account_name="<YOUR_STORAGE_ACCOUNT_NAME>",
        account_key="<YOUR_STORAGE_ACCOUNT_KEY>"
    )

    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.parquet",
        dest_path="abfs://<container>/bronze/file.parquet",
        destination=destination,
        chunk_size_mb=1,
        buffer_size_mb=100
    )

asyncio.run(download_to_azure())
```

---

## ☁️ B) Amazon S3

📦 Installation:

```bash
pip install "spfetch[s3]"
```

```python
from spfetch.destinations import S3Destination
import asyncio

async def download_to_s3():
    destination = S3Destination(
        key="<AWS_ACCESS_KEY_ID>",
        secret="<AWS_SECRET_ACCESS_KEY>"
    )

    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.csv",
        dest_path="s3://<bucket>/raw/file.csv",
        destination=destination,
        chunk_size_mb=1,
        buffer_size_mb=16
    )

asyncio.run(download_to_s3())
```

---

## ☁️ C) Google Cloud Storage (GCS)

📦 Installation:

```bash
pip install "spfetch[gcs]"
```

```python
from spfetch.destinations import GCSDestination
import asyncio

async def download_to_gcs():
    destination = GCSDestination(
        project="<my-gcp-project-id>",
        token="google_default"
    )

    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.csv",
        dest_path="gs://<bucket>/raw/file.csv",
        destination=destination
    )

asyncio.run(download_to_gcs())
```

---

## 💻 D) Local Disk

📦 Installation:

```bash
pip install spfetch
```

```python
from spfetch.destinations import LocalDestination
import asyncio

async def download_local():
    destination = LocalDestination()

    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.csv",
        dest_path="./local_downloads/file.csv",
        destination=destination
    )

asyncio.run(download_local())
```

---

## 📊 E) Read Directly to Pandas

📦 Installation:

```bash
pip install "spfetch[pandas]"
```

```python
import asyncio

async def read_to_memory():
    df = await client.read_df(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Reports/data.xlsx",
        sheet_name="Sheet1",
        skiprows=2,
        usecols="A:D"
    )

    print(df.head())

asyncio.run(read_to_memory())
```

---

# 🛡️ 6. Resilience – Handling Failures

`spfetch` automatically protects your pipeline at two levels:

1. **Microsoft Graph API Throttling (HTTP 429):**
   If `HTTP 429 Too Many Requests` occurs, the execution pauses, reads the `Retry-After` header, applies Exponential Backoff, and retries up to 5 times.
   
2. **Network Drops during Concurrent Downloads:**
   If a file connection drops midway through downloading a batch, its specific worker catches the error, waits 3 seconds, and restarts **only that file** (up to 3 attempts), while other files continue streaming at max speed.

Your pipeline will wait and recover gracefully instead of crashing.

---

# 🤝 Contributing

Pull Requests are welcome.

Before submitting:

```bash
make format
make lint
make test
```

Ensure all tests pass.

---

# 📄 License

MIT License