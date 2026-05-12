with stop_times as (
    select * from {{ source('datalake', 'ext_gtfs_stop_times') }}
),

trips as (
    select * from {{ source('datalake', 'ext_gtfs_trips') }}
),

routes as (
    select * from {{ source('datalake', 'ext_gtfs_routes') }}
),

-- 1. The Core GTFS Join
joined_service as (
    select
        st.stop_id,
        st.trip_id,
        st.arrival_time,
        
        -- Safely extract the hour even if it goes past 24:00:00 (e.g., '25:15:00' -> 25)
        cast(split(st.arrival_time, ':')[offset(0)] as int64) as hour_of_day,
        
        t.route_id,
        t.service_id,
        r.route_type
    from stop_times as st
    inner join trips as t 
        on st.trip_id = t.trip_id
    inner join routes as r 
        on t.route_id = r.route_id
    -- Filter out any malformed rows
    where st.arrival_time is not null
),

-- 2. Aggregate to the Stop-Hour grain
hourly_service_summary as (
    select
        stop_id,
        route_type,
        hour_of_day,
        count(trip_id) as total_trips_per_hour
    from joined_service
    group by 
        stop_id, 
        route_type, 
        hour_of_day
)

select * from hourly_service_summary