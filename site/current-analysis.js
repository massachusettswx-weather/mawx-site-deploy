const datasets =
    window.CURRENT_ANALYSIS_DATASETS
    ?? {};


const datasetSelect =
    document.getElementById(
        "dataset-select"
    );


const variableSelect =
    document.getElementById(
        "variable-select"
    );


const levelSelect =
    document.getElementById(
        "level-select"
    );


const datasetName =
    document.getElementById(
        "dataset-name"
    );


const datasetStatus =
    document.getElementById(
        "dataset-status"
    );


const datasetCoverage =
    document.getElementById(
        "dataset-coverage"
    );


const datasetLatency =
    document.getElementById(
        "dataset-latency"
    );


const oceanDatasets =
    document.getElementById(
        "ocean-datasets"
    );


const futureDatasets =
    document.getElementById(
        "future-datasets"
    );


// ============================================================
// DATASET OPTIONS
// ============================================================

function populateDatasets() {

    datasetSelect.innerHTML = "";

    for (
        const dataset
        of Object.values(
            datasets
        )
    ) {

        const option =
            document.createElement(
                "option"
            );

        option.value =
            dataset.id;

        option.textContent =
            dataset.enabled
                ? dataset.name
                : `${dataset.name} — Planned`;

        datasetSelect.appendChild(
            option
        );
    }


    if (
        datasets.era5
    ) {

        datasetSelect.value =
            "era5";
    }
}


// ============================================================
// VARIABLE OPTIONS
// ============================================================

function populateVariables(
    dataset
) {

    variableSelect.innerHTML =
        "";

    const variables =
        Object.values(
            dataset.variables
            ?? {}
        );


    if (
        variables.length
        ===
        0
    ) {

        const option =
            document.createElement(
                "option"
            );

        option.value = "";

        option.textContent =
            "No variables configured yet";

        variableSelect.appendChild(
            option
        );

        variableSelect.disabled =
            true;

        return;
    }


    variableSelect.disabled =
        false;


    for (
        const variable
        of variables
    ) {

        const option =
            document.createElement(
                "option"
            );

        option.value =
            variable.id;

        option.textContent =
            variable.name;

        variableSelect.appendChild(
            option
        );
    }
}


// ============================================================
// CAPABILITY CONTROLS
// ============================================================

function updateCapabilities(
    dataset
) {

    const capabilities =
        dataset.capabilities
        ?? {};


    levelSelect.disabled =
        !capabilities.pressure_level;


    document
        .getElementById(
            "date-select"
        )
        .disabled =
            !capabilities.date;


    document
        .getElementById(
            "region-select"
        )
        .disabled =
            !capabilities.region;
}


// ============================================================
// STATUS
// ============================================================

function updateDatasetStatus(
    dataset
) {

    datasetName.textContent =
        dataset.name;


    datasetStatus.textContent =
        dataset.enabled
            ? "Available"
            : "Planned";


    const coverage =
        dataset.coverage
        ?? {};


    if (
        coverage.start
    ) {

        datasetCoverage.textContent =
            coverage.end
                ? (
                    `${coverage.start} – `
                    +
                    `${coverage.end}`
                )
                : (
                    `${coverage.start} – Present`
                );

    }

    else {

        datasetCoverage.textContent =
            "Not configured";
    }


    datasetLatency.textContent =
        coverage.latency
        ?? "Not configured";
}


// ============================================================
// DATASET CARDS
// ============================================================

function renderDatasetLists() {

    oceanDatasets.innerHTML =
        "";

    futureDatasets.innerHTML =
        "";


    for (
        const dataset
        of Object.values(
            datasets
        )
    ) {

        if (
            dataset.category
            ===
            "SST / Ocean"
        ) {

            const item =
                document.createElement(
                    "div"
                );

            item.className =
                "dataset-row";

            item.innerHTML =
                `
                <span>
                    ${dataset.name}
                </span>

                <span class="${
                    dataset.enabled
                        ? "dataset-active"
                        : "dataset-planned"
                }">
                    ${
                        dataset.enabled
                            ? "Available"
                            : "Planned"
                    }
                </span>
                `;

            oceanDatasets.appendChild(
                item
            );
        }
    }


    for (
        const dataset
        of Object.values(
            datasets
        )
    ) {

        if (
            dataset.enabled
        ) {

            continue;
        }


        const item =
            document.createElement(
                "div"
            );

        item.className =
            "dataset-row";


        item.innerHTML =
            `
            <span>
                ${dataset.name}
            </span>

            <span class="dataset-planned">
                Registered
            </span>
            `;


        futureDatasets.appendChild(
            item
        );
    }
}


// ============================================================
// SELECTION
// ============================================================

function updateDatasetSelection() {

    const dataset =
        datasets[
            datasetSelect.value
        ];


    if (
        !dataset
    ) {

        return;
    }


    populateVariables(
        dataset
    );


    updateCapabilities(
        dataset
    );


    updateDatasetStatus(
        dataset
    );
}


// ============================================================
// EVENTS
// ============================================================

datasetSelect.addEventListener(
    "change",
    updateDatasetSelection
);


// ============================================================
// STARTUP
// ============================================================

populateDatasets();

renderDatasetLists();

updateDatasetSelection();
