with hex_features as (
    select * from {{ ref('int_hex_feature') }}
),

unified_stops as (
    select 
        s.stop_id,
        s.stop_geometry,
        coalesce(c.walkable_population_800m, 0) as walkable_population,
        coalesce(ss.daily_trips, 0) as daily_trips
    from {{ ref('stg_gtfs_stops') }} as s
    left join {{ ref('mrt_transit_catchments') }} as c 
        on s.stop_id = c.stop_id
    left join (
        select stop_id, sum(total_trips_per_hour) as daily_trips 
        from {{ ref('stg_gtfs_service_hour') }} 
        group by stop_id
    ) as ss 
        on s.stop_id = ss.stop_id
),

-- Spatial Join: Drop the stops into the hexes (hammering the spatial index)
hex_stop_intersections as (
    select 
        h.hex_id,
        u.stop_id,
        u.walkable_population,
        u.daily_trips
    from hex_features as h
    inner join unified_stops as u 
        on st_intersects(h.hex_geometry, u.stop_geometry)
),

-- Aggregation: Roll up transit metrics to the hex level
hex_stop_aggregates as (
    select 
        hex_id,
        count(distinct stop_id) as transit_stop_count,
        
        -- Average the population to avoid double counting people living between close stops in one hex
        cast(avg(walkable_population) as int64) as precinct_population,
        
        sum(daily_trips) as precinct_daily_trips
    from hex_stop_intersections
    group by hex_id
)

-- Final Join: Bring it all together for the dashboard
select
    h.hex_id,
    h.hex_geometry,
    
    -- OSM: Active transport and amenities
    h.total_poi_count,
    h.cycleway_count,
    h.walkway_count,
    h.car_parking_count,
    h.retail_count,
    
    -- GTFS/ABS: Transit supply and demand
    coalesce(a.transit_stop_count, 0) as transit_stop_count,
    coalesce(a.precinct_population, 0) as precinct_population,
    coalesce(a.precinct_daily_trips, 0) as precinct_daily_trips,
    
    -- Demand/Supply proxies: I'll scale and cluster these in Python later
    coalesce(a.precinct_population, 0) + (h.total_poi_count * 10) as demand_proxy,
    coalesce(a.precinct_daily_trips, 0) + (h.cycleway_count * 50) as supply_proxy
    
from hex_features as h
left join hex_stop_aggregates as a
    on h.hex_id = a.hex_id