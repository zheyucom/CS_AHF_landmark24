-- ============================================================
-- Project: CS_AHF_landmark24
-- File: sql/01_cohort/020_hf_icd_candidate.sql
-- Purpose:
--   Build a broad HF ICD candidate cohort from adult first ICU stays.
--
-- Important:
--   Diagnoses_icd represents discharge/billing diagnoses.
--   Therefore this table is only a broad HF candidate pool,
--   NOT the final AHF-at-ICU-admission cohort.
-- ============================================================

drop table if exists study_ahf_v4.cohort_020_hf_icd_candidate_v1 cascade;

create table study_ahf_v4.cohort_020_hf_icd_candidate_v1 as
with dx_clean as (
    select
        d.subject_id,
        d.hadm_id,
        d.seq_num,
        d.icd_version,
        upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) as icd_code_clean,
        d.icd_code as icd_code_raw,
        dd.long_title
    from mimiciv_hosp.diagnoses_icd d
    left join mimiciv_hosp.d_icd_diagnoses dd
        on d.icd_code = dd.icd_code
       and d.icd_version = dd.icd_version
),

hf_dx_flagged as (
    select
        subject_id,
        hadm_id,
        seq_num,
        icd_version,
        icd_code_clean,
        icd_code_raw,
        long_title,

        -- Broad HF codes:
        -- ICD-9: 428.*
        -- ICD-10: I50.*
        case
            when icd_version = 9
             and icd_code_clean like '428%'
                then 1

            when icd_version = 10
             and icd_code_clean like 'I50%'
                then 1

            else 0
        end as flag_i50_or_428,

        -- Hypertensive heart / heart-kidney disease with HF.
        -- These codes are not I50/428 but frequently indicate HF.
        case
            when icd_version = 9
             and icd_code_clean in (
                 '39891',
                 '40201','40211','40291',
                 '40401','40403','40411','40413','40491','40493'
             )
                then 1

            when icd_version = 10
             and icd_code_clean in (
                 'I110','I130','I132'
             )
                then 1

            else 0
        end as flag_hypertensive_hf,

        -- Acute or acute-on-chronic HF based on specific ICD subcodes.
        -- This is useful as supportive evidence, but still not enough
        -- to prove AHF was present exactly at ICU admission.
        case
            when icd_version = 9
             and icd_code_clean in (
                 '42821','42823',
                 '42831','42833',
                 '42841','42843'
             )
                then 1

            when icd_version = 10
             and icd_code_clean in (
                 'I5021','I5023',
                 'I5031','I5033',
                 'I5041','I5043',
                 'I50811','I50813'
             )
                then 1

            else 0
        end as flag_acute_or_acute_on_chronic

    from dx_clean
),

hf_dx_only as (
    select *
    from hf_dx_flagged
    where flag_i50_or_428 = 1
       or flag_hypertensive_hf = 1
       or flag_acute_or_acute_on_chronic = 1
),

hf_by_hadm as (
    select
        subject_id,
        hadm_id,

        1 as hf_icd_any,

        max(flag_i50_or_428) as hf_icd_i50_or_428,
        max(flag_hypertensive_hf) as hf_icd_hypertensive_hf,
        max(flag_acute_or_acute_on_chronic) as hf_icd_acute_or_acute_on_chronic,

        min(seq_num) as hf_icd_primary_seq,

        string_agg(
            distinct icd_code_clean,
            ', ' order by icd_code_clean
        ) as hf_icd_codes,

        string_agg(
            distinct coalesce(long_title, icd_code_clean),
            ' | ' order by coalesce(long_title, icd_code_clean)
        ) as hf_icd_titles

    from hf_dx_only
    group by subject_id, hadm_id
)

select
    c.*,

    h.hf_icd_any,
    h.hf_icd_i50_or_428,
    h.hf_icd_hypertensive_hf,
    h.hf_icd_acute_or_acute_on_chronic,
    h.hf_icd_primary_seq,
    h.hf_icd_codes,
    h.hf_icd_titles

from study_ahf_v4.cohort_010_adult_first_icu_v1 c
inner join hf_by_hadm h
    on c.subject_id = h.subject_id
   and c.hadm_id = h.hadm_id;
	 
	 
	 
	 
	 
