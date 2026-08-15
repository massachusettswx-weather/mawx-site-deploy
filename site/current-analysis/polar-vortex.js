const BUNDLE_URL =
    "../analysis/polar_vortex/10hpa_60n_zonal_wind/bundle.json";

const LATEST_URL =
    "../analysis/polar_vortex/10hpa_60n_zonal_wind/latest.json";

const SVG_NS = "http://www.w3.org/2000/svg";

// A "season" runs July 1 through June 30, so a single winter's
// polar vortex evolution (which straddles the calendar year
// boundary) stays on one line instead of being split across two.
// Season 2026 = Jul 1, 2026 -- Jun 30, 2027, labeled "2026/27".
const SEASON_START_MONTH = 7;

const SEASON_LENGTH_DAYS = 366;


// ============================================================
// SMALL HELPERS
// ============================================================

function setStatus(text, isError) {

    const el = document.getElementById("caStatus");

    el.textContent = text;

    el.classList.toggle(
        "error",
        Boolean(isError)
    );
}


async function fetchJson(url) {

    const response = await fetch(url);

    if (!response.ok) {

        throw new Error(
            `${url} -> HTTP ${response.status}`
        );
    }

    return response.json();
}


function formatDate(dateStr) {

    if (!dateStr) {

        return "—";
    }

    const [year, month, day] = dateStr.split("-");

    const date = new Date(
        Date.UTC(
            parseInt(year, 10),
            parseInt(month, 10) - 1,
            parseInt(day, 10)
        )
    );

    return date.toLocaleDateString(
        "en-US",
        {
            timeZone: "UTC",
            year: "numeric",
            month: "short",
            day: "numeric",
        }
    );
}


// ============================================================
// SEASON BUCKETING (Jul 1 -- Jun 30)
// ============================================================

function seasonForDate(dateStr) {

    const [year, month] = dateStr
        .split("-")
        .map((part) => parseInt(part, 10));

    return month >= SEASON_START_MONTH
        ? year
        : year - 1;
}


function seasonLabel(seasonStartYear) {

    const endYearShort = String(
        (seasonStartYear + 1) % 100
    ).padStart(2, "0");

    return `${seasonStartYear}/${endYearShort}`;
}


function daysFromSeasonStart(dateStr, seasonStartYear) {

    const [year, month, day] = dateStr
        .split("-")
        .map((part) => parseInt(part, 10));

    const start = Date.UTC(
        seasonStartYear,
        SEASON_START_MONTH - 1,
        1
    );

    const current = Date.UTC(year, month - 1, day);

    return Math.round(
        (current - start) / 86400000
    );
}


// Regroup the bundle's calendar-year buckets into season buckets.
// Returns a Map: seasonStartYear -> sorted array of
// { offset, value, date }.
function buildSeasonSeries(bundle) {

    const seasons = new Map();

    Object.keys(bundle.years).forEach((yearKey) => {

        (bundle.years[yearKey] || []).forEach((entry) => {

            const dateStr = entry[0];

            const value = entry[1];

            const seasonStartYear = seasonForDate(dateStr);

            const offset = daysFromSeasonStart(
                dateStr,
                seasonStartYear
            );

            if (!seasons.has(seasonStartYear)) {

                seasons.set(seasonStartYear, []);
            }

            seasons.get(seasonStartYear).push({
                offset,
                value,
                date: dateStr,
            });
        });
    });

    seasons.forEach((points) => {

        points.sort((a, b) => a.offset - b.offset);
    });

    return seasons;
}


// ============================================================
// STAT CARDS
// ============================================================

function renderStats(latest, seasons, currentSeasonYear) {

    document.getElementById("caValue").textContent =
        latest.latest_value_ms !== null &&
        latest.latest_value_ms !== undefined
            ? `${latest.latest_value_ms.toFixed(1)} m/s`
            : "—";

    document.getElementById("caDate").textContent =
        formatDate(latest.latest_date);

    const stateWrap = document.getElementById(
        "caStateBadgeWrap"
    );

    stateWrap.innerHTML = "";

    if (latest.state) {

        const badge = document.createElement("span");

        badge.className = `ca-badge ${latest.state}`;

        badge.textContent =
            latest.state.charAt(0).toUpperCase() +
            latest.state.slice(1);

        stateWrap.appendChild(badge);

    } else {

        stateWrap.textContent = "—";
    }

    document.getElementById("caPercentile").textContent =
        latest.percentile !== null &&
        latest.percentile !== undefined
            ? `${latest.percentile}th`
            : "—";

    document.getElementById("caPercentileSub").textContent =
        latest.percentile_window_days
            ? `vs. ±${latest.percentile_window_days} days, ` +
              `all years (n=${latest.percentile_sample_size || 0})`
            : "";

    const seasonYears = Array.from(seasons.keys()).sort(
        (a, b) => a - b
    );

    document.getElementById("caYears").textContent =
        seasonYears.length
            ? `${seasonLabel(seasonYears[0])} – ` +
              `${seasonLabel(seasonYears[seasonYears.length - 1])}`
            : "—";
}


