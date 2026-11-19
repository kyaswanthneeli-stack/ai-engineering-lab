import unittest
from repopilot.test_evidence import check_three_stage_evidence,test_count
from repopilot.sandbox import RunResult


def run(rc, output):
    return RunResult(rc,10,output)

OK="----------------------------------------------------------------------\nRan 1 test in 0.001s\n\nOK\n"
FAIL="FAIL: test_bug (test_reproduction.TestBug.test_bug)\n----------------------------------------------------------------------\nRan 2 tests in 0.001s\n\nFAILED (failures=1)\n"
ERROR="ERROR: test_reproduction (unittest.loader._FailedTest.test_reproduction)\n----------------------------------------------------------------------\nRan 2 tests in 0.001s\n\nFAILED (errors=1)\n"
PATCHED="----------------------------------------------------------------------\nRan 2 tests in 0.001s\n\nOK\n"


class EvidenceTests(unittest.TestCase):
    def test_valid_real_failure_and_patch(self):
        check_three_stage_evidence(run(0,OK),run(1,FAIL),run(0,PATCHED))
    def test_import_error_not_a_reproduction(self):
        with self.assertRaisesRegex(ValueError,"Import/runtime"):
            check_three_stage_evidence(run(0,OK),run(1,ERROR),run(0,PATCHED))
    def test_no_new_test_rejected(self):
        with self.assertRaisesRegex(ValueError,"add and retain"):
            check_three_stage_evidence(run(0,OK),run(1,FAIL.replace("Ran 2 tests","Ran 1 test")),run(0,PATCHED))
    def test_no_discovery_rejected(self):
        with self.assertRaisesRegex(ValueError,"lacks a valid"):
            check_three_stage_evidence(run(0,"OK"),run(1,FAIL),run(0,PATCHED))
    def test_timed_out_rejected(self):
        with self.assertRaisesRegex(ValueError,"Timed-out"):
            check_three_stage_evidence(run(0,OK),RunResult(1,10,FAIL,True),run(0,PATCHED))
    def test_parse_count(self):
        self.assertEqual(test_count(FAIL),2)
        self.assertIsNone(test_count("no tests discovered"))
if __name__=="__main__":
    unittest.main()
