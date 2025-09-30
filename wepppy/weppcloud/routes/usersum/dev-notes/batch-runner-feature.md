# WEPPcloud Batch Runner

A developer and administrator tool to run batches of watersheds with the same configuration

## User Story

1. A user with very special credentials loads a "Create Batch Runs" page
2. On the "Create Batch Runs" page the user specifies
   - config to use for the batch runs
   - a name for the batch project
3. On submit the backend
   - creates a directory batch project in /wc1/batch/<project_name>
   - creates a Batch Runner instance /wc1/batch/<project_name>/batch_runner.nodb
   - creates a base project with the config in /wc1/batch/<project_name>/_base
     - we end up with the NoDb singletons in _base (ron.nodb, climate.nodb, etc.) and the directories
     - Omni should always be added to the project.
4. User is redirected to the "WEPPcloud Batch Runner" page `/batch/<project_name>/`
5. On the WEPPcloud Batch Runner
   - The user has a new Batch Runner Control where they
     - Upload a .geojson file to the resources directory  (`/wc1/batch/<project_name>/resources`
     - BatchRunner stores the relative path as the `watershed_geojson` property
     - The user specifies a template string generating the `runid` of the watersheds based on the feature properties in the geojson
       - e.g. the template string could be something like "{properties['HucName']}-{properties['Region']}"
       - User has a Validate button to generate the runids from the geojson and template string. The validation checks that they are unique and provides them in the view for review
     - The user has a list of checkboxes that are all checked by default specifying which tasks they want to run for each project
       - Watershed Delineation and Abstraction
       - Landuse
       - Soils
       - Climate
       - WEPP
       - WATAR
       - Omni Scenarios
     - User has a Force Rebuild option that will always run the task for the project
     - User has a "Run Batch" button
       - BatchRunner(ControlBase) serializes all _base controller forms and submits them to `batch_runner_bp`
       - creates a new rq parent job
       - Iterate over the watersheds
         - to create new runids
           - generate `runid` using template string 
           - create `wd` is `/wc1/batch/<project_name>/<runid>`
           - copy the contents of the `_base` project to `/wc1/batch/<project_name>/<runid>`
           - hijack using `json` set ['py/state']['wd'] to the correct runid (similiar to omni)
           - clear locks and nodb cache (similiar to omni)
         - based on run state data stored in BatchRunner and force_rebuild determine if the tasks need to be ran
         - adds jobs to rq parent job with rq job dependency set appropriately.
6. Below the Batch Runner Control will be the run view for the _base project in the same order as `run_0.runs_0`
   - Controls for _base project
     - SBS Upload
     - Channel Delineation
     - Subcatchment Delineation
     - Landuse
     - Soils
     - Climate
     - WEPP
     - Omni
   - The page will be bootstrapped to remove the Build/Run buttons of these controls
   - The user goes through and sets all the options as desired.
   - "Run Batch" updates the `_base` project before running tasks, then when the files are created all of this configuration will be configured to run

## Key Components

### `BatchRunner(NoDbBase)`

- Retains state related to the batch runner and tracks which projects have been ran
- runs the projects using rq worker pool

### `BatchRunner(ControlBase)`

- follows controller_js singleton model

### `batch_runner_bp` routes for the Batch Runner

#### Routes

##### `/batch/create/` Create New BatchRunner project
- specify the config to use
- specify a `batch_name` (must be less 30 characters, lowercase, no special characters)

#####

- View based on `run_0.runs_0` with `BatchRunner(ControlBase)`

## RQ Worker Pool

- spin up limited number of workers e.g. 3 on a special batch channel. Then BatchRunner submits jobs to these worker to limit the number that are processed. greatly scalable via kubernetes.
