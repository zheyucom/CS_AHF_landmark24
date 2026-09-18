-- Audit a more specific acute-care NT-proBNP rule-in sensitivity.
-- This does not replace the current phenotype or alter any model table.
-- ESC acute-HF rule-in cutoffs used here are age-stratified:
--   age <55: 450 pg/mL; age 55-75: 900 pg/mL; age >75: 1800 pg/mL.

drop table if exists study_ahf_v3_2.audit_104_ntprobnp_rulein_refinement_v1;

create table study_ahf_v3_2.audit_104_ntprobnp_rulein_refinement_v1 as
with x as (
    select
        c.stay_id,
        c.subject_id,
        c.hadm_id,
        c.final_state,
        p.age,
        c.ntprobnp_max_adm_to_t0,
        c.actual_iv_loop_emar_pre_t0_flag,
        case
            when p.age < 55 then 450
            when p.age <= 75 then 900
            else 1800
        end as ntprobnp_rulein_cutoff
    from study_ahf_v3_2.cohort_099_strict_pre_t0_ahf_v1 c
    join study_ahf_v3_2.model_090b_compact_predictors_v33_v1 p
      on p.stay_id = c.stay_id
)
select
    x.*,
    case when x.ntprobnp_max_adm_to_t0 >= x.ntprobnp_rulein_cutoff
         then 1 else 0 end as ntprobnp_age_rulein_flag,
    case when x.actual_iv_loop_emar_pre_t0_flag = 1
              and x.ntprobnp_max_adm_to_t0 >= x.ntprobnp_rulein_cutoff
         then 1 else 0 end as loop_plus_age_rulein_flag,
    case when x.actual_iv_loop_emar_pre_t0_flag = 1
              or x.ntprobnp_max_adm_to_t0 >= x.ntprobnp_rulein_cutoff
         then 1 else 0 end as loop_or_age_rulein_flag
from x;

create index if not exists idx_104_rulein_stay
    on study_ahf_v3_2.audit_104_ntprobnp_rulein_refinement_v1 (stay_id);

analyze study_ahf_v3_2.audit_104_ntprobnp_rulein_refinement_v1;

select
    count(*) as n_current_strict_candidate,
    count(*) filter (where ntprobnp_age_rulein_flag = 1) as n_age_rulein,
    count(*) filter (where actual_iv_loop_emar_pre_t0_flag = 1) as n_loop_emar,
    count(*) filter (where loop_plus_age_rulein_flag = 1) as n_loop_plus_age_rulein,
    count(*) filter (where loop_or_age_rulein_flag = 1) as n_loop_or_age_rulein,
    count(*) filter (where loop_or_age_rulein_flag = 1 and final_state = 'event') as events_loop_or_age_rulein,
    count(*) filter (where loop_plus_age_rulein_flag = 1 and final_state = 'event') as events_loop_plus_age_rulein
from study_ahf_v3_2.audit_104_ntprobnp_rulein_refinement_v1;

select
    ntprobnp_rulein_cutoff,
    count(*) as n,
    count(*) filter (where ntprobnp_age_rulein_flag = 1) as n_age_rulein,
    count(*) filter (where loop_or_age_rulein_flag = 1) as n_loop_or_age_rulein,
    count(*) filter (where loop_or_age_rulein_flag = 1 and final_state = 'event') as events_loop_or_age_rulein
from study_ahf_v3_2.audit_104_ntprobnp_rulein_refinement_v1
group by ntprobnp_rulein_cutoff
order by ntprobnp_rulein_cutoff;
