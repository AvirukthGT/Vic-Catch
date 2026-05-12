{{ config(
    materialized='table',
    cluster_by=['hex_geometry']
) }}

select 
    hex_id,
    -- ensure it is cast properly for the spatial index
    ST_GEOGFROMTEXT(ST_ASTEXT(geometry)) as hex_geometry
from {{ source('datalake', 'ext_hex_grid') }}