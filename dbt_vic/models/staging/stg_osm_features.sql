{{ config(
    materialized='table',
    cluster_by=['feature_geometry']
) }}

with source as (
    select * from {{ source('datalake', 'ext_osm_features') }}
),

renamed as (
    select
        osm_id,
        osm_type,
        feature_group,
        
        -- Keeping raw coordinates for debugging
        cast(lat as float64) as latitude,
        cast(lon as float64) as longitude,
        
        --  Create the BigQuery Geography Point
        ST_GEOGPOINT(cast(lon as float64), cast(lat as float64)) as feature_geometry
        
    from source
    -- Filter out any bad coordinates just in case
    where lat is not null and lon is not null
)

select * from renamed