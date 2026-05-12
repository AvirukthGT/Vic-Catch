with source as (
    select * from {{ source('datalake', 'ext_abs_demographics') }}
),

renamed as (
    select
        SA1_CODE21 as sa1_id,
        cast(total_population as int64) as total_population,
        
        geometry as sa1_geometry
    from source
)

select * from renamed