## Omni is functionality for running scenarios inside of a parent weppcloud project


### Omni scenarios

- **Uniform High Severity**: Forest, shrubs, and grasses burned at high soil burn severity
- **Uniform Moderate Severity**: Forest, shrubs, and grasses burned at moderate soil burn severity
- **Uniform Low Severity**: Forest, shrubs, and grasses burned at low soil burn severity
- **Soil Burn Severity Map**: Forest, shrubs, and grasses burned at from soil burn severity (not implement, but easy to implement)
- **Thinning**: Forests use thinned management (pre-fire)
- **Mulching**: Mulching post fire (not implemented)
- **Seeding**: WIP (not implemented)

Scenarios are created within the `omni/scenarios` folder. Each scenario has it's own folder and is a weppcloud project.
It symlinks (equivalent of Windows shortcuts) to the parent project for shared inputs
The `wepp/output` folder contains all the hillslope and watershed files of a normal weppcloud project 


### Workflow

#### 1. Create Undisturbed weppcloud project

#### 2. Define omni scenarios

```python
omni = Omni.getInstance()
omni.scenarios = ['uniform_high', 'uniform_moderate', 'uniform_low', 'thinning']
```

#### 3. Run omni scenarios

```python
omni = Omni.getInstance()
omni.run_omni_scenarios()
```


#### 4. Objective parameter analysis to idenfity contrast hillslopes

Omni uses the gpkg exports to find hillslopes with high sediment, runoff, lateral flow, ...

Applies filter to limit selection of hillslopes


#### 5. Run Contrast Scenarios

Omni uses the gpkg exports to find hillslopes with high sediment, runoff, lateral flow, ...

Applies filter to limit selection of hillslopes


## Meeting with Bill and Pete (3/13/2025)

### Mulching
using multipling coverage to adjust the percent bare

e.g. start with 80% bare (from burn severity)

#### Current Burn Severity Covers -> **Mulch Treatment 1/2-ton / acre 30% cover**
- Forest
  - High 30% -> 60%
  - Moderate 60% -> 90% 
  - Low 85% -> 100%
- Shrub
  - High 30% -> 60%
  - Moderate 55% -> 85% 
  - Low 80% -> 100%
- Grass
  - High 10% -> 40% 
  - Moderate 35% -> 65% 
  - Low 60% -> 90%

#### Current Burn Severity Covers -> **Mulch Treatment 1-ton / acre 60% cover**
- Forest
  - High 30% -> 90%
  - Moderate 60% -> 100% 
  - Low 85% -> 100%
- Shrub
  - High 30% -> 90%
  - Moderate 55% -> 100% 
  - Low 80% -> 100%
- Grass
  - High 10% -> 70% 
  - Moderate 35% -> 95% 
  - Low 60% -> 100%

Initial burn covers could be regionally dependent. More veg before fire results in more after fire (Lewis)

#### Mulching Treatments

From ERMiT
- Mulching 47% ground cover (1 Mg/ha ~1/2 ton/ac)
- Mulching 72% ground cover (2 Mg/ha ~1 ton/ac)  
- Mulching 89% ground cover (3-1/2 Mg/ha ~1-1/2 ton/ac)
- Mulching 94% ground cover (4-1/2 Mg/ha ~2 ton/ac)

Pete

**1 ton / acre straw mulch is 60% cover** what everyone is doing in reality.

wood mulch is 4x more expensive


### Seeding

seeding would only impacts 2nd year after fire. need to know the cover change with and without cover to know the change in cover. (lack of data)

use revegetation database to look at cover changes

might be fires where there are treatment boundaries