// ============================================================
// COLOR SCALE
//
// A purple -> teal sequential gradient ordered chronologically
// (oldest = purple, most recent historical season = teal), so
// color itself communicates recency -- not a rainbow of unordered
// hues. The current season is drawn separately in bold accent blue.
// ============================================================

function seasonColor(index, total) {

    const fraction =
        total > 1 ? index / (total - 1) : 0;

    const hue = 275 - fraction * 95; // 275 (purple) -> 180 (teal)

    return `hsl(${hue}, 45%, ${42 + fraction * 15}%)`;
}


// ============================================================
// CHART
// ============================================================

function renderChart(bundle, latest) {

    const wrapper = document.getElementById("caChartWrapper");

    wrapper.innerHTML = "";

    const seasons = buildSeasonSeries(bundle);

    if (seasons.size === 0) {

        wrapper.textContent =
            "No historical data available yet.";

        return { seasons, currentSeasonYear: null };
    }

    const currentSeasonYear = latest.latest_date
        ? seasonForDate(latest.latest_date)
        : Math.max(...seasons.keys());

    const historicalSeasonYears = Array.from(seasons.keys())
        .filter((year) => year !== currentSeasonYear)
        .sort((a, b) => a - b);

    // -------- geometry --------

    const width = 1000;

    const height = 480;

    const margin = {
        top: 14,
        right: 18,
        bottom: 30,
        left: 52,
    };

    const plotWidth = width - margin.left - margin.right;

    const plotHeight = height - margin.top - margin.bottom;

    // -------- value domain --------

    let minValue = 0;

    let maxValue = 0;

    seasons.forEach((points) => {

        points.forEach((point) => {

            if (point.value < minValue) minValue = point.value;

            if (point.value > maxValue) maxValue = point.value;
        });
    });

    const padding =
        Math.max(5, (maxValue - minValue) * 0.08);

    minValue -= padding;

    maxValue += padding;

    const valueRange = maxValue - minValue || 1;

    function xForOffset(offset) {

        return (
            margin.left +
            (offset / SEASON_LENGTH_DAYS) * plotWidth
        );
    }

    function yForValue(value) {

        return (
            margin.top +
            plotHeight -
            ((value - minValue) / valueRange) * plotHeight
        );
    }

    // -------- svg root --------

    const svg = document.createElementNS(SVG_NS, "svg");

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    // -------- y gridlines / labels --------

    const yStep = niceStep(valueRange, 5);

    for (
        let value = Math.ceil(minValue / yStep) * yStep;
        value <= maxValue;
        value += yStep
    ) {

        const y = yForValue(value);

        const line = document.createElementNS(SVG_NS, "line");

        line.setAttribute("x1", margin.left);
        line.setAttribute("x2", width - margin.right);
        line.setAttribute("y1", y);
        line.setAttribute("y2", y);
        line.setAttribute("class", "ca-axis-line");
        line.setAttribute("opacity", "0.35");

        svg.appendChild(line);

        const label = document.createElementNS(SVG_NS, "text");

        label.setAttribute("x", margin.left - 8);
        label.setAttribute("y", y + 3);
        label.setAttribute("text-anchor", "end");
        label.setAttribute("class", "ca-axis-label");
        label.textContent = Math.round(value);

        svg.appendChild(label);
    }

    // -------- month gridlines / labels (season order: Jul -> Jun) --------

    const monthStarts = [
        0, 31, 62, 92, 123, 153,
        184, 215, 243, 274, 304, 335,
    ];

    const monthNames = [
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    ];

    monthStarts.forEach((offset, index) => {

        const x = xForOffset(offset);

        const line = document.createElementNS(SVG_NS, "line");

        line.setAttribute("x1", x);
        line.setAttribute("x2", x);
        line.setAttribute("y1", margin.top);
        line.setAttribute("y2", height - margin.bottom);
        line.setAttribute("class", "ca-axis-line");
        line.setAttribute("opacity", "0.2");

        svg.appendChild(line);

        const label = document.createElementNS(SVG_NS, "text");

        label.setAttribute("x", x + 3);
        label.setAttribute("y", height - margin.bottom + 14);
        label.setAttribute("class", "ca-axis-label");
        label.textContent = monthNames[index];

        svg.appendChild(label);
    });

    // -------- historical min/max band --------
    //
    // A shaded envelope across all HISTORICAL seasons (excludes the
    // current, still-incomplete season), giving quick visual context
    // for the full historical range behind the individual lines.

    const byOffset = new Map();

    historicalSeasonYears.forEach((year) => {

        seasons.get(year).forEach((point) => {

            if (!byOffset.has(point.offset)) {

                byOffset.set(point.offset, []);
            }

            byOffset.get(point.offset).push(point.value);
        });
    });

    const bandOffsets = Array.from(byOffset.keys()).sort(
        (a, b) => a - b
    );

    if (bandOffsets.length > 1) {

        let pathData = "";

        bandOffsets.forEach((offset, index) => {

            const values = byOffset.get(offset);

            const minAtOffset = Math.min(...values);

            const x = xForOffset(offset);

            const y = yForValue(minAtOffset);

            pathData += `${index === 0 ? "M" : "L"} ${x} ${y} `;
        });

        for (let i = bandOffsets.length - 1; i >= 0; i--) {

            const offset = bandOffsets[i];

            const values = byOffset.get(offset);

            const maxAtOffset = Math.max(...values);

            const x = xForOffset(offset);

            const y = yForValue(maxAtOffset);

            pathData += `L ${x} ${y} `;
        }

        pathData += "Z";

        const band = document.createElementNS(SVG_NS, "path");

        band.setAttribute("d", pathData.trim());
        band.setAttribute("class", "ca-history-band");

        svg.appendChild(band);
    }

    // -------- individual historical season lines --------

    function drawSeason(seasonYear, points, isCurrent, colorIndex) {

        if (points.length === 0) {

            return;
        }

        let pathData = "";

        points.forEach((point, index) => {

            const x = xForOffset(point.offset);

            const y = yForValue(point.value);

            pathData += `${index === 0 ? "M" : "L"} ${x} ${y} `;
        });

        const path = document.createElementNS(SVG_NS, "path");

        path.setAttribute("d", pathData.trim());

        if (isCurrent) {

            path.setAttribute("class", "ca-year-line current");

        } else {

            path.setAttribute("class", "ca-year-line");

            path.setAttribute(
                "stroke",
                seasonColor(colorIndex, historicalSeasonYears.length)
            );
        }

        svg.appendChild(path);
    }

    historicalSeasonYears.forEach((year, index) => {

        drawSeason(year, seasons.get(year), false, index);
    });

    // -------- zero line (drawn after the spaghetti so it stays crisp) --------

    const zeroY = yForValue(0);

    const zeroLine = document.createElementNS(SVG_NS, "line");

    zeroLine.setAttribute("x1", margin.left);
    zeroLine.setAttribute("x2", width - margin.right);
    zeroLine.setAttribute("y1", zeroY);
    zeroLine.setAttribute("y2", zeroY);
    zeroLine.setAttribute("class", "ca-zero-line");

    svg.appendChild(zeroLine);

    const zeroLabel = document.createElementNS(SVG_NS, "text");

    zeroLabel.setAttribute("x", width - margin.right);
    zeroLabel.setAttribute("y", zeroY - 4);
    zeroLabel.setAttribute("text-anchor", "end");
    zeroLabel.setAttribute("class", "ca-zero-label");
    zeroLabel.textContent =
        "0 m/s  (westerly above · easterly below)";

    svg.appendChild(zeroLabel);

    // -------- current season, drawn last so it's always on top --------

    if (seasons.has(currentSeasonYear)) {

        drawSeason(
            currentSeasonYear,
            seasons.get(currentSeasonYear),
            true,
            0
        );
    }

    wrapper.appendChild(svg);

    renderLegend(historicalSeasonYears, currentSeasonYear);

    return { seasons, currentSeasonYear };
}


