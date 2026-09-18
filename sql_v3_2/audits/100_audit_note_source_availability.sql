-- Audit MIMIC-IV-Note/CXR installation without reading note content.
-- Safe when mimiciv_note is absent.

drop table if exists study_ahf_v3_2.audit_100_note_source_availability_v1;

create table study_ahf_v3_2.audit_100_note_source_availability_v1 as
select
    x.source_name,
    x.expected_schema,
    x.expected_table,
    exists (
        select 1 from information_schema.tables t
        where t.table_schema = x.expected_schema
          and t.table_name = x.expected_table
    ) as table_exists,
    case when exists (
        select 1 from information_schema.tables t
        where t.table_schema = x.expected_schema
          and t.table_name = x.expected_table
    ) then 'available_for_qc' else 'not_installed' end as status
from (values
    ('MIMIC-IV-Note discharge', 'mimiciv_note', 'discharge'),
    ('MIMIC-IV-Note radiology', 'mimiciv_note', 'radiology'),
    ('MIMIC-IV-Note discharge detail', 'mimiciv_note', 'discharge_detail'),
    ('MIMIC-IV-Note radiology detail', 'mimiciv_note', 'radiology_detail'),
    ('MIMIC-CXR report source', 'mimiciv_cxr', 'cxr')
) as x(source_name, expected_schema, expected_table);

select * from study_ahf_v3_2.audit_100_note_source_availability_v1
order by source_name;

select table_schema, table_name, column_name, data_type
from information_schema.columns
where table_schema in ('mimiciv_note', 'mimiciv_cxr')
order by table_schema, table_name, ordinal_position;

