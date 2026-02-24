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

---

## 🔐 1️⃣ Authenticate (Device Code / MFA)

```python
import spfetch as sp

client = sp.connect_device_code(
    tenant_id="YOUR_TENANT_ID",
    client_id="YOUR_CLIENT_ID",
)
```

✔️ Works with MFA-enabled accounts  
✔️ No secrets required  
✔️ Ideal for local development  

---

## 📂 2️⃣ List a Folder

```python
items = client.ls(
    site_url="https://tenant.sharepoint.com/sites/MySite",
    folder="/Shared Documents/Reports",
)

for item in items:
    print(item.name, item.is_folder, item.size)
```

Returns structured metadata for files and folders.

---

## ⬇️ 3️⃣ Streaming Download (Recommended for Large Files)

### 🖥️ Download to Local Filesystem

```python
client.download(
    site_url="https://tenant.sharepoint.com/sites/MySite",
    path="/Shared Documents/Big/base.csv",
    dst="stage/base.csv",
)
```

---

### ☁️ Download Directly to Cloud Storage

```python
client.download(
    site_url="https://tenant.sharepoint.com/sites/MySite",
    path="/Shared Documents/Big/base.csv",
    dst="gs://my-bucket/stage/base.csv",  # or s3://... or abfss://...
)
```

🔥 Files are streamed in chunks — no full in-memory loading.

Perfect for large CSVs, parquet files, exports, and data pipelines.

---

## 📊 4️⃣ Read Small Files into pandas (Optional)

```python
df = client.read_excel(
    site_url="https://tenant.sharepoint.com/sites/MySite",
    path="/Shared Documents/Reports/sales.xlsx",
    sheet_name="Base",
    usecols="B:F",
    skiprows=8,
)
```

> ⚠️ For very large files, prefer `download()` and process them using Spark, Dask, or your data engine of choice.

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

- Add tests for new features  
- Keep public APIs documented  
- Maintain backward compatibility when possible  

---

# 📄 License

MIT

---

<p align="center">
  Built for modern data workflows 🚀
</p>
