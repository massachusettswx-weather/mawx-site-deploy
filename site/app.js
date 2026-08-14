let manifest = null;

let currentFiles = [];
let currentIndex = 0;
let playTimer = null;
let manifestLoadToken = 0;


const MODEL_CONFIG = {

    weathernext2_mean: {
        name: "WeatherNext 2",

        latestUrls: [
            "../output/weathernext2_mean/latest.json",
            "../output/latest.json",
        ],

        manifestType: "direct",
    },

    gfs: {
        name: "NCEP GFS",

        currentUrls: [
            "../metadata/gfs/current.json",
        ],

        latestUrls: [
            "../metadata/gfs/latest.json",
        ],

        manifestType: "pointer",
    },

    ifs: {
        name: "ECMWF IFS",

        currentUrls: [
            "../metadata/ifs/current.json",
        ],

        latestUrls: [
            "../metadata/ifs/latest.json",
        ],

        manifestType: "pointer",
    },

    aifs: {
        name: "ECMWF AIFS",

        currentUrls: [
            "../metadata/aifs/current.json",
        ],

        latestUrls: [
            "../metadata/aifs/latest.json",
        ],

        manifestType: "pointer",
    },
};


const PRODUCT_DISPLAY_NAMES = {

    h5_vort:
        "500 mb Height + Relative Vorticity",

    t925_hgt:
        "925 mb Temperature + Height",

    t850_hgt:
        "850 mb Temperature + Height",

    rh700_hgt:
        "700 mb Relative Humidity + Height",

    omega700:
        "700 mb Vertical Velocity",

    wind925_hgt:
        "925 mb Wind + Height",

    wind850_hgt:
        "850 mb Wind + Height",

    wind700_hgt:
        "700 mb Wind + Height",

    wind500_hgt:
        "500 mb Wind + Height",

    jet300:
        "300 mb Jet",

    jet250:
        "250 mb Jet",

    mslp:
        "Mean Sea-Level Pressure",

    t2m:
        "2 m Temperature",

    td2m:
        "2 m Dew Point",

    cloud_total:
        "Total Cloud Cover",

    wind10:
        "10 m Wind",

    wind100:
        "100 m Wind",

    pwat:
        "Precipitable Water",

    precip_rate:
        "Precipitation Rate",

    precip_type:
        "Precipitation Type",

    mucape:
        "Most-Unstable CAPE",

    geopotential_500:
        "500 mb Geopotential Height",

    vorticity_500:
        "500 mb Relative Vorticity",

    thickness_1000_500:
        "1000–500 mb Thickness",

    temperature_850:
        "850 mb Temperature",

    rh_omega_700:
        "700 mb RH + Vertical Velocity",

    temperature_2m:
        "2 m Temperature",

    wind_10m:
        "10 m Wind",

    wind_100m:
        "100 m Wind",

    wind_850:
        "850 mb Wind",

    wind_500:
        "500 mb Wind",

    jet_250:
        "250 mb Jet",

    precipitable_water:
        "Precipitable Water",

    precip_6h:
        "6-h Precipitation",

    total_precipitation:
        "Total Precipitation",
};


