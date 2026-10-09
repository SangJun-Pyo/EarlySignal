"""Focused checks for presentation evidence boundaries; no API or private data."""
import importlib.util
import json
from pathlib import Path
import unittest
from scipy.stats import poisson

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stat_figures',HERE/'build_stat_figures.py')
figures=importlib.util.module_from_spec(spec);spec.loader.exec_module(figures)
REPO=HERE.parents[2]


class FigureEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.console=json.loads((REPO/'web/public/data/console.json').read_text())
        self.rule=json.loads((REPO/'web/public/data/meta.json').read_text())['params']
        self.group=self.console['demo_signal']['grp']
        self.category=self.console['demo_signal']['category']
        self.series=self.console['series'][self.group]
        self.index=self.series['months'].index(self.console['demo_signal']['month'])
        self.values=self.series['categories'][self.category]

    def test_current_export_matches_independent_calculation(self):
        result=figures.extract_example(self.console,self.rule)
        self.assertEqual(result['labeler'],self.console['labeler'])
        self.assertTrue(result['verification']['alert_matches_export'])

    def test_llm_values_are_not_keyword_constants(self):
        self.console['labeler']='llm'
        for i in range(self.index-12,self.index):self.values['n'][i]=1
        self.values['n'][self.index]=6
        self.values['baseline'][self.index]=1
        self.values['alert'][self.index]=True
        result=figures.extract_example(self.console,self.rule)
        self.assertEqual((result['baseline'],result['observed']),(1,6))
        self.assertAlmostEqual(result['p_value'],poisson.sf(5,1))
        self.assertEqual(result['labeler'],'llm')

    def test_future_counts_do_not_change_selected_month(self):
        before=figures.extract_example(self.console,self.rule)
        for i in range(self.index+1,len(self.series['months'])):
            self.values['n'][i]=self.series['total'][i]
        self.assertEqual(before,figures.extract_example(self.console,self.rule))

    def test_zero_history_uses_declared_floor_and_no_false_alert(self):
        for i in range(self.index-12,self.index+1):self.values['n'][i]=0
        self.values['baseline'][self.index]=self.rule['lambda_floor']
        self.values['alert'][self.index]=False
        result=figures.extract_example(self.console,self.rule)
        self.assertEqual(result['baseline'],self.rule['lambda_floor'])
        self.assertEqual(result['p_value'],1)
        self.assertFalse(result['alert'])

    def test_mismatched_export_is_rejected(self):
        self.values['baseline'][self.index]+=1
        with self.assertRaisesRegex(ValueError,'disagrees'):figures.extract_example(self.console,self.rule)

    def test_insufficient_history_is_rejected(self):
        month=self.series['months'][self.rule['min_history']-1]
        self.console['demo_signal']['month']=month
        self.console['asof_months'].append(month)
        with self.assertRaisesRegex(ValueError,'enough history'):figures.extract_example(self.console,self.rule)


if __name__=='__main__':unittest.main()
