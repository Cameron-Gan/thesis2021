from unittest import TestCase
from datetime import time
from thesisInitial.tariff import TOUTariff

class TestTOUTariff(TestCase):
    def test_get_tariff(self):
        tou_tariff = {(time(0,0), time(12,0)): 10, (time(12,0), time(12,59)): 20}
        print(tou_tariff[0][0])
        t = TOUTariff(10,10,tou_tariff)
        self.assertTrue(t.get_tariff(time(10, 0)) == 10)
        self.fail()