const REGION_DISPLAY_NAMES = {
    global: "Global",

    north_america: "North America",
    conus: "CONUS",
    northeast: "Northeast",
    new_england: "New England",
    mid_atlantic: "Mid-Atlantic",
    southeast: "Southeast",
    florida: "Florida",
    gulf_coast: "Gulf Coast",
    southern_plains: "Southern Plains",
    central_plains: "Central Plains",
    northern_plains: "Northern Plains",
    midwest: "Midwest",
    great_lakes: "Great Lakes",
    ohio_valley: "Ohio Valley",
    rockies: "Rockies",
    southwest: "Southwest",
    northwest: "Northwest",
    california: "California",
    alaska: "Alaska",
    hawaii: "Hawaii",
    canada: "Canada",
    eastern_canada: "Eastern Canada",
    western_canada: "Western Canada",
    mexico: "Mexico",

    atlantic: "Atlantic Ocean",
    western_atlantic: "Western Atlantic",
    central_atlantic: "Central Atlantic",
    eastern_atlantic: "Eastern Atlantic",
    tropical_atlantic: "Tropical Atlantic",
    caribbean: "Caribbean",
    gulf_of_mexico: "Gulf of Mexico",

    europe: "Europe",
    western_europe: "Western Europe",
    central_europe: "Central Europe",
    eastern_europe: "Eastern Europe",
    northern_europe: "Northern Europe",
    southern_europe: "Southern Europe",
    uk_ireland: "UK & Ireland",
    iberia: "Iberian Peninsula",
    france_benelux: "France & Benelux",
    germany_alps: "Germany & Alps",
    italy_adriatic: "Italy & Adriatic",
    balkans: "Balkans",
    greece_turkey: "Greece & Turkey",
    scandinavia: "Scandinavia",
    mediterranean: "Mediterranean",

    asia: "Asia",
    east_asia: "East Asia",
    china: "China",
    korea_japan: "Korea & Japan",
    southeast_asia: "Southeast Asia",
    south_asia: "South Asia",
    india_subcontinent: "Indian Subcontinent",
    central_asia: "Central Asia",
    middle_east: "Middle East",
    maritime_continent: "Maritime Continent",

    africa: "Africa",
    north_africa: "North Africa",
    west_africa: "West Africa",
    east_africa: "East Africa",
    southern_africa: "Southern Africa",

    south_america: "South America",
    northern_south_america: "Northern South America",
    southern_south_america: "Southern South America",
    brazil: "Brazil",
    andes: "Andes",

    north_pacific: "North Pacific",
    eastern_pacific: "Eastern Pacific",
    western_pacific: "Western Pacific",
    northwest_pacific: "Northwest Pacific",
    tropical_pacific: "Tropical Pacific",

    indian_ocean: "Indian Ocean",
    western_indian_ocean: "Western Indian Ocean",
    central_indian_ocean: "Central Indian Ocean",
    eastern_indian_ocean: "Eastern Indian Ocean",
    tropical_indian_ocean: "Tropical Indian Ocean",

    australia: "Australia",
    new_zealand: "New Zealand",

    arctic: "Arctic",
    antarctica: "Antarctica",
    southern_ocean: "Southern Ocean",
};


const REGION_GROUPS = [
    {
        name: "Global",
        regions: [
            "global",
        ],
    },

    {
        name: "United States",
        regions: [
            "conus",
            "northeast",
            "new_england",
            "mid_atlantic",
            "southeast",
            "florida",
            "gulf_coast",
            "southern_plains",
            "central_plains",
            "northern_plains",
            "midwest",
            "great_lakes",
            "ohio_valley",
            "rockies",
            "southwest",
            "northwest",
            "california",
            "alaska",
            "hawaii",
        ],
    },

    {
        name: "North America",
        regions: [
            "north_america",
            "canada",
            "eastern_canada",
            "western_canada",
            "mexico",
        ],
    },

    {
        name: "Atlantic / Caribbean",
        regions: [
            "atlantic",
            "western_atlantic",
            "central_atlantic",
            "eastern_atlantic",
            "tropical_atlantic",
            "caribbean",
            "gulf_of_mexico",
        ],
    },

    {
        name: "Europe",
        regions: [
            "europe",
            "western_europe",
            "central_europe",
            "eastern_europe",
            "northern_europe",
            "southern_europe",
            "uk_ireland",
            "iberia",
            "france_benelux",
            "germany_alps",
            "italy_adriatic",
            "balkans",
            "greece_turkey",
            "scandinavia",
            "mediterranean",
        ],
    },

    {
        name: "Asia / Middle East",
        regions: [
            "asia",
            "east_asia",
            "china",
            "korea_japan",
            "southeast_asia",
            "south_asia",
            "india_subcontinent",
            "central_asia",
            "middle_east",
            "maritime_continent",
        ],
    },

    {
        name: "Africa",
        regions: [
            "africa",
            "north_africa",
            "west_africa",
            "east_africa",
            "southern_africa",
        ],
    },

    {
        name: "South America",
        regions: [
            "south_america",
            "northern_south_america",
            "southern_south_america",
            "brazil",
            "andes",
        ],
    },

    {
        name: "Pacific",
        regions: [
            "north_pacific",
            "eastern_pacific",
            "western_pacific",
            "northwest_pacific",
            "tropical_pacific",
        ],
    },

    {
        name: "Indian Ocean",
        regions: [
            "indian_ocean",
            "western_indian_ocean",
            "central_indian_ocean",
            "eastern_indian_ocean",
            "tropical_indian_ocean",
        ],
    },

    {
        name: "Oceania",
        regions: [
            "australia",
            "new_zealand",
        ],
    },

    {
        name: "Polar",
        regions: [
            "arctic",
            "antarctica",
            "southern_ocean",
        ],
    },
];


