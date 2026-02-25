# 🚀 spfetch

![spfetch_lg](https://github.com/user-attachments/assets/c66f083b-3899-4482-94da-1f85609b357e)

<p align="center">
  <b>Simple. Streaming. Resilient. MFA-ready.</b><br>
  List and fetch files from <b>SharePoint</b> via <b>Microsoft Graph</b> with clean APIs and cloud-native downloads.
</p>

---

## ✨ What is spfetch?

`spfetch` is an asynchronous Python library built for data pipelines:

- 📂 **List** SharePoint folders with structured metadata.
- ⬇️ **Stream** large files directly to Local Disk, S3, GCS, or Azure without memory crashes.
- 📊 **Load** small files directly into Pandas DataFrames.
- 🔐 **Authenticate** via MFA (Device Code) or Silent (Client Secret) flows.
- 🛡️ **Auto-Recover** from Microsoft API Throttling (HTTP 429) using Exponential Backoff.

---

## 🔐 1. Authentication

Before running any workflow, you must instantiate the client with your Microsoft Entra ID (Azure AD) credentials.

### Option A: Interactive / Local (Device Code Flow)
Ideal for local scripts. Supports MFA.

```python
from spfetch.auth import DeviceCodeAuth
from spfetch.client import SharePointClient

auth = DeviceCodeAuth(tenant_id="<YOUR_TENANT_ID>", client_id="<YOUR_CLIENT_ID>")
client = SharePointClient(auth=auth)
```

### Option B: Automated / CI-CD (Client Secret Flow)
Ideal for Airflow, Databricks, or GitHub Actions.

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

## 📊 2. Telemetry and Progress Bar (Logging)

By default, **spfetch** follows Python's golden rule and does not force any logging configuration on your environment (`NullHandler`). It also automatically silences verbose logs from third-party libraries (such as Azure/S3/GCS SDKs and `httpx`) to keep your terminal clean.

If you are running standalone scripts, Jupyter notebooks, or simply want to visualize the download status in real-time, just import and call the `enable_console_logs()` function. 

This will activate a **native progress bar (via tqdm)** and display bilingual transfer speed metrics (Portuguese/English):

```python
import asyncio
from spfetch.auth import ClientSecretAuth
from spfetch.client import SharePointClient
from spfetch.destinations import LocalDestination

# 1. Import the helper function
from spfetch import enable_console_logs

# 2. Enable clean logs and the progress bar in the terminal
enable_console_logs()

async def main():
    sp_auth = ClientSecretAuth(
        tenant_id="YOUR_TENANT_ID",
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET"
    )
    client = SharePointClient(auth=sp_auth)
    
    # Example using a local destination (can be S3, Azure, GCS, or Pandas)
    my_destination = LocalDestination()

    # The download will now automatically display the progress bar
    await client.download(
        hostname="your_company.sharepoint.com",
        site_path="/sites/YourSite",
        file_path="/Folder/your_file.csv",
        dest_path="./data/your_file.csv",
        destination=my_destination
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## 🖥️ Expected Terminal Output
When enabled, you will get a clean, structured, and bilingual view of the entire operation, regardless of the chosen destination:

```Plaintext
🚀 [INGESTÃO STREAMING | STREAMING INGESTION] Iniciada em | Started at: YYYY-MM-DD HH:MM:SS
📍 Destino | Destination: <DestinationClass> -> path/to/your/destination/file.ext
📂 Origem | Source:  /path/in/sharepoint/file.ext (X.XX GB)
📦 <DestinationClass>: 100%|███████████████████████████████| X.XXG/X.XXG [MM:SS<00:00, XX.XMB/s]

-------------------------------------------------------
✅ INGESTÃO CONCLUÍDA COM SUCESSO | INGESTION COMPLETED SUCCESSFULLY
⏱️ Tempo Total | Total Time: XXX.XXs
⚡ Velocidade Média | Average Speed: XX.XX MB/s
🏁 Finalizado em | Finished at: YYYY-MM-DD HH:MM:SS
-------------------------------------------------------
```

---

## 📖 3. Exploration: Listing Folders

📦 Required Installation:

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

## 🌊 4. Ingestion Workflows

### 💻 Workflow A: Download to Local Disk

📦 Required Installation:

```bash
pip install spfetch
```

```python
from spfetch.destinations import LocalDestination
import asyncio

async def download_local():
    # 1. Setup local destination
    dest = LocalDestination()
    
    # 2. Stream to disk
    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.csv",
        dest_path="./local_downloads/file.csv",  # Local file path
        destination=dest
    )