// A "nice" axis step (1/2/5 * 10^n) for a target number of ticks.
function niceStep(range, targetTicks) {

    const roughStep = range / targetTicks;

    const magnitude = Math.pow(
        10,
        Math.floor(Math.log10(roughStep))
    );

    const residual = roughStep / magnitude;

    let step;

    if (residual > 5) {

        step = 10 * magnitude;

    } else if (residual > 2) {

        step = 5 * magnitude;

    } else if (residual > 1) {

        step = 2 * magnitude;

    } else {

        step = magnitude;
    }

    return step || 1;
}


// ============================================================
// COLOR LEGEND (gradient colorbar + current-season swatch)
// ============================================================

function renderLegend(historicalSeasonYears, currentSeasonYear) {

    const container = document.getElementById("caLegend");

    container.innerHTML = "";

    if (historicalSeasonYears.length === 0) {

        return;
    }

    const gradientWidth = 260;

    const gradientHeight = 10;

    const svg = document.createElementNS(SVG_NS, "svg");

    svg.setAttribute(
        "viewBox",
        `0 0 ${gradientWidth} ${gradientHeight}`
    );

    svg.setAttribute("class", "ca-legend-gradient");

    const defs = document.createElementNS(SVG_NS, "defs");

    const gradient = document.createElementNS(
        SVG_NS,
        "linearGradient"
    );

    gradient.setAttribute("id", "caSeasonGradient");

    const stopCount = 8;

    for (let i = 0; i <= stopCount; i++) {

        const fraction = i / stopCount;

        const index = Math.round(
            fraction * (historicalSeasonYears.length - 1)
        );

        const stop = document.createElementNS(SVG_NS, "stop");

        stop.setAttribute("offset", `${fraction * 100}%`);

        stop.setAttribute(
            "stop-color",
            seasonColor(index, historicalSeasonYears.length)
        );

        gradient.appendChild(stop);
    }

    defs.appendChild(gradient);

    svg.appendChild(defs);

    const rect = document.createElementNS(SVG_NS, "rect");

    rect.setAttribute("x", 0);
    rect.setAttribute("y", 0);
    rect.setAttribute("width", gradientWidth);
    rect.setAttribute("height", gradientHeight);
    rect.setAttribute("fill", "url(#caSeasonGradient)");
    rect.setAttribute("rx", 3);

    svg.appendChild(rect);

    const row = document.createElement("div");

    row.className = "ca-legend-row";

    const startLabel = document.createElement("span");

    startLabel.textContent = seasonLabel(
        historicalSeasonYears[0]
    );

    const endLabel = document.createElement("span");

    endLabel.textContent = seasonLabel(
        historicalSeasonYears[historicalSeasonYears.length - 1]
    );

    const gradientWrap = document.createElement("div");

    gradientWrap.className = "ca-legend-gradient-wrap";

    gradientWrap.appendChild(startLabel);

    gradientWrap.appendChild(svg);

    gradientWrap.appendChild(endLabel);

    const currentSwatch = document.createElement("div");

    currentSwatch.className = "ca-legend-current";

    const swatchLine = document.createElement("span");

    swatchLine.className = "ca-legend-current-line";

    const swatchLabel = document.createElement("span");

    swatchLabel.textContent =
        `Current season (${seasonLabel(currentSeasonYear)})`;

    currentSwatch.appendChild(swatchLine);

    currentSwatch.appendChild(swatchLabel);

    row.appendChild(gradientWrap);

    row.appendChild(currentSwatch);

    container.appendChild(row);
}


// ============================================================
// MAIN
// ============================================================

async function main() {

    try {

        setStatus("Loading...", false);

        const [bundle, latest] = await Promise.all([
            fetchJson(BUNDLE_URL),
            fetchJson(LATEST_URL),
        ]);

        const { seasons, currentSeasonYear } =
            renderChart(bundle, latest);

        renderStats(latest, seasons, currentSeasonYear);

        setStatus(
            `Updated ${formatDate(latest.latest_date)} · ` +
                `ERA5/ERA5T`,
            false
        );

    } catch (error) {

        console.error("Polar vortex load failed:", error);

        setStatus(
            "Could not load polar vortex data yet. " +
                "The historical backfill may not have run.",
            true
        );
    }
}


main();