const modelText =
    document.getElementById(
        "modelText"
    );

const cycleText =
    document.getElementById(
        "cycleText"
    );

const availabilityBadge =
    document.getElementById(
        "availabilityBadge"
    );

const modelSelect =
    document.getElementById(
        "modelSelect"
    );

const regionSelect =
    document.getElementById(
        "regionSelect"
    );

const productSelect =
    document.getElementById(
        "productSelect"
    );

const speedSelect =
    document.getElementById(
        "speedSelect"
    );

const mapImage =
    document.getElementById(
        "mapImage"
    );

const loadingText =
    document.getElementById(
        "loadingText"
    );

const prevButton =
    document.getElementById(
        "prevButton"
    );

const nextButton =
    document.getElementById(
        "nextButton"
    );

const playButton =
    document.getElementById(
        "playButton"
    );

const productText =
    document.getElementById(
        "productText"
    );

const hourText =
    document.getElementById(
        "hourText"
    );

const frameCounter =
    document.getElementById(
        "frameCounter"
    );

const selectedHourText =
    document.getElementById(
        "selectedHourText"
    );

const hourGrid =
    document.getElementById(
        "hourGrid"
    );


function prettifyIdentifier(
    value
) {

    return String(
        value || ""
    )
        .replace(
            /_/g,
            " "
        )
        .replace(
            /\b\w/g,
            letter =>
                letter.toUpperCase()
        );
}


function formatRegionName(
    region
) {

    return (
        REGION_DISPLAY_NAMES[
            region
        ]
        ||
        prettifyIdentifier(
            region
        )
    );
}


function productDisplayName(
    product
) {

    return (
        PRODUCT_DISPLAY_NAMES[
            product
        ]
        ||
        prettifyIdentifier(
            product
        )
    );
}


function setAvailability(
    state,
    text
) {

    availabilityBadge.className =
        (
            "availability-badge "
            +
            state
        );

    availabilityBadge.textContent =
        text;
}


function stopAnimation() {

    if (!playTimer) {
        return;
    }

    clearInterval(
        playTimer
    );

    playTimer = null;

    playButton.textContent =
        "▶ Play";
}


function clearViewer(
    message
) {

    stopAnimation();

    manifest = null;

    currentFiles = [];
    currentIndex = 0;

    regionSelect.innerHTML =
        "";

    productSelect.innerHTML =
        "";

    hourGrid.innerHTML =
        "";

    selectedHourText.textContent =
        "—";

    productText.textContent =
        "No data";

    hourText.textContent =
        "—";

    frameCounter.textContent =
        "0 / 0";

    mapImage.removeAttribute(
        "src"
    );

    loadingText.style.display =
        "flex";

    loadingText.textContent =
        message;

    regionSelect.disabled =
        true;

    productSelect.disabled =
        true;

    prevButton.disabled =
        true;

    nextButton.disabled =
        true;

    playButton.disabled =
        true;
}


async function fetchJson(
    url
) {

    const response =
        await fetch(
            url,
            {
                cache:
                    "no-store",
            }
        );

    if (!response.ok) {

        throw new Error(
            (
                url
                +
                " returned "
                +
                response.status
            )
        );
    }

    return response.json();
}


async function fetchFirstAvailableJson(
    urls
) {

    let lastError =
        null;

    for (const url of urls) {

        try {

            return await fetchJson(
                url
            );

        }

        catch (error) {

            lastError =
                error;
        }
    }

    throw (
        lastError
        ||
        new Error(
            "No manifest is available."
        )
    );
}


