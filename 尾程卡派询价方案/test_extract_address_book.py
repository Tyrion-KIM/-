# test_extract_address_book.py
import unittest, os, tempfile
from extract_address_book import english_name, country_code, clean_company, make_label, write_js

class TestExtract(unittest.TestCase):
    def test_english_name_strips_chinese(self):
        self.assertEqual(english_name("奥地利 Austria"), "Austria")
        self.assertEqual(english_name("英国 United Kingdom"), "United Kingdom")

    def test_country_code_mapping(self):
        self.assertEqual(country_code("奥地利 Austria"), "AT")
        self.assertEqual(country_code("英国 United Kingdom"), "GB")
        self.assertEqual(country_code("丹麦 Denmark"), "DK")
        self.assertEqual(country_code("未知 Xyzzy"), "")

    def test_clean_company_drops_junk_and_empty(self):
        self.assertEqual(clean_company("EICO A/S"), "EICO A/S")
        self.assertEqual(clean_company("VAT ID: ATU1  EMAIL: a@b.com"), "")
        self.assertEqual(clean_company(""), "")
        self.assertEqual(clean_company(None), "")

    def test_make_label(self):
        self.assertEqual(make_label("EICO A/S", "Sønderborg", "6400"), "EICO A/S")
        self.assertEqual(make_label("", "Genk", "3600"), "Genk 3600")

    def test_write_js_emits_const(self):
        rows = [{"id":1,"label":"Genk 3600","country":"BE","countryName":"Belgium",
                 "city":"Genk","postCode":"3600","addressLine":"De Schom 39","companyName":""}]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "address_book.js")
            write_js(rows, p)
            with open(p, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("window.ADDRESS_BOOK = [", text)
            self.assertIn('"postCode": "3600"', text)

if __name__ == "__main__":
    unittest.main()
