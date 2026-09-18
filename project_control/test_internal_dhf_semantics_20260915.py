"""Regression checks for errors that alter cohort eligibility or event time."""
import unittest

from advance_internal_dhf_v20260915 import ICU, TRANSFER, RETRO, assertions, time, blank_icu_template, entry_evidence


class SemanticsTest(unittest.TestCase):
    def test_orthopnea_and_its_negation(self):
        self.assertEqual(next(assertions('睡眠时无法平卧','congestion'))[0],'affirmed')
        self.assertEqual(next(assertions('否认无法平卧','congestion'))[0],'negated')
        self.assertEqual(next(assertions('全身中高度凹陷性浮肿','congestion'))[0],'affirmed')

    def test_empty_vs_populated_icu_admission(self):
        empty='入ICU时间：入ICU原因： 入ICU前诊治经过： 既往史： 入科查体： 辅助检查： 入ICU诊断： 转入ICU后诊疗计划：给予利尿治疗'
        self.assertTrue(blank_icu_template('入ICU记录',empty))
        self.assertFalse(blank_icu_template('入ICU记录',empty.replace('入ICU原因：','入ICU原因：呼吸困难')))

    def test_negation_inside_composite_edema_phrase(self):
        rows=list(assertions('双下肢无水肿','congestion'))
        self.assertEqual([r[0] for r in rows],['negated'])

    def test_negation_does_not_spread_to_next_clause(self):
        rows=list(assertions('未闻及湿啰音，但双下肢水肿','congestion'))
        self.assertEqual([r[0] for r in rows],['negated','affirmed'])

    def test_cannot_exclude_is_uncertain_not_negative(self):
        self.assertEqual(next(assertions('不能排除心衰','hf'))[0],'uncertain')

    def test_risk_and_historical_not_current_disease(self):
        self.assertEqual(next(assertions('可能发生心衰','hf'))[0],'hypothetical')
        self.assertEqual(next(assertions('既往心衰','hf'))[0],'historical')
        self.assertEqual(next(assertions('伴或不伴右心衰竭表现','hf'))[0],'hypothetical')

    def test_date_only_does_not_become_midnight(self):
        self.assertIsNone(time('2025-04-02'))
        self.assertIsNotNone(time('2025年4月2日 15：00'))

    def test_transfer_direction_preserves_ordinary_ward(self):
        text='患者于2025-04-23 16:16由钱塘1-3F ICU护理转入呼吸内科(钱塘)接科情况：神清'
        match=TRANSFER.search(text)
        self.assertIsNotNone(match)
        self.assertTrue(ICU.search(match.group(2)))
        self.assertFalse(ICU.search(match.group(3)))

    def test_respiratory_critical_care_department_is_not_icu(self):
        text='患者于2025-09-03 16:03由重症医学科(4F)(大运河)转入呼吸内科(大运河)/呼吸与危重症医学科'
        match=TRANSFER.search(text)
        self.assertTrue(ICU.search(match.group(2)))
        self.assertFalse(ICU.search(match.group(3)))
        self.assertTrue(ICU.search('呼吸与危重症医学科ICU'))

    def test_prior_episode_survives_later_explicit_entry(self):
        earlier=dict(event_time='2025-08-26 09:30:00', source='icu_discharge_note_admission_field')
        later=dict(event_time='2025-09-09 14:51:00', source='explicit_document_event')
        exit_=dict(event_time='2025-09-03 16:03:00')
        self.assertEqual(entry_evidence([later,earlier],[exit_]),[earlier,later])
        self.assertEqual(entry_evidence([later,earlier],[]),[later])

    def test_cancelled_and_unparsed_checklists_not_phenotype_evidence(self):
        for name in ['作废','病危通知','病重通知','麻醉前访视单']:
            self.assertTrue(RETRO.search(name))
        for name in ['入ICU记录','查房记录(SOAP)','会诊结果']:
            self.assertFalse(RETRO.search(name))


if __name__=='__main__':
    unittest.main()
