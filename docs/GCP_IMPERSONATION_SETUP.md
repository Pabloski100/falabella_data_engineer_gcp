# Connecting Airflow (Docker) to BigQuery and Cloud Storage with Service Account Impersonation

This guide sets up BigQuery and Cloud Storage access for the Airflow Docker Compose
project **without downloading a service account JSON key**.

Instead of a long-lived key file, Airflow authenticates as *your* Google account and
borrows a short-lived token (1 hour) that acts as a service account. Nothing secret
ever lands in the repo.

## How it works

Three identities are involved:

1. **You** — your Google account. The *source* identity.
2. **The service account** (`airflow-bq@PROJECT_ID.iam.gserviceaccount.com`) — the
   *target*. It holds the GCP permissions.
3. **BigQuery / Cloud Storage** — the resources being accessed.

Airflow starts with your credentials, calls the IAM Credentials API to request a token
that acts as the service account, and uses that token against GCP. Your own account
never needs BigQuery or Storage permissions — only permission to borrow the service
account.

The token is scoped to `cloud-platform`, so a single service account and a single
Airflow connection cover every GCP service. Adding a new service later means granting
IAM roles only — no Docker or connection changes.

When this later moves to Cloud Composer or GKE, only identity #1 changes. The service
account, the DAG code and the Airflow connection stay identical.

---

## Prerequisites

- `gcloud` CLI installed and able to reach your project
- Docker and Docker Compose
- On the GCP project: `roles/iam.serviceAccountAdmin` and `roles/resourcemanager.projectIamAdmin`
  (Owner covers both) — needed for steps 2–5 only
- A BigQuery dataset and a Cloud Storage bucket to work against

Set these once; every command below reuses them. Re-export them in any new terminal:

```bash
export PROJECT_ID="your-project-id"          # gcloud config get-value project
export SA_NAME="airflow-bq"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export MY_EMAIL=$(gcloud config get-value account)
export BUCKET_NAME="your-bucket-name"        # bare name, no gs:// prefix

echo "$PROJECT_ID / $SA_EMAIL / $MY_EMAIL / gs://$BUCKET_NAME"   # sanity check
```

Store the bucket name without `gs://`. Airflow's GCS operators want the bare name
(`bucket_name="my-bucket"`) while `gcloud storage` wants the URL form, so adding the
prefix at the call site keeps one variable usable in both places.

---

## Step 1 — Enable the required APIs

`iamcredentials.googleapis.com` is the one that is easy to miss, and its error message
is not obvious.

```bash
gcloud services enable \
  iamcredentials.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT_ID"
```

## Step 2 — Create the service account

```bash
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Airflow BigQuery" \
  --project="$PROJECT_ID"
```

Do **not** run `gcloud iam service-accounts keys create`. That produces the key file
this setup exists to avoid.

## Step 3 — Grant BigQuery permissions to the service account

Two roles are needed. Missing the first one is the most common initial failure.

```bash
# Permission to run query jobs — must be granted at project level
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.jobUser"

# Permission to read/write table data
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.dataEditor"
```

`jobUser` lets it *start* a query; `dataEditor` lets it *touch data*. Both are required.

Project-wide `dataEditor` is fine for a test project. For anything that matters, scope
it to specific datasets instead (BigQuery console → dataset → Sharing → Permissions).

## Step 4 — Grant Cloud Storage access to the bucket

Unlike the BigQuery roles above, grant this **on the bucket** rather than the project.
It is barely more work and limits the service account to the one bucket it needs.

```bash
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"
```

Use `roles/storage.objectUser` instead if the pipeline also needs to write — uploading
files, or letting BigQuery export to GCS. It covers read, write and delete on objects.
Pick one role, not both.

Confirm the binding, and that it is scoped to this bucket only:

```bash
gcloud storage buckets get-iam-policy "gs://${BUCKET_NAME}" \
  --format="table(bindings.role, bindings.members)"

gcloud storage ls "gs://${BUCKET_NAME}/" --impersonate-service-account="$SA_EMAIL"
```

The second command should succeed for this bucket and return 403 for any other bucket
in the project — that is the point of scoping it here.

Notes:

- Object roles do **not** grant `storage.buckets.list`. Listing objects inside a named
  bucket works; listing all buckets in the project does not. Expect that, since the
  error message is confusing otherwise.
- If the bucket lives in a **different project** from the service account, this
  bucket-level binding is the only thing that works — project-level bindings on your own
  project have no effect on it.