-- 	 QC1:总体人数
select
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    min(anchor_age) as min_age,
    max(anchor_age) as max_age,
    min(icu_los_hours) as min_icu_los_hours,
    percentile_cont(0.5) within group (order by icu_los_hours) as median_icu_los_hours,
    max(icu_los_hours) as max_icu_los_hours
from study_ahf_v4.cohort_020_hf_icd_candidate_v1;




-- QC2：ICD 类型分布
select
    hf_icd_i50_or_428,
    hf_icd_hypertensive_hf,
    hf_icd_acute_or_acute_on_chronic,
    count(*) as n,
    round(
        count(*) * 100.0 /
        sum(count(*)) over (),
        2
    ) as pct
from study_ahf_v4.cohort_020_hf_icd_candidate_v1
group by
    hf_icd_i50_or_428,
    hf_icd_hypertensive_hf,
    hf_icd_acute_or_acute_on_chronic
order by n desc;




-- QC 3：HF ICD seq_num 分布
select
    case
        when hf_icd_primary_seq = 1 then '01_seq_1'
        when hf_icd_primary_seq between 2 and 5 then '02_seq_2_5'
        when hf_icd_primary_seq between 6 and 10 then '03_seq_6_10'
        when hf_icd_primary_seq > 10 then '04_seq_gt_10'
        else '99_missing'
    end as hf_seq_group,
    count(*) as n,
    round(
        count(*) * 100.0 /
        sum(count(*)) over (),
        2
    ) as pct
from study_ahf_v4.cohort_020_hf_icd_candidate_v1
group by
    case
        when hf_icd_primary_seq = 1 then '01_seq_1'
        when hf_icd_primary_seq between 2 and 5 then '02_seq_2_5'
        when hf_icd_primary_seq between 6 and 10 then '03_seq_6_10'
        when hf_icd_primary_seq > 10 then '04_seq_gt_10'
        else '99_missing'
    end
order by hf_seq_group;




-- QC 4：最常见 HF ICD codes
with dx_exploded as (
    select
        d.subject_id,
        d.hadm_id,
        d.seq_num,
        d.icd_version,
        upper(regexp_replace(d.icd_code, '[^A-Za-z0-9]', '', 'g')) as icd_code_clean,
        dd.long_title
    from mimiciv_hosp.diagnoses_icd d
    left join mimiciv_hosp.d_icd_diagnoses dd
        on d.icd_code = dd.icd_code
       and d.icd_version = dd.icd_version
    inner join study_ahf_v4.cohort_020_hf_icd_candidate_v1 c
        on d.subject_id = c.subject_id
       and d.hadm_id = c.hadm_id
)
select
    icd_version,
    icd_code_clean,
    coalesce(long_title, 'missing title') as long_title,
    count(*) as n,
    min(seq_num) as min_seq,
    percentile_cont(0.5) within group (order by seq_num) as median_seq
from dx_exploded
where
    (
        icd_version = 9
        and (
            icd_code_clean like '428%'
            or icd_code_clean in (
                '39891',
                '40201','40211','40291',
                '40401','40403','40411','40413','40491','40493'
            )
        )
    )
    or
    (
        icd_version = 10
        and (
            icd_code_clean like 'I50%'
            or icd_code_clean in ('I110','I130','I132')
        )
    )
group by
    icd_version,
    icd_code_clean,
    coalesce(long_title, 'missing title')
order by n desc
limit 50;





-- 写入 cohort flow
insert into study_ahf_v4.cohort_flow (
    step_id,
    step_name,
    table_name,
    n_rows,
    n_subjects,
    n_hadm,
    n_stay,
    excluded_from_prior,
    notes
)
select
    20 as step_id,
    'hf_icd_candidate' as step_name,
    'study_ahf_v4.cohort_020_hf_icd_candidate_v1' as table_name,
    count(*) as n_rows,
    count(distinct subject_id) as n_subjects,
    count(distinct hadm_id) as n_hadm,
    count(distinct stay_id) as n_stay,
    (
        select count(*)
        from study_ahf_v4.cohort_010_adult_first_icu_v1
    ) - count(*) as excluded_from_prior,
    'Broad HF ICD candidate based on discharge/billing ICD codes. Not final AHF-at-ICU-admission cohort.' as notes
from study_ahf_v4.cohort_020_hf_icd_candidate_v1;