function resolveObjectUrl(
    objectName
) {

    if (!objectName) {
        return null;
    }

    const value =
        String(
            objectName
        );

    const storagePrefix =
        (
            "https://storage.googleapis.com/"
            +
            "massachusettswx-nwp-project/"
        );

    if (
        value.startsWith(
            storagePrefix
        )
    ) {

        const objectPath =
            value.slice(
                storagePrefix.length
            );

        if (
            objectPath.startsWith(
                "products/"
            )
        ) {

            return (
                "/objects/"
                +
                objectPath.replace(
                    /^\/+/,
                    ""
                )
            );
        }

        return (
            "../"
            +
            objectPath.replace(
                /^\/+/,
                ""
            )
        );
    }

    if (
        value.startsWith(
            "products/"
        )
    ) {

        return (
            "/objects/"
            +
            value.replace(
                /^\/+/,
                ""
            )
        );
    }

    if (
        value.startsWith(
            "metadata/"
        )
    ) {

        return (
            "../"
            +
            value.replace(
                /^\/+/,
                ""
            )
        );
    }

    if (
        value.startsWith(
            "http://"
        )
        ||
        value.startsWith(
            "https://"
        )
    ) {

        return value;
    }

    return (
        "../"
        +
        value.replace(
            /^\/+/,
            ""
        )
    );
}


async function loadRawManifest(
    modelId
) {

    const config =
        MODEL_CONFIG[
            modelId
        ];

    /*
     * WeatherNext 2 still uses its existing direct latest manifest.
     */
    if (
        config.manifestType
        ===
        "direct"
    ) {

        return (
            fetchFirstAvailableJson(
                config.latestUrls
            )
        );
    }

    /*
     * Operational GFS / IFS / AIFS:
     *
     *   1. Prefer current.json so a cycle becomes usable while it
     *      is still running.
     *   2. Fall back to latest.json when no current cycle has begun
     *      or current metadata is temporarily unavailable.
     */
    let pointer =
        null;

    if (
        Array.isArray(
            config.currentUrls
        )
    ) {

        try {

            pointer =
                await fetchFirstAvailableJson(
                    config.currentUrls
                );

        }

        catch (error) {

            console.debug(
                (
                    config.name
                    +
                    " current cycle is not available yet."
                ),
                error
            );
        }
    }

    if (
        !pointer
    ) {

        pointer =
            await fetchFirstAvailableJson(
                config.latestUrls
            );
    }

    const manifestUrl =
        (
            pointer.manifest_object
            ?
            resolveObjectUrl(
                pointer.manifest_object
            )
            :
            pointer.manifest_url
        );

    if (!manifestUrl) {

        throw new Error(
            (
                config.name
                +
                " metadata has no manifest pointer."
            )
        );
    }

    return fetchJson(
        manifestUrl
    );
}

function normalizeFile(
    file,
    modelId
) {

    let imageUrl =
        null;

    if (file.object_name) {

        imageUrl =
            resolveObjectUrl(
                file.object_name
            );
    }

    else if (file.https_url) {

        imageUrl =
            resolveObjectUrl(
                file.https_url
            );
    }

    else if (file.path) {

        imageUrl =
            (
                "../"
                +
                String(
                    file.path
                ).replace(
                    /^\/+/
,
                    ""
                )
            );
    }

    return {

        status:
            (
                file.status
                ||
                "ready"
            ),

        model:
            (
                file.model
                ||
                modelId
            ),

        product:
            file.product,

        product_name:
            (
                file.product_name
                ||
                productDisplayName(
                    file.product
                )
            ),

        region:
            file.region,

        forecast_hour:
            Number(
                file.forecast_hour
            ),

        image_url:
            imageUrl,
    };
}


function normalizeManifest(
    rawManifest,
    modelId
) {

    const sourceFiles =
        (
            Array.isArray(
                rawManifest.files
            )
            ?
            rawManifest.files
            :
            []
        );

    return {

        ...rawManifest,

        model:
            (
                rawManifest.model
                ||
                modelId
            ),

        model_name:
            (
                rawManifest.model_name
                ||
                MODEL_CONFIG[
                    modelId
                ].name
            ),

        files:
            sourceFiles
                .map(
                    file =>
                        normalizeFile(
                            file,
                            modelId
                        )
                )
                .filter(
                    file =>
                        file.product
                        &&
                        file.region
                        &&
                        file.image_url
                        &&
                        Number.isFinite(
                            file.forecast_hour
                        )
                ),
    };
}


function goodFiles() {

    if (
        !manifest
        ||
        !Array.isArray(
            manifest.files
        )
    ) {

        return [];
    }

    return manifest.files.filter(
        file =>
            file.status
            !==
            "failed"
            &&
            file.product
            &&
            file.region
            &&
            file.image_url
            &&
            Number.isFinite(
                file.forecast_hour
            )
    );
}


