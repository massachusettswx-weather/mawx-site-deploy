# WeatherNext 3: surface ensemble means without paid GCP workloads

Status: implementation prepared and tested against small synthetic fixtures. Live
access and the actual source schema still need verification with your approved
Google identity. No cloud project, paid job, scheduler, or website has been enabled.

This adds WN3 to the existing MassachusettsWx viewer and reuses its region registry
and base maps. It reads Google's already-produced surface means from
`weathernext3_statistics_spatial`. It performs no model inference and never reads
the Requester Pays full-ensemble bucket. There is no billing project header.

All supported `*_mean` surface fields present in a run are included, including
station-head fields, gridded temperature/dew point, wind speed and components,
precipitation variants, MSLP, SST, clouds, and radiation. Metadata controls units;
unrecognized units stop the export for inspection rather than being guessed.
No upper-air parameters are supplied in this statistics dataset. Mean wind speed
is read directly, not derived from mean U/V. Precipitation maps show the source
1-hour or 6-hour accumulation, not a spurious total since initialization.

## Install in the existing repository

The delivery ZIP contains complete replacements for modified files and complete
new files under `updated-files/`, plus a git patch. Make a new branch in
`massachusettswx-weather/mawx-site-deploy`, then copy the contents of
`updated-files/` into the repository root, retaining the directory structure.
Do not upload the ZIP itself or the enclosing `updated-files` directory.

For a local checkout, `git apply /path/to/weathernext3.patch` is an alternative.
The patch applies to the repository snapshot identified in `BASE_COMMIT.txt`.
It preserves the existing GFS/IFS/AIFS/WN2 definitions and all old processing code.
WN3 becomes the initially selected viewer model.

## First live check on your Mac

Run from the repository root in Terminal, with Python 3.12 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r wn3/requirements.txt
```

Authentication is still required by Google's source bucket. Use the same Google
account previously approved for WeatherNext; WN2 approval has not yet been verified
against WN3. The local Google CLI can sign in without creating or reopening a paid
project. If it is installed, run:

```bash
gcloud auth application-default login --disable-quota-project
export WN3_CREDENTIALS_FILE="$HOME/.config/gcloud/application_default_credentials.json"
python -m wn3.run --inspect
```

This login overwrites any existing local application-default login, but does not
change the separate gcloud CLI login. Keep credentials on your machine, outside
the repository. Do not paste credentials into chat or commit them.

Alternatively set `WN3_ACCESS_TOKEN` locally to a current OAuth access token for
the approved identity; it expires and is intended for a short manual check.
No account keys or credentials are included in this package.

If authentication or access fails, stop and resolve account allowlisting. Do not
reactivate billing, create another cloud project, or switch to the full-ensemble
bucket as a workaround.

## Generate and view the first cycle locally

After the metadata check passes:

```bash
python -m wn3.run --regions conus --end-hour 48 --step 6
python -m http.server 8000 --bind 127.0.0.1 --directory output/wn3-preview
```

Open http://127.0.0.1:8000/site/ . This uses your existing model viewer, timeline,
region and parameter selectors. Every frame has initialization and valid time.
The preview lists only WN3, since the terminated project's other maps are not
included. The repository retains those models for later recovery.

The initial scope is all supported surface mean parameters, CONUS, f006–f048 at
six-hour intervals. Expand `--regions` and `--end-hour` after measuring runtime.
Use `--output output/wn3-preview-2` for another run: existing output is never
overwritten. Limits are 2,000 frames and 200 MiB per export. They bound local
output, not remote source chunk download volume. Data are selected by variable,
region, and forecast time before loading; actual bytes depend on source chunking.
The first render downloads Natural Earth boundaries for Cartopy.

Output is built in a temporary directory and becomes visible only on completion.
An incomplete or failed update does not replace the previous preview. No raw data
or credentials are copied into the viewer output.

## GitHub-only access check

`.github/workflows/wn3-inspect.yml` adds a manually started, metadata-only check
under Actions. It accepts a short-lived token through the repository Actions
secret `WN3_ACCESS_TOKEN` (Settings → Secrets and variables → Actions).
After adding the secret, run **Inspect WeatherNext 3 access** promptly because
the token expires. Never put a token in a workflow input or public file.

The workflow has a public-repository condition, uses the standard Ubuntu runner,
has a ten-minute timeout, no schedule, no data artifacts, and no dependency cache.
It does not generate or publish maps. Public-repository standard runner compute
is free under GitHub's documented pricing; larger runners and artifact storage
have separate charging rules. Do not replace the runner with a paid larger runner.

## Public hosting and automation: unresolved before deployment

The intended next hosting step is a static site outside GCP, with preprocessing
on free standard GitHub runners or the Mac. No publication workflow is enabled
yet. Google's current real-time terms explicitly exclude mere coloring, formatting,
or regional subsetting from the definition of a Value Added Service. Therefore a
plain public forecast-map viewer needs the applicable permission/use terms resolved
before deploying it. An old initialization does not make future-valid forecasts
historical data. Local internal use is listed separately in the terms.

Once live schema/access and the public-display permission are settled, adapt the
manual exporter into a bounded refresh-and-publish workflow. GitHub Pages currently
has a 1-GB site limit and a 100-GB/month soft bandwidth limit; do not promise a free
global all-fields archive. Store only a bounded latest set, not raw global forecasts.

## Verification

```bash
python -m unittest wn3.test_export -v
node --check site/app.js
```

Tests cover unit conversions, scalar wind handling, descending latitudes, longitude
wrap, rejection of paid source paths, missing-hour detection, viewer file paths,
preservation of existing output, and cleanup after failed generation. They do not
substitute for a live authenticated source check.

## Official references

- Source/schema: https://developers.google.com/weathernext/guides/gcs
- Access: https://developers.google.com/weathernext/guides/access-forecast
- Terms: https://storage.googleapis.com/weathernext-public/terms-of-use.pdf
- Login without quota project: https://docs.cloud.google.com/sdk/gcloud/reference/auth/application-default/login
- GitHub compute/storage pricing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
