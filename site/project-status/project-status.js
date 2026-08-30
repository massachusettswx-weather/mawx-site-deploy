"use strict";


/* ============================================================
   MASSACHUSETTSWX MASTER DEVELOPMENT ROADMAP
   ============================================================ */

const PROJECTS = [

    {
        id: 1,

        title:
            "Current Analysis: 10 hPa / 60°N zonal-wind system",

        priority:
            "P0",

        status:
            "in-progress",

        description:
            "ERA5 1940–present climatology and current-year zonal-wind chart. Use ERA5 where available and append GFS analysis for the newest days. Add freshness metadata and later month/season selection.",
    },


    {
        id: 2,

        title:
            "New MassachusettsWx home page",

        priority:
            "P0",

        status:
            "in-progress",

        description:
            "Create a true landing page for Forecast Models, Current Analysis, Reanalysis Tools, Tropical, SST/Ocean Analysis, Climate, and latest-data status information.",
    },


    {
        id: 3,

        title:
            "General Current Analysis / observational-data framework",

        priority:
            "P0",

        status:
            "todo",

        description:
            "Build reusable analysis architecture for ERA5, OSTIA, NOAA Coral Reef Watch, NOAA OISST, and future datasets with common dataset, variable, date, region, level, freshness, and caching controls.",
    },


    {
        id: 4,

        title:
            "On-demand ERA5 1940–present explorer using ARCO",

        priority:
            "P1",

        status:
            "todo",

        description:
            "Allow users to select a date, variable, pressure level, and region. Retrieve only the needed ERA5 ARCO slice and cache popular requests. Later support hourly fields, anomalies, climatologies, and date comparisons.",
    },


    {
        id: 5,

        title:
            "Reusable dataset catalog / data browser",

        priority:
            "P1",

        status:
            "todo",

        description:
            "Create a searchable catalog of atmospheric reanalysis, SST, ocean, tropical, forecast-model, and satellite-derived datasets with coverage, resolution, update cadence, and source information.",
    },


    {
        id: 6,

        title:
            "Expand deterministic model support",

        priority:
            "P1",

        status:
            "in-progress",

        description:
            "Continue GFS, IFS, and AIFS integration and expand through shared model configuration to additional systems such as GDPS, ICON, UKMET where practical, and future AI models.",
    },


    {
        id: 7,

        title:
            "HAFS support",

        priority:
            "P1/P2",

        status:
            "todo",

        description:
            "Add storm-centric HAFS support including storm and cycle selection, HAFS-A/HAFS-B, track and intensity products, storm-centered meteorological fields, and Tropical-section integration.",
    },


    {
        id: 8,

        title:
            "SST / ocean-analysis section",

        priority:
            "P1",

        status:
            "todo",

        description:
            "Support OSTIA, NOAA OISST, NOAA Coral Reef Watch, SST anomalies, marine heatwave or percentile products, dataset comparisons, and useful ocean-region presets.",
    },


    {
        id: 9,

        title:
            "Interactive historical comparison tools",

        priority:
            "P2",

        status:
            "todo",

        description:
            "Generalize the stratospheric-wind concept so users can select variable, pressure level, latitude or region, month, and years, with historical envelopes and current-year traces.",
    },


    {
        id: 10,

        title:
            "Unified site search / Find a Product",

        priority:
            "P2",

        status:
            "todo",

        description:
            "Allow searches such as 850 wind anomaly, SST, HAFS, or ERA5 August 1954 and route users directly to the relevant model, analysis product, dataset, or tool.",
    },


    {
        id: 11,

        title:
            "Data freshness / status dashboard",

        priority:
            "P2",

        status:
            "todo",

        description:
            "Show latest model cycles and forecast hours, latest ERA5/OSTIA/OISST/CRW dates, and operational states such as Updating, Waiting Upstream, Complete, and Delayed.",
    },


    {
        id: 12,

        title:
            "Shareable URLs",

        priority:
            "P2",

        status:
            "todo",

        description:
            "Store selections such as model, product, region, forecast hour, dataset, date, and other view state in the URL so exact views can be shared.",
    },


    {
        id: 13,

        title:
            "Download / export tools",

        priority:
            "P3",

        status:
            "todo",

        description:
            "Support PNG downloads, future small CSV or NetCDF data slices, permanent links, and easy copying of source and attribution information.",
    },


    {
        id: 14,

        title:
            "Comparison mode",

        priority:
            "P3",

        status:
            "todo",

        description:
            "Add side-by-side model and dataset comparisons such as GFS versus IFS versus AIFS, ERA5 versus operational analysis, and OSTIA versus OISST, eventually including difference maps.",
    },


    {
        id: 15,

        title:
            "Future ideas bucket",

        priority:
            "Unranked",

        status:
            "todo",

        description:
            "Capture new MassachusettsWx feature ideas here first before assigning them a permanent priority and development position.",
    },

];


