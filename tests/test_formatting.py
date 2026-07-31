from config.formatting import ordinal


def test_ordinal_first_second_third():
    assert ordinal(1) == "1st"
    assert ordinal(2) == "2nd"
    assert ordinal(3) == "3rd"


def test_ordinal_eleven_to_thirteen_are_th_not_st_nd_rd():
    # 11/12/13 are the classic exception to the "1->st, 2->nd, 3->rd" rule
    assert ordinal(11) == "11th"
    assert ordinal(12) == "12th"
    assert ordinal(13) == "13th"


def test_ordinal_regular_days():
    assert ordinal(4) == "4th"
    assert ordinal(20) == "20th"
    assert ordinal(31) == "31st"


def test_ordinal_twenty_first_to_twenty_third():
    assert ordinal(21) == "21st"
    assert ordinal(22) == "22nd"
    assert ordinal(23) == "23rd"


def test_ordinal_hundreds_repeat_the_same_exception():
    # n % 100 in [10, 20] should still be "th" even for 111-113 (matches 11-13)
    assert ordinal(111) == "111th"
    assert ordinal(112) == "112th"
    assert ordinal(113) == "113th"
    assert ordinal(121) == "121st"
