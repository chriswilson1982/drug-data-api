import main


class FakeCollection:
    """Stand-in for a pymongo Collection: looks documents up by a single
    query field value and records every value it was queried with, so
    tests can assert which fallback candidates were actually tried."""

    def __init__(self, docs_by_key=None):
        self.docs_by_key = docs_by_key or {}
        self.calls = []

    def find_one(self, query, projection=None):
        (key,) = query.values()
        self.calls.append(key)
        return self.docs_by_key.get(key)


class ExplodingCollection:
    """Simulates a database error, e.g. a dropped connection."""

    def find_one(self, query, projection=None):
        raise RuntimeError("mongodb+srv://user:supersecret@cluster/db unreachable")


# -- insert_zero / candidate builders (pure functions) ----------------------

def test_insert_zero_first_position_prepends():
    assert main.insert_zero("1234567890", 1) == "01234567890"


def test_insert_zero_sixth_position():
    assert main.insert_zero("1234567890", 6) == "12345067890"


def test_gtin_candidates_13_digit_tries_leading_zero():
    gtin = "1234567890123"
    assert main.gtin_candidates(gtin) == [gtin, "0" + gtin]


def test_gtin_candidates_14_digit_tries_stripped():
    gtin = "12345678901234"
    assert main.gtin_candidates(gtin) == [gtin, gtin[1:]]


def test_ndc_candidates_10_digit_tries_both_zero_positions():
    ndc = "1234567890"
    assert main.ndc_candidates(ndc) == [
        ndc,
        main.insert_zero(ndc, 1),
        main.insert_zero(ndc, 6),
    ]


def test_ndc_candidates_11_digit_leading_zero_tries_stripped():
    ndc = "01234567890"
    assert main.ndc_candidates(ndc) == [ndc, ndc[1:]]


def test_ndc_candidates_11_digit_no_leading_zero_has_no_fallback():
    ndc = "11234567890"
    assert main.ndc_candidates(ndc) == [ndc]


# -- find_with_fallback -------------------------------------------------

def test_find_with_fallback_returns_first_match_and_stops_trying():
    fake = FakeCollection({"b": {"x": 1}})
    result = main.find_with_fallback(fake, "field", ["a", "b", "c"], {})
    assert result == {"x": 1}
    assert fake.calls == ["a", "b"]


def test_find_with_fallback_returns_none_when_nothing_matches():
    fake = FakeCollection({})
    result = main.find_with_fallback(fake, "field", ["a", "b"], {})
    assert result is None
    assert fake.calls == ["a", "b"]


# -- dmd_api --------------------------------------------------------------

def test_dmd_api_rejects_non_numeric_gtin(monkeypatch):
    fake = FakeCollection({})
    monkeypatch.setattr(main, "dmd_collection", fake)
    result = main.dmd_api("abc")
    assert result["error"] is True
    assert fake.calls == []


def test_dmd_api_rejects_wrong_length_gtin(monkeypatch):
    fake = FakeCollection({})
    monkeypatch.setattr(main, "dmd_collection", fake)
    result = main.dmd_api("12345")
    assert result["error"] is True
    assert fake.calls == []


def test_dmd_api_falls_back_to_leading_zero_gtin(monkeypatch):
    gtin = "1234567890123"
    fake = FakeCollection({"0" + gtin: {"ampp": {"name": "Test Drug"}}})
    monkeypatch.setattr(main, "dmd_collection", fake)
    result = main.dmd_api(gtin)
    assert result["status"] == "success"
    assert result["data"] == {"name": "Test Drug"}
    assert fake.calls == [gtin, "0" + gtin]


def test_dmd_api_not_found(monkeypatch):
    monkeypatch.setattr(main, "dmd_collection", FakeCollection({}))
    result = main.dmd_api("1234567890123")
    assert result["error"] is True
    assert result["message"] == "Error: No drug data found for that GTIN"


def test_dmd_api_database_error_does_not_leak_details(monkeypatch):
    monkeypatch.setattr(main, "dmd_collection", ExplodingCollection())
    result = main.dmd_api("1234567890123")
    assert result["error"] is True
    assert result["message"] == "Error: Unable to process request at this time"
    assert "supersecret" not in result["message"]


# -- fda_api ----------------------------------------------------------------
# These two regression-test the real bugs found in review: the 11-digit
# fallback previously only ran when a result had *already* been found
# (misindented elif), and the 10-digit leading-zero fallback inserted the
# zero in the wrong place (insertZero(ndc, 0) instead of position 1).

def test_fda_api_falls_back_from_leading_zero_to_stripped_ndc(monkeypatch):
    fake = FakeCollection({"1234567890": {"generic_name": "Aspirin"}})
    monkeypatch.setattr(main, "fda_collection", fake)
    result = main.fda_api("01234567890")
    assert result["status"] == "success"
    assert fake.calls == ["01234567890", "1234567890"]


def test_fda_api_falls_back_to_leading_zero_ndc(monkeypatch):
    fake = FakeCollection({"01234567890": {"generic_name": "Ibuprofen"}})
    monkeypatch.setattr(main, "fda_collection", fake)
    result = main.fda_api("1234567890")
    assert result["status"] == "success"
    assert fake.calls == ["1234567890", "01234567890"]


def test_fda_api_rejects_non_numeric_ndc(monkeypatch):
    fake = FakeCollection({})
    monkeypatch.setattr(main, "fda_collection", fake)
    result = main.fda_api("abc")
    assert result["error"] is True
    assert fake.calls == []


def test_fda_api_not_found_message_names_ndc_not_gtin(monkeypatch):
    monkeypatch.setattr(main, "fda_collection", FakeCollection({}))
    result = main.fda_api("1234567890")
    assert result["error"] is True
    assert result["message"] == "Error: No drug data found for that NDC"


def test_fda_api_database_error_does_not_leak_details(monkeypatch):
    monkeypatch.setattr(main, "fda_collection", ExplodingCollection())
    result = main.fda_api("1234567890")
    assert result["error"] is True
    assert result["message"] == "Error: Unable to process request at this time"
    assert "supersecret" not in result["message"]


# -- misc endpoints -----------------------------------------------------

def test_api_test_endpoint():
    result = main.api_test()
    assert result["status"] == "success"
    assert result["message"] == "API Status OK"


def test_root_url_mentions_both_endpoints():
    result = main.handle_root_url()
    assert result["status"] == "success"
    assert "/api/dmd/gtin/" in result["message"]
    assert "/api/fda/ndc/" in result["message"]


def test_404_handler_is_registered_on_the_app_actually_run():
    # Regression test: @error(404) used to register on bottle's default
    # app rather than the custom `app` instance passed to app.run(),
    # so it never fired.
    assert main.app.error_handler.get(404) is main.error404