/* ============================================================
   STATUS LABELS
   ============================================================ */

const STATUS_LABELS = {

    "todo":
        "To Do",

    "in-progress":
        "In Progress",

    "completed":
        "Completed",

};


/* ============================================================
   DOM REFERENCES
   ============================================================ */

const todoList =
    document.getElementById(
        "todoList"
    );

const progressList =
    document.getElementById(
        "progressList"
    );

const completedList =
    document.getElementById(
        "completedList"
    );


const todoCount =
    document.getElementById(
        "todoCount"
    );

const progressColumnCount =
    document.getElementById(
        "progressColumnCount"
    );

const completedColumnCount =
    document.getElementById(
        "completedColumnCount"
    );


const totalCount =
    document.getElementById(
        "totalCount"
    );

const progressCount =
    document.getElementById(
        "progressCount"
    );

const completedCount =
    document.getElementById(
        "completedCount"
    );


/* ============================================================
   CARD CREATION
   ============================================================ */

function createProjectCard(
    project
) {

    const card =
        document.createElement(
            "article"
        );

    card.className =
        "project-card";

    card.dataset.status =
        project.status;


    const top =
        document.createElement(
            "div"
        );

    top.className =
        "project-card-top";


    const number =
        document.createElement(
            "span"
        );

    number.className =
        "project-number";

    number.textContent =
        `#${project.id}`;


    const priority =
        document.createElement(
            "span"
        );

    priority.className =
        "priority-badge";

    priority.dataset.priority =
        project.priority;

    priority.textContent =
        project.priority;


    top.appendChild(
        number
    );

    top.appendChild(
        priority
    );


    const title =
        document.createElement(
            "h4"
        );

    title.textContent =
        project.title;


    const description =
        document.createElement(
            "p"
        );

    description.className =
        "project-description";

    description.textContent =
        project.description;


    const status =
        document.createElement(
            "span"
        );

    status.className =
        "project-status-label";

    status.textContent =
        STATUS_LABELS[
            project.status
        ]
        ||
        project.status;


    card.appendChild(
        top
    );

    card.appendChild(
        title
    );

    card.appendChild(
        description
    );

    card.appendChild(
        status
    );


    return card;
}


/* ============================================================
   EMPTY COLUMN
   ============================================================ */

function addEmptyMessage(
    container,
    text
) {

    const empty =
        document.createElement(
            "div"
        );

    empty.className =
        "empty-column";

    empty.textContent =
        text;

    container.appendChild(
        empty
    );
}


/* ============================================================
   RENDER ROADMAP
   ============================================================ */

function renderRoadmap() {

    todoList.replaceChildren();

    progressList.replaceChildren();

    completedList.replaceChildren();


    const todo =
        PROJECTS.filter(
            (project) =>
                project.status
                ===
                "todo"
        );

    const progress =
        PROJECTS.filter(
            (project) =>
                project.status
                ===
                "in-progress"
        );

    const completed =
        PROJECTS.filter(
            (project) =>
                project.status
                ===
                "completed"
        );


    /*
     * Preserve the master roadmap order.
     */
    const byId =
        (
            first,
            second
        ) =>
            first.id
            -
            second.id;


    todo.sort(
        byId
    );

    progress.sort(
        byId
    );

    completed.sort(
        byId
    );


    for (
        const project
        of todo
    ) {

        todoList.appendChild(
            createProjectCard(
                project
            )
        );
    }


    for (
        const project
        of progress
    ) {

        progressList.appendChild(
            createProjectCard(
                project
            )
        );
    }


    for (
        const project
        of completed
    ) {

        completedList.appendChild(
            createProjectCard(
                project
            )
        );
    }


    if (
        todo.length
        ===
        0
    ) {

        addEmptyMessage(
            todoList,
            "No planned items."
        );
    }


    if (
        progress.length
        ===
        0
    ) {

        addEmptyMessage(
            progressList,
            "Nothing is currently in progress."
        );
    }


    if (
        completed.length
        ===
        0
    ) {

        addEmptyMessage(
            completedList,
            "Completed projects will appear here."
        );
    }


    todoCount.textContent =
        String(
            todo.length
        );

    progressColumnCount.textContent =
        String(
            progress.length
        );

    completedColumnCount.textContent =
        String(
            completed.length
        );


    totalCount.textContent =
        String(
            PROJECTS.length
        );

    progressCount.textContent =
        String(
            progress.length
        );

    completedCount.textContent =
        String(
            completed.length
        );
}


/* ============================================================
   START
   ============================================================ */

renderRoadmap();