function populateRegions() {

    const availableRegions =
        new Set(
            goodFiles()
                .map(
                    file =>
                        file.region
                )
        );

    const previous =
        regionSelect.value;

    regionSelect.innerHTML =
        "";

    const included =
        new Set();

    REGION_GROUPS.forEach(
        groupConfig => {

            const available =
                groupConfig.regions.filter(
                    region =>
                        availableRegions.has(
                            region
                        )
                );

            if (
                available.length
                ===
                0
            ) {

                return;
            }

            const group =
                document.createElement(
                    "optgroup"
                );

            group.label =
                groupConfig.name;

            available.forEach(
                region => {

                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        region;

                    option.textContent =
                        formatRegionName(
                            region
                        );

                    group.appendChild(
                        option
                    );

                    included.add(
                        region
                    );
                }
            );

            regionSelect.appendChild(
                group
            );
        }
    );

    const uncategorized =
        [
            ...availableRegions,
        ]
        .filter(
            region =>
                !included.has(
                    region
                )
        )
        .sort(
            (
                a,
                b
            ) =>
                formatRegionName(
                    a
                )
                .localeCompare(
                    formatRegionName(
                        b
                    )
                )
        );

    if (
        uncategorized.length
        >
        0
    ) {

        const group =
            document.createElement(
                "optgroup"
            );

        group.label =
            "Other";

        uncategorized.forEach(
            region => {

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    region;

                option.textContent =
                    formatRegionName(
                        region
                    );

                group.appendChild(
                    option
                );
            }
        );

        regionSelect.appendChild(
            group
        );
    }

    if (
        availableRegions.has(
            previous
        )
    ) {

        regionSelect.value =
            previous;
    }

    else if (
        availableRegions.has(
            "conus"
        )
    ) {

        regionSelect.value =
            "conus";
    }

    else if (
        availableRegions.size
        >
        0
    ) {

        regionSelect.value =
            [
                ...availableRegions,
            ][
                0
            ];
    }
}

function populateProducts() {

    const products =
        [
            ...new Set(
                goodFiles()
                    .map(
                        file =>
                            file.product
                    )
            ),
        ]
        .sort(
            (
                a,
                b
            ) =>
                productDisplayName(
                    a
                )
                .localeCompare(
                    productDisplayName(
                        b
                    )
                )
        );

    productSelect.innerHTML =
        "";

    products.forEach(
        product => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                product;

            option.textContent =
                productDisplayName(
                    product
                );

            productSelect.appendChild(
                option
            );
        }
    );
}


function populateHourGrid() {

    hourGrid.innerHTML =
        "";

    currentFiles.forEach(
        (
            file,
            index
        ) => {

            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            button.className =
                "hour-button";

            if (
                index
                ===
                currentIndex
            ) {

                button.classList.add(
                    "selected"
                );
            }

            button.textContent =
                String(
                    file.forecast_hour
                ).padStart(
                    3,
                    "0"
                );

            button.title =
                (
                    "Forecast hour "
                    +
                    file.forecast_hour
                );

            button.addEventListener(
                "click",
                () => {

                    stopAnimation();

                    currentIndex =
                        index;

                    showCurrentImage();
                }
            );

            hourGrid.appendChild(
                button
            );
        }
    );
}


function updateAvailableFiles() {

    stopAnimation();

    const region =
        regionSelect.value;

    const product =
        productSelect.value;

    currentFiles =
        goodFiles()
            .filter(
                file =>
                    file.region
                    ===
                    region
                    &&
                    file.product
                    ===
                    product
            )
            .sort(
                (
                    a,
                    b
                ) =>
                    a.forecast_hour
                    -
                    b.forecast_hour
            );

    currentIndex = 0;

    populateHourGrid();

    showCurrentImage();
}


function updateControls() {

    const hasFrames =
        currentFiles.length
        >
        0;

    prevButton.disabled =
        !hasFrames;

    nextButton.disabled =
        !hasFrames;

    playButton.disabled =
        currentFiles.length
        <
        2;

    if (!hasFrames) {

        productText.textContent =
            "No data";

        hourText.textContent =
            "—";

        selectedHourText.textContent =
            "—";

        frameCounter.textContent =
            "0 / 0";

        return;
    }

    const file =
        currentFiles[
            currentIndex
        ];

    productText.textContent =
        file.product_name;

    const hourLabel =
        (
            "F"
            +
            String(
                file.forecast_hour
            ).padStart(
                3,
                "0"
            )
        );

    hourText.textContent =
        hourLabel;

    selectedHourText.textContent =
        hourLabel;

    frameCounter.textContent =
        (
            (currentIndex + 1)
            +
            " / "
            +
            currentFiles.length
        );
}


