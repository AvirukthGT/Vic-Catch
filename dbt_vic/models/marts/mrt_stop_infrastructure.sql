with stops as (
    select * from {{ ref('stg_gtfs_stops') }}
),

osm_features as (
    select * from {{ ref('stg_osm_features') }}
),

-- 1. The Spatial Join: Find all OSM features within 800 meters of a stop
stop_feature_intersections as (
    select
        s.stop_id,
        s.stop_name,
        s.network_type,
        s.stop_geometry,
        o.osm_id,
        o.feature_group
    from stops as s
    inner join osm_features as o
        -- Check if the infrastructure is within an 800m radius of the stop
        on st_dwithin(s.stop_geometry, o.feature_geometry, 800)
),

-- 2. The Feature Engineering: Pivot the feature groups into columns
infrastructure_profile as (
    select
        stop_id,
        max(stop_name) as stop_name,
        max(network_type) as network_type,
        any_value(stop_geometry) as stop_geometry,
        
        -- Conditional Aggregation to create our scoring columns
        sum(case when feature_group = 'cycleway' then 1 else 0 end) as nearby_cycleways,
        sum(case when feature_group = 'bike_parking' then 1 else 0 end) as nearby_bike_parking,
        sum(case when feature_group = 'walkway' then 1 else 0 end) as nearby_walkways,
        sum(case when feature_group = 'retail_shop' then 1 else 0 end) as nearby_retail,
        sum(case when feature_group = 'parking' then 1 else 0 end) as nearby_car_parking
        
    from stop_feature_intersections
    group by stop_id
)

select * from infrastructure_profile