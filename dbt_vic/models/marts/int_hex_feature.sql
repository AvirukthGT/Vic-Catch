with hex_grid as (
    select * from {{ ref('stg_hex_grid') }}
),

osm_features as (
    select * from {{ ref('stg_osm_features') }}
),

-- Spatial Join: BQ should hammer the spatial index here
hex_intersections as (
    select
        h.hex_id,
        o.feature_group
    from hex_grid as h
    inner join osm_features as o
        on st_intersects(h.hex_geometry, o.feature_geometry)
),

-- Aggregation: Count everything up before I link back to the map
hex_aggregates as (
    select
        hex_id,
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

-- Final Join: Link back to the grid so I keep the empty hexes
select
    h.hex_id,
    h.hex_geometry,
    coalesce(a.total_poi_count, 0) as total_poi_count,
    coalesce(a.walkway_count, 0) as walkway_count,
    coalesce(a.cycleway_count, 0) as cycleway_count,
    coalesce(a.bike_parking_count, 0) as bike_parking_count,
    coalesce(a.car_parking_count, 0) as car_parking_count,
    coalesce(a.retail_count, 0) as retail_count,
    coalesce(a.landuse_diversity_count, 0) as landuse_diversity_count
from hex_grid as h
left join hex_aggregates as a
    on h.hex_id = a.hex_id