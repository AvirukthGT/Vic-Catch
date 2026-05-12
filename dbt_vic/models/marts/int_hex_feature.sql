with hex_grid as (
    select 
        hex_id,
        geometry as hex_geometry
    from {{ source('datalake', 'ext_hex_grid') }}
),

osm_features as (
    select * from {{ ref('stg_osm_features') }}
),

-- Spatial Join: Dropping the OSM points directly into the hexagons
hex_intersections as (
    select
        h.hex_id,
        h.hex_geometry,
        o.feature_group
    from hex_grid as h
    left join osm_features as o
        on st_intersects(h.hex_geometry, o.feature_geometry)
),

-- Aggregate to get the final profile of every hexagon
hex_profile as (
    select
        hex_id,
        any_value(hex_geometry) as hex_geometry,
        
        count(feature_group) as total_poi_count,
        sum(case when feature_group = 'walkway' then 1 else 0 end) as walkway_count,
        sum(case when feature_group = 'cycleway' then 1 else 0 end) as cycleway_count,
        sum(case when feature_group = 'bike_parking' then 1 else 0 end) as bike_parking_count,
        sum(case when feature_group = 'parking' then 1 else 0 end) as car_parking_count,
        sum(case when feature_group = 'retail_shop' then 1 else 0 end) as retail_count,
        sum(case when feature_group like 'zone_%' then 1 else 0 end) as landuse_diversity_count

    from hex_intersections
    group by hex_id
)

select * from hex_profile