- If you previously granted `roles/storage.objectViewer` at project level, remove it or
  the bucket-level scoping buys you nothing:

```bash
gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"
```

## Step 5 — Allow yourself to impersonate the service account

This binding goes **on the service account**, not on the project — note the different
command and the `user:` prefix.

```bash
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="user:${MY_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="$PROJECT_ID"
```

The `user:` prefix is required. Human accounts use `user:`, service accounts use
`serviceAccount:`, groups use `group:`. Using the wrong prefix gives a "does not exist"
error even when the address is valid.

## Step 6 — Verify IAM before touching Docker

Do not skip this. It separates IAM problems from Docker problems.

```bash
gcloud auth login    # if not already authenticated
gcloud auth print-access-token --impersonate-service-account="$SA_EMAIL"
```

A printed token means IAM is correct and everything after this is plumbing. IAM
bindings can take 30–60 seconds to propagate, so retry once before debugging.

## Step 7 — Create Application Default Credentials

This is **separate** from `gcloud auth login`. It writes the credential file that client
libraries — including Airflow's Google provider — read.

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$PROJECT_ID"
```

Log in with the **same account** you granted `serviceAccountTokenCreator` to in step 5.
Picking a different account in the browser (easy with multiple Google logins) causes a
permission error on `iam.serviceAccounts.getAccessToken` later.

The file is written to:

| OS | Path |
|---|---|
| Linux / macOS / WSL | `~/.config/gcloud/application_default_credentials.json` |
| Windows (native gcloud) | `%APPDATA%\gcloud\application_default_credentials.json` |

Confirm it exists before continuing:

```bash
ls -l ~/.config/gcloud/application_default_credentials.json
```

## Step 8 — Configure `.env`

Create `.env` next to `docker-compose.yaml`:

```bash
echo "AIRFLOW_UID=$(id -u)" >> .env
echo "FERNET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" >> .env
```

- **`AIRFLOW_UID`** feeds the compose file's `user: "${AIRFLOW_UID:-50000}:0"`. The ADC
  file is mode `0600` owned by your host user, and bind mounts preserve host UIDs — so
  the container UID must match yours or the read fails. Required on Linux; harmless and
  recommended elsewhere.
- **`FERNET_KEY`** is referenced with no default in the compose file, so leaving it
  unset silently becomes an empty string and Airflow complains about connection
  encryption.

Do not commit `.env`. Commit a `.env.example` with blank values instead.

## Step 9 — Edit `docker-compose.yaml`

Both edits go in the shared `x-airflow-common` block so every service (scheduler,
worker, API server, dag-processor, init) inherits them. Do not move them into a single
service.

Add to the existing `environment:` block — **merge into it, do not add a second
`environment:` key**:

```yaml
    GOOGLE_APPLICATION_CREDENTIALS: /opt/airflow/gcp/adc.json
    GOOGLE_CLOUD_PROJECT: your-project-id
    GCS_BUCKET: your-bucket-name
    AIRFLOW_CONN_GOOGLE_CLOUD_DEFAULT: >-
      {"conn_type": "google_cloud_platform",
       "extra": {"project": "your-project-id",
                 "impersonation_chain": "airflow-bq@your-project-id.iam.gserviceaccount.com"}}
```

Add to the existing `volumes:` list:

```yaml
    - ~/.config/gcloud/application_default_credentials.json:/opt/airflow/gcp/adc.json:ro
```

Notes:

- `/opt/airflow/gcp/adc.json` is an arbitrary name — it only has to match
  `GOOGLE_APPLICATION_CREDENTIALS`. The left side must be a real host path.
- `:ro` mounts read-only. Nothing should write to your credential file. Do **not** add
  `:ro` to `./logs`.
- Mount the single **file**, not the whole `~/.config/gcloud` directory — gcloud writes
  lock files into that directory.
- JSON in `AIRFLOW_CONN_*` requires Airflow 2.3+. On older versions the value must be a
  connection URI.
- The same `google_cloud_default` connection serves BigQuery and Cloud Storage. There is
  no second connection to create, and DAGs never name the service account —
  `BigQueryHook`, `GCSHook` and `GCSToBigQueryOperator` all read the impersonation chain
  from the connection extras.
- Neither the project ID nor the bucket name is a secret, so both can live in the
  committed compose file. Use an Airflow Variable instead if you want to change the
  bucket from the UI without recreating containers.
