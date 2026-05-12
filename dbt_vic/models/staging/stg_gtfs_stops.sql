with source as (
    select * from {{ source('datalake', 'ext_gtfs_stops') }}
),

renamed as (
    select
        stop_id,
        stop_name,
        cast(stop_lat as float64) as latitude,
        cast(stop_lon as float64) as longitude,
        
        --  turn raw lat/lon into a BigQuery Point Geometry
        ST_GEOGPOINT(cast(stop_lon as float64), cast(stop_lat as float64)) as stop_geometry,
        
        network_type
    from source
)

select * from renamed