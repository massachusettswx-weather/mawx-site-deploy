window.CURRENT_ANALYSIS_DATASETS = {

    era5: {
        id: "era5",
        name: "ECMWF ERA5",
        category: "Atmosphere / Reanalysis",

        enabled: true,
        status: "active",

        capabilities: {
            date: true,
            region: true,
            pressure_level: true,
            variable: true,
            climatology: true,
            anomaly: true,
            time_series: true,
            map: true
        },

        coverage: {
            start: "1940-01-01",
            end: null,
            latency: "ERA5 + recent GFS analysis extension"
        },

        variables: {
            u10_60n: {
                id: "u10_60n",
                name: "60°N Zonal-Mean Zonal Wind",
                units: "m/s",
                level: "10 hPa",
                view: "timeseries",

                source_strategy: {
                    primary: "era5",
                    recent_extension: "gfs_analysis"
                }
            }
        }
    },


    gfs_analysis: {
        id: "gfs_analysis",
        name: "NCEP GFS Analysis",
        category: "Atmosphere / Analysis",

        enabled: true,
        status: "active",

        capabilities: {
            date: true,
            region: true,
            pressure_level: true,
            variable: true,
            climatology: false,
            anomaly: false,
            time_series: true,
            map: true
        },

        coverage: {
            start: null,
            end: null,
            latency: "near real time"
        },

        variables: {
            u10_60n: {
                id: "u10_60n",
                name: "60°N Zonal-Mean Zonal Wind",
                units: "m/s",
                level: "10 hPa",
                view: "timeseries"
            }
        }
    },


    ostia: {
        id: "ostia",
        name: "OSTIA",
        category: "SST / Ocean",

        enabled: false,
        status: "planned",

        capabilities: {
            date: true,
            region: true,
            pressure_level: false,
            variable: true,
            climatology: false,
            anomaly: true,
            time_series: true,
            map: true
        },

        coverage: {
            start: null,
            end: null,
            latency: null
        },

        variables: {}
    },


    oisst: {
        id: "oisst",
        name: "NOAA OISST",
        category: "SST / Ocean",

        enabled: false,
        status: "planned",

        capabilities: {
            date: true,
            region: true,
            pressure_level: false,
            variable: true,
            climatology: true,
            anomaly: true,
            time_series: true,
            map: true
        },

        coverage: {
            start: null,
            end: null,
            latency: null
        },

        variables: {}
    },


    crw: {
        id: "crw",
        name: "NOAA Coral Reef Watch",
        category: "SST / Ocean",

        enabled: false,
        status: "planned",

        capabilities: {
            date: true,
            region: true,
            pressure_level: false,
            variable: true,
            climatology: false,
            anomaly: true,
            time_series: true,
            map: true
        },

        coverage: {
            start: null,
            end: null,
            latency: null
        },

        variables: {}
    }

};
