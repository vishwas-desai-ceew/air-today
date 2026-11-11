from views.home_screen import ANDROID_STEPS, IPHONE_STEPS, home_screen_steps

IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


def test_iphone_gets_safari_steps():
    assert home_screen_steps(IPHONE) is IPHONE_STEPS


def test_android_gets_chrome_steps():
    assert home_screen_steps(ANDROID) is ANDROID_STEPS


def test_computer_gets_nothing():
    assert home_screen_steps(MAC) is None
    assert home_screen_steps("") is None