function showCurrentImage() {

    updateControls();

    populateHourGrid();

    if (
        currentFiles.length
        ===
        0
    ) {

        loadingText.style.display =
            "flex";

        loadingText.textContent =
            "No maps available for this selection.";

        mapImage.removeAttribute(
            "src"
        );

        return;
    }

    const file =
        currentFiles[
            currentIndex
        ];

    loadingText.style.display =
        "flex";

    loadingText.textContent =
        "Loading map...";

    mapImage.onload =
        () => {

            loadingText.style.display =
                "none";
        };

    mapImage.onerror =
        () => {

            loadingText.style.display =
                "flex";

            loadingText.textContent =
                "Map image could not be loaded.";
        };

    const separator =
        (
            file.image_url.includes(
                "?"
            )
            ?
            "&"
            :
            "?"
        );

    const version =
        encodeURIComponent(
            (
                manifest
                &&
                manifest.updated_at_utc
            )
            ||
            Date.now()
        );

    mapImage.src =
        (
            file.image_url
            +
            separator
            +
            "v="
            +
            version
        );
}


function previousHour() {

    if (
        currentFiles.length
        ===
        0
    ) {

        return;
    }

    currentIndex =
        (
            currentIndex
            -
            1
            +
            currentFiles.length
        )
        %
        currentFiles.length;

    showCurrentImage();
}


function nextHour() {

    if (
        currentFiles.length
        ===
        0
    ) {

        return;
    }

    currentIndex =
        (
            currentIndex
            +
            1
        )
        %
        currentFiles.length;

    showCurrentImage();
}


function startAnimation() {

    if (
        currentFiles.length
        <
        2
    ) {

        return;
    }

    const delay =
        Number(
            speedSelect.value
        );

    playButton.textContent =
        "❚❚ Pause";

    playTimer =
        setInterval(
            nextHour,
            delay
        );
}


function togglePlay() {

    if (playTimer) {

        stopAnimation();

        return;
    }

    startAnimation();
}


async function loadSelectedModel() {

    stopAnimation();

    const token =
        ++manifestLoadToken;

    const modelId =
        modelSelect.value;

    const config =
        MODEL_CONFIG[
            modelId
        ];

    modelText.textContent =
        config.name;

    cycleText.textContent =
        "Loading latest cycle...";

    setAvailability(
        "loading",
        "Loading"
    );

    clearViewer(
        (
            "Loading latest "
            +
            config.name
            +
            " cycle..."
        )
    );

    modelSelect.disabled =
        false;

    try {

        const rawManifest =
            await loadRawManifest(
                modelId
            );

        if (
            token
            !==
            manifestLoadToken
        ) {

            return;
        }

        manifest =
            normalizeManifest(
                rawManifest,
                modelId
            );

        if (
            goodFiles().length
            ===
            0
        ) {

            throw new Error(
                "No usable maps in manifest."
            );
        }

        modelText.textContent =
            manifest.model_name;

        cycleText.textContent =
            (
                "Cycle "
                +
                manifest.cycle
            );

        setAvailability(
            "ready",
            "Ready"
        );

        regionSelect.disabled =
            false;

        productSelect.disabled =
            false;

        populateRegions();

        populateProducts();

        updateAvailableFiles();

    }

    catch (error) {

        console.error(
            error
        );

        if (
            token
            !==
            manifestLoadToken
        ) {

            return;
        }

        cycleText.textContent =
            "Latest cycle unavailable";

        setAvailability(
            "unavailable",
            "Unavailable"
        );

        clearViewer(
            (
                config.name
                +
                " does not have a published cycle available yet."
            )
        );

        modelSelect.disabled =
            false;

        setAvailability(
            "unavailable",
            "Unavailable"
        );
    }
}


modelSelect.addEventListener(
    "change",
    loadSelectedModel
);

regionSelect.addEventListener(
    "change",
    updateAvailableFiles
);

productSelect.addEventListener(
    "change",
    updateAvailableFiles
);

speedSelect.addEventListener(
    "change",
    () => {

        if (playTimer) {

            stopAnimation();

            startAnimation();
        }
    }
);

prevButton.addEventListener(
    "click",
    () => {

        stopAnimation();

        previousHour();
    }
);

