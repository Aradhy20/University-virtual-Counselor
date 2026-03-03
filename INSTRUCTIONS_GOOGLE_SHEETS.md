
# How to Enable Lead Saving to Google Sheets

You provided a **Client ID** (`91014751772-...`), which is used for user logins.

For Aditi to automatically save leads to Google Sheets without you logging in every time, she needs a **Service Account Key**.

## Step 1: Get the Service Account Key (JSON)
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts).
2.  Select your project.
3.  Click **+ CREATE SERVICE ACCOUNT**.
    - Name: `aditi-agent` (or similar).
    - Click **Create and Continue**.
4.  Grant Access: Select `Editor` role (optional, but easiest). Click **Done**.
5.  In the list, click on the new service account (e.g., `aditi-agent@...`).
6.  Go to the **KEYS** tab (top menu).
7.  Click **ADD KEY** > **Create new key**.
8.  Select **JSON** and click **CREATE**.
9.  A file will download to your computer.

## Step 2: Add to Project
1.  Rename the downloaded file to: `google_credentials.json`
2.  Move it to this folder: `d:/tmu/university_counselor/`

## Step 3: Share the Sheet
1.  Open your Google Sheet (`1qinO_9LGC4SBFubrIlq88HQIO72QaeCJzLEx7x_EirA`).
2.  Click **Share** (top right).
3.  Copy the **client_email** from your JSON file (it looks like `aditi-agent@project-id.iam.gserviceaccount.com`).
4.  Paste it into the Share box and give **Editor** access.
5.  Click **Send**.

## Step 4: Restart Aditi
Once the file is in place, Aditi will automatically detect it and start saving leads.
