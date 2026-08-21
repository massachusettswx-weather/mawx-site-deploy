const MODEL_CONFIG = {
    weathernext2_mean: {
        name: "WeatherNext 2",

        latestUrls: [
            "../metadata/weathernext2_mean/latest.json",
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


const MODEL_ORDER = [
    "weathernext2_mean",
    "gfs",
    "ifs",
    "aifs",
];


const state = {
    modelId: "gfs",

    manifest: null,

    files: [],

    region: null,

    product: null,

    forecastHour: null,

    frameIndex: 0,

    playing: false,

    animationTimer: null,
};


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


const prevButton =
    document.getElementById(
        "prevButton"
    );


const playButton =
    document.getElementById(
        "playButton"
    );


const nextButton =
    document.getElementById(
        "nextButton"
    );


const mapImage =
    document.getElementById(
        "mapImage"
    );


const loadingText =
    document.getElementById(
        "loadingText"
    );


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


const forecastScrubber =
    document.getElementById(
        "forecastScrubber"
    );


const scrubberHourText =
    document.getElementById(
        "scrubberHourText"
    );


const scrubberStartText =
    document.getElementById(
        "scrubberStartText"
    );


const scrubberEndText =
    document.getElementById(
        "scrubberEndText"
    );


function addCacheBuster(
    url
) {

    const separator =
        url.includes("?")
            ? "&"
            : "?";

    return (
        url
        +
        separator
        +
        "v="
        +
        Date.now()
    );
}


async function fetchJson(
    url
) {

    const response =
        await fetch(
            addCacheBuster(
                url
            ),
            {
                cache: "no-store",
            }
        );

    if (
        !response.ok
    ) {

        throw new Error(
            (
                "HTTP "
                +
                response.status
                +
                " for "
                +
                url
            )
        );
    }

    return (
        await response.json()
    );
}


async function fetchFirstAvailableJson(
    urls
) {

    let lastError =
        null;

    for (
        const url
        of urls
    ) {

        try {

            return (
                await fetchJson(
                    url
                )
            );

        }

        catch (
            error
        ) {

            lastError =
                error;
        }
    }

    throw (
        lastError
        ||
        new Error(
            "No JSON URL was available."
        )
    );
}


function resolveObjectUrl(
    objectName
) {

    if (
        !objectName
    ) {

        return null;
    }

    if (
        objectName.startsWith(
            "http://"
        )
        ||
        objectName.startsWith(
            "https://"
        )
    ) {

        return objectName;
    }

    return (
        "../"
        +
        objectName.replace(
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
     * 1. Prefer current.json so a cycle becomes usable while it
     *    is still running.
     *
     * 2. Fall back to latest.json when no current cycle has begun
     *    or current metadata is temporarily unavailable.
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

        catch (
            error
        ) {

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

    if (
        !manifestUrl
    ) {

        throw new Error(
            (
                config.name
                +
                " metadata has no manifest pointer."
            )
        );
    }

    return (
        fetchJson(
            manifestUrl
        )
    );
}


function normalizeFile(
    file
) {

    const forecastHour =
        Number(
            file.forecast_hour
            ??
            file.forecastHour
            ??
            file.hour
            ??
            0
        );

    return {
        ...file,

        model:
            file.model
            ??
            state.modelId,

        region:
            file.region
            ??
            "global",

        product:
            file.product
            ??
            "unknown",

        forecast_hour:
            forecastHour,

        url:
            (
                file.url
                ??
                file.public_url
                ??
                file.https_url
                ??
                (
                    file.object_name
                        ?
                        resolveObjectUrl(
                            file.object_name
                        )
                        :
                        null
                )
            ),
    };
}


function normalizeManifest(
    rawManifest
) {

    const rawFiles =
        (
            rawManifest.files
            ??
            rawManifest.products
            ??
            []
        );

    const files =
        Array.isArray(
            rawFiles
        )
            ?
            rawFiles
                .map(
                    normalizeFile
                )
                .filter(
                    file =>
                        (
                            file.url
                            &&
                            file.region
                            &&
                            file.product
                        )
                )
            :
            [];

    return {
        ...rawManifest,

        files:
            files,
    };
}


function getDisplayModelName() {

    return (
        MODEL_CONFIG[
            state.modelId
        ]?.name
        ??
        state.modelId.toUpperCase()
    );
}


function formatRegionName(
    region
) {

    if (
        REGION_DISPLAY_NAMES[
            region
        ]
    ) {

        return (
            REGION_DISPLAY_NAMES[
                region
            ]
        );
    }

    return (
        String(
            region
        )
            .replaceAll(
                "_",
                " "
            )
            .replace(
                /\b\w/g,
                character =>
                    character.toUpperCase()
            )
    );
}


function formatProductName(
    product
) {

    return (
        String(
            product
        )
            .replaceAll(
                "_",
                " "
            )
            .replace(
                /\b\w/g,
                character =>
                    character.toUpperCase()
            )
    );
}


function formatForecastHour(
    forecastHour
) {

    return (
        "f"
        +
        String(
            Number(
                forecastHour
            )
        ).padStart(
            3,
            "0"
        )
    );
}


function availableRegions() {

    return (
        new Set(
            state.files.map(
                file =>
                    file.region
            )
        )
    );
}


function filesForRegion(
    region
) {

    return (
        state.files.filter(
            file =>
                file.region
                ===
                region
        )
    );
}


function filesForSelection() {

    return (
        state.files
            .filter(
                file =>
                    (
                        file.region
                        ===
                        state.region
                    )
                    &&
                    (
                        file.product
                        ===
                        state.product
                    )
            )
            .sort(
                (
                    a,
                    b
                ) =>
                    (
                        Number(
                            a.forecast_hour
                        )
                        -
                        Number(
                            b.forecast_hour
                        )
                    )
            )
    );
}


function populateModelSelect() {

    const previous =
        state.modelId;

    modelSelect.innerHTML =
        "";

    for (
        const modelId
        of MODEL_ORDER
    ) {

        const config =
            MODEL_CONFIG[
                modelId
            ];

        if (
            !config
        ) {

            continue;
        }

        const option =
            document.createElement(
                "option"
            );

        option.value =
            modelId;

        option.textContent =
            config.name;

        modelSelect.appendChild(
            option
        );
    }

    modelSelect.value =
        previous;
}


function populateRegions() {

    const available =
        availableRegions();

    const previous =
        state.region;

    regionSelect.innerHTML =
        "";

    const included =
        new Set();

    REGION_GROUPS.forEach(
        groupConfig => {

            const groupRegions =
                groupConfig.regions.filter(
                    region =>
                        available.has(
                            region
                        )
                );

            if (
                groupRegions.length
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

            groupRegions.forEach(
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
            ...available,
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
                    (
                        formatRegionName(
                            a
                        )
                            .localeCompare(
                                formatRegionName(
                                    b
                                )
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
        previous
        &&
        available.has(
            previous
        )
    ) {

        state.region =
            previous;
    }

    else if (
        available.has(
            "conus"
        )
    ) {

        state.region =
            "conus";
    }

    else {

        state.region =
            (
                [
                    ...available,
                ][0]
                ??
                null
            );
    }

    if (
        state.region
    ) {

        regionSelect.value =
            state.region;
    }
}


function populateProducts() {

    const previous =
        state.product;

    const products =
        [
            ...new Set(
                filesForRegion(
                    state.region
                ).map(
                    file =>
                        file.product
                )
            ),
        ].sort();

    productSelect.innerHTML =
        "";

    for (
        const product
        of products
    ) {

        const option =
            document.createElement(
                "option"
            );

        option.value =
            product;

        option.textContent =
            formatProductName(
                product
            );

        productSelect.appendChild(
            option
        );
    }

    if (
        previous
        &&
        products.includes(
            previous
        )
    ) {

        state.product =
            previous;
    }

    else {

        state.product =
            (
                products[0]
                ??
                null
            );
    }

    if (
        state.product
    ) {

        productSelect.value =
            state.product;
    }
}


function updateSelectionFiles() {

    state.selectionFiles =
        filesForSelection();

    if (
        state.selectionFiles.length
        ===
        0
    ) {

        state.frameIndex =
            0;

        state.forecastHour =
            null;

        return;
    }

    const matchingIndex =
        state.selectionFiles.findIndex(
            file =>
                Number(
                    file.forecast_hour
                )
                ===
                Number(
                    state.forecastHour
                )
        );

    if (
        matchingIndex
        >=
        0
    ) {

        state.frameIndex =
            matchingIndex;
    }

    else {

        state.frameIndex =
            0;

        state.forecastHour =
            Number(
                state.selectionFiles[
                    0
                ].forecast_hour
            );
    }
}


function updateHeader() {

    modelText.textContent =
        getDisplayModelName();

    const cycle =
        (
            state.manifest?.cycle
            ??
            state.manifest?.cycle_id
            ??
            "Latest"
        );

    cycleText.textContent =
        (
            "Cycle: "
            +
            cycle
        );

    const status =
        (
            state.manifest?.status
            ??
            (
                state.files.length
                    >
                    0
                    ?
                    "available"
                    :
                    "unavailable"
            )
        );

    availabilityBadge.textContent =
        (
            status === "running"
                ?
                "Updating"
                :
                status === "complete"
                    ?
                    "Complete"
                    :
                    status === "available"
                        ?
                        "Available"
                        :
                        "Unavailable"
        );

    availabilityBadge.className =
        (
            "availability-badge "
            +
            status
        );
}


function updateFrameInformation() {

    if (
        !state.selectionFiles
        ||
        state.selectionFiles.length
        ===
        0
    ) {

        productText.textContent =
            "—";

        hourText.textContent =
            "—";

        selectedHourText.textContent =
            "—";

        frameCounter.textContent =
            "0 / 0";

        return;
    }

    const current =
        state.selectionFiles[
            state.frameIndex
        ];

    productText.textContent =
        formatProductName(
            current.product
        );

    hourText.textContent =
        formatForecastHour(
            current.forecast_hour
        );

    selectedHourText.textContent =
        formatForecastHour(
            current.forecast_hour
        );

    frameCounter.textContent =
        (
            (state.frameIndex + 1)
            +
            " / "
            +
            state.selectionFiles.length
        );
}


function updateNavigationButtons() {

    const count =
        (
            state.selectionFiles?.length
            ??
            0
        );

    prevButton.disabled =
        (
            count
            ===
            0
        );

    nextButton.disabled =
        (
            count
            ===
            0
        );

    playButton.disabled =
        (
            count
            <=
            1
        );
}


function syncForecastScrubber() {

    const files =
        (
            state.selectionFiles
            ??
            []
        );

    if (
        files.length
        ===
        0
    ) {

        forecastScrubber.min =
            "0";

        forecastScrubber.max =
            "0";

        forecastScrubber.value =
            "0";

        forecastScrubber.disabled =
            true;

        scrubberHourText.textContent =
            "—";

        scrubberStartText.textContent =
            "—";

        scrubberEndText.textContent =
            "—";

        return;
    }

    forecastScrubber.min =
        "0";

    forecastScrubber.max =
        String(
            files.length - 1
        );

    forecastScrubber.step =
        "1";

    forecastScrubber.value =
        String(
            state.frameIndex
        );

    forecastScrubber.disabled =
        (
            files.length
            <=
            1
        );

    const current =
        files[
            state.frameIndex
        ];

    scrubberHourText.textContent =
        formatForecastHour(
            current.forecast_hour
        );

    scrubberStartText.textContent =
        formatForecastHour(
            files[
                0
            ].forecast_hour
        );

    scrubberEndText.textContent =
        formatForecastHour(
            files[
                files.length - 1
            ].forecast_hour
        );
}


function renderHourGrid() {

    syncForecastScrubber();


    hourGrid.innerHTML =
        "";

    if (
        !state.selectionFiles
        ||
        state.selectionFiles.length
        ===
        0
    ) {

        return;
    }

    state.selectionFiles.forEach(
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

            button.textContent =
                String(
                    Number(
                        file.forecast_hour
                    )
                ).padStart(
                    3,
                    "0"
                );

            if (
                index
                ===
                state.frameIndex
            ) {

                button.classList.add(
                    "selected"
                );
            }

            button.addEventListener(
                "click",
                () => {

                    stopAnimation();

                    state.frameIndex =
                        index;

                    state.forecastHour =
                        Number(
                            file.forecast_hour
                        );

                    renderCurrentFrame();
                }
            );

            hourGrid.appendChild(
                button
            );
        }
    );
}


function renderNoData(
    message
) {

    mapImage.style.display =
        "none";

    mapImage.removeAttribute(
        "src"
    );

    loadingText.style.display =
        "flex";

    loadingText.textContent =
        (
            message
            ??
            "No forecast data available."
        );

    updateFrameInformation();

    updateNavigationButtons();

    renderHourGrid();
}


function renderCurrentFrame() {

    if (
        !state.selectionFiles
        ||
        state.selectionFiles.length
        ===
        0
    ) {

        renderNoData(
            "No forecast frames available for this selection."
        );

        return;
    }

    if (
        state.frameIndex
        <
        0
    ) {

        state.frameIndex =
            0;
    }

    if (
        state.frameIndex
        >=
        state.selectionFiles.length
    ) {

        state.frameIndex =
            state.selectionFiles.length
            -
            1;
    }

    const current =
        state.selectionFiles[
            state.frameIndex
        ];

    state.forecastHour =
        Number(
            current.forecast_hour
        );

    loadingText.style.display =
        "flex";

    loadingText.textContent =
        "Loading map...";

    mapImage.onload =
        () => {

            loadingText.style.display =
                "none";

            mapImage.style.display =
                "block";
        };

    mapImage.onerror =
        () => {

            loadingText.style.display =
                "flex";

            loadingText.textContent =
                "Map image could not be loaded.";

            mapImage.style.display =
                "none";
        };

    mapImage.src =
        addCacheBuster(
            current.url
        );

    mapImage.alt =
        (
            getDisplayModelName()
            +
            " "
            +
            formatProductName(
                current.product
            )
            +
            " "
            +
            formatRegionName(
                current.region
            )
            +
            " "
            +
            formatForecastHour(
                current.forecast_hour
            )
        );

    updateFrameInformation();

    updateNavigationButtons();

    renderHourGrid();
}


function previousFrame() {

    if (
        !state.selectionFiles
        ||
        state.selectionFiles.length
        ===
        0
    ) {

        return;
    }

    state.frameIndex -=
        1;

    if (
        state.frameIndex
        <
        0
    ) {

        state.frameIndex =
            state.selectionFiles.length
            -
            1;
    }

    renderCurrentFrame();
}


function nextFrame() {

    if (
        !state.selectionFiles
        ||
        state.selectionFiles.length
        ===
        0
    ) {

        return;
    }

    state.frameIndex +=
        1;

    if (
        state.frameIndex
        >=
        state.selectionFiles.length
    ) {

        state.frameIndex =
            0;
    }

    renderCurrentFrame();
}


function animationDelay() {

    const value =
        Number(
            speedSelect.value
        );

    if (
        Number.isFinite(
            value
        )
        &&
        value
        >
        0
    ) {

        return value;
    }

    return 800;
}


function stopAnimation() {

    if (
        state.animationTimer
    ) {

        clearInterval(
            state.animationTimer
        );

        state.animationTimer =
            null;
    }

    state.playing =
        false;

    playButton.textContent =
        "▶ Play";
}


function startAnimation() {

    if (
        !state.selectionFiles
        ||
        state.selectionFiles.length
        <=
        1
    ) {

        return;
    }

    stopAnimation();

    state.playing =
        true;

    playButton.textContent =
        "❚❚ Pause";

    state.animationTimer =
        setInterval(
            () => {

                nextFrame();

            },
            animationDelay()
        );
}


function toggleAnimation() {

    if (
        state.playing
    ) {

        stopAnimation();
    }

    else {

        startAnimation();
    }
}


async function loadModel(
    modelId,
    {
        preserveSelection = false,
    } = {}
) {

    stopAnimation();

    state.modelId =
        modelId;

    modelSelect.value =
        modelId;

    loadingText.style.display =
        "flex";

    loadingText.textContent =
        (
            "Loading "
            +
            getDisplayModelName()
            +
            "..."
        );

    mapImage.style.display =
        "none";

    availabilityBadge.textContent =
        "Loading";

    availabilityBadge.className =
        "availability-badge loading";

    try {

        const rawManifest =
            await loadRawManifest(
                modelId
            );

        state.manifest =
            normalizeManifest(
                rawManifest
            );

        state.files =
            state.manifest.files;

        if (
            !preserveSelection
        ) {

            state.region =
                null;

            state.product =
                null;

            state.forecastHour =
                null;

            state.frameIndex =
                0;
        }

        populateRegions();

        populateProducts();

        updateSelectionFiles();

        updateHeader();

        renderCurrentFrame();

    }

    catch (
        error
    ) {

        console.error(
            error
        );

        state.manifest =
            null;

        state.files =
            [];

        state.selectionFiles =
            [];

        state.region =
            null;

        state.product =
            null;

        state.forecastHour =
            null;

        state.frameIndex =
            0;

        modelText.textContent =
            getDisplayModelName();

        cycleText.textContent =
            "Cycle unavailable";

        availabilityBadge.textContent =
            "Unavailable";

        availabilityBadge.className =
            "availability-badge unavailable";

        regionSelect.innerHTML =
            "";

        productSelect.innerHTML =
            "";

        renderNoData(
            (
                getDisplayModelName()
                +
                " does not have a published cycle available yet."
            )
        );
    }
}


async function refreshCurrentModel() {

    const previousCycle =
        state.manifest?.cycle
        ??
        state.manifest?.cycle_id
        ??
        null;

    const previousFileCount =
        state.files.length;

    const previousRegion =
        state.region;

    const previousProduct =
        state.product;

    const previousHour =
        state.forecastHour;

    try {

        const rawManifest =
            await loadRawManifest(
                state.modelId
            );

        const refreshed =
            normalizeManifest(
                rawManifest
            );

        const refreshedCycle =
            refreshed.cycle
            ??
            refreshed.cycle_id
            ??
            null;

        const changed =
            (
                refreshedCycle
                !==
                previousCycle
            )
            ||
            (
                refreshed.files.length
                !==
                previousFileCount
            );

        if (
            !changed
        ) {

            return;
        }

        state.manifest =
            refreshed;

        state.files =
            refreshed.files;

        state.region =
            previousRegion;

        state.product =
            previousProduct;

        state.forecastHour =
            previousHour;

        populateRegions();

        populateProducts();

        updateSelectionFiles();

        updateHeader();

        renderCurrentFrame();

    }

    catch (
        error
    ) {

        console.debug(
            "Background manifest refresh failed:",
            error
        );
    }
}


modelSelect.addEventListener(
    "change",
    () => {

        loadModel(
            modelSelect.value
        );
    }
);


regionSelect.addEventListener(
    "change",
    () => {

        stopAnimation();

        state.region =
            regionSelect.value;

        state.product =
            null;

        state.forecastHour =
            null;

        state.frameIndex =
            0;

        populateProducts();

        updateSelectionFiles();

        renderCurrentFrame();
    }
);


productSelect.addEventListener(
    "change",
    () => {

        stopAnimation();

        state.product =
            productSelect.value;

        state.forecastHour =
            null;

        state.frameIndex =
            0;

        updateSelectionFiles();

        renderCurrentFrame();
    }
);


speedSelect.addEventListener(
    "change",
    () => {

        if (
            state.playing
        ) {

            startAnimation();
        }
    }
);


prevButton.addEventListener(
    "click",
    () => {

        stopAnimation();

        previousFrame();
    }
);


playButton.addEventListener(
    "click",
    () => {

        toggleAnimation();
    }
);


nextButton.addEventListener(
    "click",
    () => {

        stopAnimation();

        nextFrame();
    }
);


document.addEventListener(
    "keydown",
    event => {

        const target =
            event.target;

        if (
            target
            &&
            (
                target.tagName
                ===
                "INPUT"
                ||
                target.tagName
                ===
                "SELECT"
                ||
                target.tagName
                ===
                "TEXTAREA"
            )
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

            previousFrame();
        }

        else if (
            event.key
            ===
            "ArrowRight"
        ) {

            event.preventDefault();

            stopAnimation();

            nextFrame();
        }

        else if (
            event.code
            ===
            "Space"
        ) {

            event.preventDefault();

            toggleAnimation();
        }
    }
);


populateModelSelect();


loadModel(
    state.modelId
);


setInterval(
    () => {

        refreshCurrentModel();

    },
    30000
);

forecastScrubber.addEventListener(
    "input",
    () => {

        if (
            !state.selectionFiles
            ||
            state.selectionFiles.length
            ===
            0
        ) {

            return;
        }

        stopAnimation();

        const index =
            Math.max(
                0,
                Math.min(
                    state.selectionFiles.length - 1,
                    Number(
                        forecastScrubber.value
                    )
                )
            );

        state.frameIndex =
            index;

        state.forecastHour =
            Number(
                state.selectionFiles[
                    index
                ].forecast_hour
            );

        renderCurrentFrame();
    }
);


