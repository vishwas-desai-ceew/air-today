"""'Get Air Today as an app' pop-up on the sign-in screen (phones only).

Browsers don't let a page add itself to the home screen (iPhone has no API
for it at all), so we show the steps for the visitor's phone instead. The
icon and name they get come from static/ (see the head tags in dashboard.py).
"""
import streamlit as st

IPHONE_STEPS = [
    ":material/ios_share: Tap **Share** in Safari",
    ":material/add_box: Tap **Add to Home Screen**",
]

ANDROID_STEPS = [
    ":material/more_vert: Tap **⋮** in Chrome",
    ":material/add_to_home_screen: Tap **Add to Home screen**",
]

_SEEN_KEY = "home_screen_popup_seen"


def home_screen_steps(user_agent: str) -> list[str] | None:
    """Steps for this phone, or None on a computer (nothing to show)."""
    if any(k in user_agent for k in ("iPhone", "iPad", "iPod")):
        return IPHONE_STEPS
    if "Android" in user_agent:
        return ANDROID_STEPS
    return None


@st.dialog("Get Air Today as an app", width="small")
def _home_screen_dialog(steps: list[str]) -> None:
    st.markdown("\n\n".join(steps))
    if st.button("Got it", type="primary", width="stretch"):
        st.rerun()


def render_home_screen_help(user_agent: str) -> None:
    """Pops up once per visit on a phone; a small button reopens it."""
    steps = home_screen_steps(user_agent)
    if steps is None:
        return
    reopen = st.button(
        "Add to home screen", icon=":material/add_to_home_screen:",
        type="tertiary", width="stretch", key="home_screen_reopen",
    )
    if reopen or not st.session_state.get(_SEEN_KEY):
        st.session_state[_SEEN_KEY] = True
        _home_screen_dialog(steps)
