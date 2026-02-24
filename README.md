# 🚀 spfetch

![spfetch_lg](https://github.com/user-attachments/assets/c66f083b-3899-4482-94da-1f85609b357e)



<p align="center">
  <b>Simple. Streaming. MFA-ready.</b><br>
  List and fetch files from <b>SharePoint</b> via <b>Microsoft Graph</b> with clean APIs and cloud-native downloads.
</p>

---

## ✨ What is spfetch?

`spfetch` is a Python library to:

- 📂 List SharePoint folders  
- ⬇️ Download files in streaming mode  
- ☁️ Send files directly to S3 / GCS / ADLS  
- 🔐 Authenticate with MFA (Device Code Flow)  
- 📊 Optionally read small files into pandas  

Built for data engineers and analytics workflows that need reliability and simplicity.

---

## 🤔 Why?

Accessing SharePoint programmatically usually involves:

- 🔐 Complex authentication flows (MFA included)  
- 🔎 Confusing browser URLs vs API paths  
- 🚦 Throttling (HTTP 429)  
- 🧠 Memory issues when handling large files  

`spfetch` solves this with:

- ✅ MFA-compatible authentication  
- ✅ Streaming-first downloads (no full in-memory load)  
- ✅ fsspec integration (cloud-native destinations)  
- ✅ Minimal and explicit API  

---

## 📦 Installation

### Core

```bash
pip install spfetch
```

---

### ☁️ Cloud destinations (optional)

```bash
pip install spfetch[s3]     # Amazon S3 (s3fs)
pip install spfetch[gcs]    # Google Cloud Storage (gcsfs)
pip install spfetch[azure]  # Azure Data Lake (adlfs)
```

---

### 📊 Pandas helpers (optional)

```bash
pip install spfetch[pandas]
```

---

# 🚀 Quickstart
Since spfetch is built for modern data engineering, all network operations are asynchronous.

---

## 🔐 1️⃣ Authenticate (Device Code / MFA)

For Local Development (Device Code / MFA)
Works with MFA-enabled accounts. No secrets required.

```python
from spfetch.auth import DeviceCodeAuth
from spfetch.client import SharePointClient

auth = DeviceCodeAuth(
    tenant_id="YOUR_TENANT_ID",
    client_id="YOUR_CLIENT_ID"
)
client = SharePointClient(auth=auth)
```

✔️ Works with MFA-enabled accounts  
✔️ No secrets required  
✔️ Ideal for local development  

For CI/CD & Automated Pipelines (Client Secret)

```python
from spfetch.auth import ClientSecretAuth

auth = ClientSecretAuth(
    tenant_id="YOUR_TENANT_ID",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)
client = SharePointClient(auth=auth)
```

---

## 📂 2️⃣ List a Folder

```python
import asyncio

async def main():
    items = await client.ls(
        hostname="tenant.sharepoint.com",
        site_path="/sites/MySite",
        folder_path="/Shared Documents/Reports"
    )

    for item in items:
        icon = "📁" if item["is_folder"] else "📄"
        print(f"{icon} {item['name']} | Size: {item['size']} | ID: {item['id']}")

asyncio.run(main())
```

Returns structured metadata for files and folders.

---

## ⬇️ 3️⃣ Streaming Download (Recommended for Large Files)
🔥 Files are streamed in chunks — no full in-memory loading. Perfect for large CSVs, parquet files, and data pipelines.

### 🖥️ Download to Local Filesystem

```python
async def main():
    await client.download(
        hostname="tenant.sharepoint.com",
        site_path="/sites/MySite",
        file_path="/Shared Documents/Big/base.csv",
        dest_path="stage/base.csv"
    )
```

---

### ☁️ Download Directly to Cloud Storage

```python
from spfetch.destinations import S3Destination
# from spfetch.destinations import AzureDestination, GCSDestination

async def main():
    # Pass your cloud credentials configuration
    s3_dest = S3Destination(key="AWS_KEY", secret="AWS_SECRET")

    await client.download(
        hostname="tenant.sharepoint.com",
        site_path="/sites/MySite",
        file_path="/Shared Documents/Big/base.csv",
        dest_path="s3://my-bucket/stage/base.csv",
        destination=s3_dest
    )
```

🔥 Files are streamed in chunks — no full in-memory loading.

Perfect for large CSVs, parquet files, exports, and data pipelines.

---

## 📊 4️⃣ Read Small Files into pandas (Optional)
`read_df` automatically detects `.csv`, `.xlsx`, or `.xls` and loads it into memory without writing to disk.

```python
async def main():
    df = await client.read_df(
        hostname="tenant.sharepoint.com",
        site_path="/sites/MySite",
        file_path="/Shared Documents/Reports/sales.xlsx",
        sheet_name="Base", # Passed down to pandas
        usecols="B:F",
        skiprows=8
    )
    print(df.head())
```

> ⚠️ For very large files, prefer `download()` and process them using Spark, Dask, or your data engine of choice.

---

## 🛡️ Resilience (Handling HTTP 429)
`spfetch` includes a built-in resilience layer. If Microsoft Graph throws an `HTTP 429 Too Many Requests` error, the client will automatically:

1. Catch the error.
2. Read the `Retry-After` header provided by Microsoft.
3. Pause execution asynchronously using Exponential Backoff.
4. Retry the request automatically up to `max_retries` (Default: 3 for API calls, 5 for downloads).

Your pipelines will simply wait and recover gracefully.

---

# 🔐 Microsoft Entra ID (Azure AD) Setup

To use `spfetch`, create an **App Registration** in Microsoft Entra ID.

---

## 🧭 Setup Steps

1. Create an **App Registration**
2. Copy the `tenant_id`
3. Copy the `client_id`
4. Enable **Public client flows** (Device Code flow)
5. Grant required Microsoft Graph permissions
6. (If needed) Request **Admin Consent**

---

## 🔑 Required Permissions

Minimum permissions depend on your use case.

### 📖 Read-only access

```
Sites.Read.All
```

### ✍️ Read & Write access

```
Sites.ReadWrite.All
```

Some tenants may require:

- Admin consent  
- Site-specific permission configuration  

---

# 🧱 Design Principles

- 🔐 MFA-first authentication  
- 🌊 Streaming over buffering  
- ☁️ Cloud-native architecture  
- 🧩 Minimal API surface  
- 🔎 Explicit behavior over magic  

---

# 🗺️ Roadmap

Planned features:

- 🔑 `connect_client_secret()` for pipelines / CI  
- 🔄 `sync_folder()` with ETag / Last-Modified support  
- 🧭 Path and URL normalization helpers  
- 📊 Richer metadata filtering  
- 🔁 Configurable retry / backoff strategy  

---

# 🤝 Contributing

PRs are welcome!

Please:

- Check our `CONTRIBUTING.md`.
- Ensure all tests pass `via make test`.
- We use the Conventional Commits specification.

---

# 📄 License

MIT

---

<p align="center">
  Built for modern data workflows 🚀
</p>
