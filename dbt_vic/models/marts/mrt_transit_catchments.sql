with stops as (
    select * from {{ ref('stg_gtfs_stops') }}
),

demographics as (
    select * from {{ ref('stg_abs_demographics') }}
),

-- Find all SA1 blocks within 800 meters of a stop
catchment_areas as (
    select
        s.stop_id,
        s.stop_name,
        s.network_type,
        s.stop_geometry,
        d.sa1_id,
        d.total_population
    from stops as s
    inner join demographics as d
        -- ST_DWithin checks if the distance between the two shapes is <= 800 meters
        on st_dwithin(s.stop_geometry, d.sa1_geometry, 800)
),

-- Sum up the population for every unique stop
catchment_summary as (
    select
        stop_id,
        max(stop_name) as stop_name,
        max(network_type) as network_type,
        
        -- Keep the geometry so I can visualize this on a map later
        any_value(stop_geometry) as stop_geometry,
        
        count(distinct sa1_id) as intersecting_sa1_blocks,
        sum(total_population) as walkable_population_800m
    from catchment_areas
    group by stop_id
)

select * from catchment_summary