asyncio.run(download_local())
```

---

### ☁️ Workflow B: Download directly to Azure (ADLS / Blob)

📦 Required Installation:

```bash
pip install "spfetch[azure]"
```

```python
from spfetch.destinations import AzureDestination
import asyncio

async def download_to_azure():
    # 1. Setup Azure credentials
    dest = AzureDestination(
        account_name="<YOUR_STORAGE_ACCOUNT_NAME>",
        account_key="<YOUR_STORAGE_ACCOUNT_KEY>"  # Or sas_token="<YOUR_SAS_TOKEN>"
    )
    
    # 2. Stream directly to Azure (abfs://)
    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.parquet",
        dest_path="abfs://<container_name>/bronze/file.parquet",
        destination=dest
    )

asyncio.run(download_to_azure())
```

---

### ☁️ Workflow C: Download directly to Amazon S3

📦 Required Installation:

```bash
pip install "spfetch[s3]"
```

```python
from spfetch.destinations import S3Destination
import asyncio

async def download_to_s3():
    # 1. Setup AWS credentials
    dest = S3Destination(
        key="<AWS_ACCESS_KEY_ID>",
        secret="<AWS_SECRET_ACCESS_KEY>"
    )
    
    # 2. Stream directly to S3 (s3://)
    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.csv",
        dest_path="s3://<bucket_name>/raw/file.csv",
        destination=dest
    )

asyncio.run(download_to_s3())
```

---

### ☁️ Workflow D: Download directly to Google Cloud Storage (GCS)

📦 Required Installation:

```bash
pip install "spfetch[gcs]"
```

```python
from spfetch.destinations import GCSDestination
import asyncio

async def download_to_gcs():
    # 1. Setup GCS credentials (can use default environment or token path)
    dest = GCSDestination(
        project="<my-gcp-project-id>",
        token="google_default"  # Or path to service_account.json
    )
    
    # 2. Stream directly to GCS (gs://)
    await client.download(
        hostname="<tenant>.sharepoint.com",
        site_path="/sites/<YourSite>",
        file_path="/Shared Documents/Data/file.csv",
        dest_path="gs://<bucket_name>/raw/file.csv",
        destination=dest
    )

asyncio.run(download_to_gcs())
```

---

### 📊 Workflow E: Read directly to Pandas DataFrame

📦 Required Installation:

```bash
pip install "spfetch[pandas]"
```

Ideal for smaller files (`.csv`, `.xlsx`). This method skips saving to disk and loads the file straight into memory.

```python
import asyncio

async def read_to_memory():
    # client.read_df accepts all standard pandas kwargs (sheet_name, sep, skiprows, etc.)
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

## 🛡️ 5. Resilience (Handling HTTP 429)

Microsoft Graph API strictly throttles heavy requests. spfetch handles this out-of-the-box.

If a `429 Too Many Requests` occurs, the client automatically:

- Pauses execution.
- Reads the `Retry-After` header.
- Applies Exponential Backoff.
- Retries seamlessly (up to 5 times for downloads).

Your pipeline won't crash; it will simply wait and recover gracefully.

---

## 🤝 Contributing

PRs are welcome! Check our `CONTRIBUTING.md`. Ensure all tests pass via `make test`.

---

## 📄 License

MIT