nextButton.addEventListener(
    "click",
    () => {

        stopAnimation();

        nextHour();
    }
);

playButton.addEventListener(
    "click",
    togglePlay
);


document.addEventListener(
    "keydown",
    event => {

        const activeTag =
            document.activeElement
                ?.tagName
                ?.toLowerCase();

        if (
            activeTag
            ===
            "select"
            ||
            activeTag
            ===
            "input"
            ||
            activeTag
            ===
            "textarea"
        ) {

            return;
        }

        if (
            event.key
            ===
            "ArrowLeft"
        ) {

            event.preventDefault();

            stopAnimation();

            previousHour();
        }

        else if (
            event.key
            ===
            "ArrowRight"
        ) {

            event.preventDefault();

            stopAnimation();

            nextHour();
        }

        else if (
            event.code
            ===
            "Space"
        ) {

            event.preventDefault();

            togglePlay();
        }
    }
);



// ============================================================
// LIVE MANIFEST REFRESH
// ============================================================

const LIVE_REFRESH_MS = 5000;
let liveRefreshBusy = false;


async function refreshSelectedModelInBackground() {

    if (
        liveRefreshBusy
        ||
        playTimer
    ) {
        return;
    }

    liveRefreshBusy = true;

    try {

        const modelId =
            modelSelect.value;

        const previousRegion =
            regionSelect.value;

        const previousProduct =
            productSelect.value;

        const previousFiles =
            currentFiles.slice();

        const previousIndex =
            currentIndex;

        const previousHour =
            (
                previousFiles.length > 0
                ?
                previousFiles[
                    previousIndex
                ]?.forecast_hour
                :
                null
            );

        const wasOnNewest =
            (
                previousFiles.length > 0
                &&
                previousIndex
                ===
                previousFiles.length - 1
            );

        const rawManifest =
            await loadRawManifest(
                modelId
            );

        const refreshed =
            normalizeManifest(
                rawManifest,
                modelId
            );

        if (
            !refreshed
            ||
            !Array.isArray(
                refreshed.files
            )
            ||
            refreshed.files.length === 0
        ) {
            return;
        }

        manifest = refreshed;

        modelText.textContent =
            manifest.model_name;

        cycleText.textContent =
            (
                "Cycle "
                +
                manifest.cycle
            );

        setAvailability(
            (
                manifest.status
                ===
                "running"
                ?
                "loading"
                :
                "ready"
            ),
            (
                manifest.status
                ===
                "running"
                ?
                "Updating"
                :
                "Ready"
            )
        );

        populateRegions();

        if (
            [
                ...regionSelect.options,
            ].some(
                option =>
                    option.value
                    ===
                    previousRegion
            )
        ) {
            regionSelect.value =
                previousRegion;
        }

        populateProducts();

        if (
            [
                ...productSelect.options,
            ].some(
                option =>
                    option.value
                    ===
                    previousProduct
            )
        ) {
            productSelect.value =
                previousProduct;
        }

        const region =
            regionSelect.value;

        const product =
            productSelect.value;

        currentFiles =
            goodFiles()
                .filter(
                    file =>
                        file.region
                        ===
                        region
                        &&
                        file.product
                        ===
                        product
                )
                .sort(
                    (
                        a,
                        b
                    ) =>
                        a.forecast_hour
                        -
                        b.forecast_hour
                );

        if (
            currentFiles.length === 0
        ) {
            currentIndex = 0;
            populateHourGrid();
            showCurrentImage();
            return;
        }

        if (wasOnNewest) {
            currentIndex =
                currentFiles.length - 1;
        }

        else if (
            previousHour !== null
        ) {

            const matchedIndex =
                currentFiles.findIndex(
                    file =>
                        file.forecast_hour
                        ===
                        previousHour
                );

            currentIndex =
                (
                    matchedIndex >= 0
                    ?
                    matchedIndex
                    :
                    Math.min(
                        previousIndex,
                        currentFiles.length - 1
                    )
                );
        }

        else {
            currentIndex = 0;
        }

        populateHourGrid();
        showCurrentImage();
    }

    catch (error) {
        console.debug(
            "Live manifest refresh failed:",
            error
        );
    }

    finally {
        liveRefreshBusy = false;
    }
}


setInterval(
    refreshSelectedModelInBackground,
    LIVE_REFRESH_MS
);

loadSelectedModel();
